import os
import glob
import re
import pandas as pd
import matplotlib.pyplot as plt


def summarize_battery_locations_rq2_1(results_root="."):
    rows = []

    folders = glob.glob(
        os.path.join(
            results_root,
            "results_*_RQ2.1_Scene=*_PV*_Batt=*"
        )
    )

    for folder in folders:
        try:
            folder_name = os.path.basename(folder)

            scene_match = re.search(r"Scene=([^_]+)", folder_name)
            pv_match = re.search(r"PV([\d\.]+)", folder_name)
            batt_match = re.search(r"Batt=([\d\.]+)", folder_name)

            if not batt_match:
                continue

            scene = scene_match.group(1) if scene_match else None
            pv_share = float(pv_match.group(1)) if pv_match else None
            num_batts = float(batt_match.group(1))

            battery_file = os.path.join(folder, "batteries.csv")

            if not os.path.exists(battery_file):
                continue

            df = pd.read_csv(battery_file)

            # Remove non-installed or phantom batteries
            if "battery_installed" in df.columns:
                df = df[df["battery_installed"] > 0]

            if "Emax_kWh" in df.columns:
                df = df[df["Emax_kWh"] > 1e-6]

            if len(df) == 0:
                continue

            for _, row in df.iterrows():
                rows.append({
                    "Scene": scene,
                    "PV_Share": pv_share,
                    "Allowed_Batteries": num_batts,
                    "Bus": int(row["bus"]),
                    "Energy_kWh": row["Emax_kWh"] if "Emax_kWh" in df.columns else None,
                    "Power_kW": row["Pmax_kW"] if "Pmax_kW" in df.columns else None,
                })

        except Exception as e:
            print(f"Skipping {folder}: {e}")

    summary = pd.DataFrame(rows)

    if summary.empty:
        print("No batteries found.")
        return None

    scene_order = {"Uniform": 0, "Bus": 1, "Line": 2}
    summary["_scene_order"] = summary["Scene"].map(scene_order).fillna(99)

    summary = (
        summary.sort_values(
            ["_scene_order", "PV_Share", "Allowed_Batteries", "Bus"]
        )
        .drop(columns="_scene_order")
        .reset_index(drop=True)
    )

    print("\n==============================")
    print("RQ2.1 BATTERY PLACEMENT SUMMARY")
    print("==============================\n")

    print(
        summary.to_string(
            index=False,
            float_format=lambda x: f"{x:.2f}"
        )
    )

    return summary

def plot_bess_sizing_vs_pv(summary):
    """
    Plot total installed BESS energy capacity [kWh]
    versus PV penetration for each PV strategy.

    Parameters
    ----------
    summary : pd.DataFrame
        Output of summarize_battery_locations_rq2_1()
    """

    import matplotlib.pyplot as plt
    import pandas as pd

    # ----------------------------------------
    # Total installed capacity per scenario
    # ----------------------------------------

    df_plot = (
        summary
        .groupby(
            ["Scene", "PV_Share", "Allowed_Batteries"]
        )["Energy_kWh"]
        .sum()
        .reset_index()
    )

    # ----------------------------------------
    # Plot
    # ----------------------------------------

    plt.figure(figsize=(8, 5))

    for scene in ["Uniform", "Bus", "Line"]:

        df_scene = (
            df_plot[
                (df_plot["Scene"] == scene)
                &
                (df_plot["Allowed_Batteries"] == 2)
            ]
            .sort_values("PV_Share")
        )

        plt.plot(
            df_scene["PV_Share"],
            df_scene["Energy_kWh"],
            marker="o",
            linewidth=2,
            label=scene
        )

    plt.xlabel("PV Penetration Factor")
    plt.ylabel("Installed BESS Capacity [kWh]")
    plt.title(
        "Optimal BESS Sizing under Alternative PV Deployment Strategies"
    )

    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.show()

def summarize_pv_utilization_rq2_1(results_root="."):
    """
    Summarize PV generation, utilization, and curtailment for RQ2.1 scenarios.

    Expected folder format:
        results_0613_0614_RQ2.1_Scene=Uniform_PV1.25_Batt=2.00

    Expected file:
        pv_summary.csv

    Expected columns:
        bus,time,PV_used_kW,PV_curtailed_kW
    """

    import os
    import re
    import glob
    import pandas as pd

    rows = []

    folders = glob.glob(
        os.path.join(
            results_root,
            "results_*_RQ2.1_Scene=*_PV*_Batt=*"
        )
    )

    for folder in folders:
        try:
            folder_name = os.path.basename(folder)

            scene_match = re.search(r"Scene=([^_]+)", folder_name)
            pv_match = re.search(r"PV([\d\.]+)", folder_name)
            batt_match = re.search(r"Batt=([\d\.]+)", folder_name)

            if not (scene_match and pv_match and batt_match):
                continue

            scene = scene_match.group(1)
            pv_share = float(pv_match.group(1))
            bess = float(batt_match.group(1))

            pv_file = os.path.join(folder, "pv_summary.csv")

            if not os.path.exists(pv_file):
                print(f"[WARNING] Missing pv_summary.csv in {folder_name}")
                continue

            df = pd.read_csv(pv_file)

            required_cols = {
                "PV_used_kW",
                "PV_curtailed_kW"
            }

            missing_cols = required_cols - set(df.columns)

            if missing_cols:
                print(
                    f"[WARNING] Missing columns {missing_cols} "
                    f"in {folder_name}"
                )
                continue

            pv_used_kwh = df["PV_used_kW"].sum()
            pv_curtailed_kwh = df["PV_curtailed_kW"].sum()
            pv_generated_kwh = pv_used_kwh + pv_curtailed_kwh

            if pv_generated_kwh > 0:
                pv_used_pct = 100 * pv_used_kwh / pv_generated_kwh
                pv_curtailed_pct = 100 * pv_curtailed_kwh / pv_generated_kwh
            else:
                pv_used_pct = 0.0
                pv_curtailed_pct = 0.0

            rows.append({
                "Scenario_ID": (
                    f"S4.{scene}.PV{int(round(pv_share * 100))}"
                    f".B{int(round(bess))}"
                ),
                "Scene": scene,
                "PV_Share": pv_share,
                "BESS": bess,
                "PV_Generated_MWh": pv_generated_kwh / 1000,
                "PV_Used_MWh": pv_used_kwh / 1000,
                "PV_Curtailed_MWh": pv_curtailed_kwh / 1000,
                "PV_Used_%": pv_used_pct,
                "PV_Curtailed_%": pv_curtailed_pct
            })

        except Exception as e:
            print(f"Skipping {folder}: {e}")

    summary = pd.DataFrame(rows)

    if summary.empty:
        print("No PV utilization results found.")
        return None

    scene_order = {
        "Uniform": 0,
        "Bus": 1,
        "Line": 2
    }

    summary["_scene_order"] = (
        summary["Scene"]
        .map(scene_order)
        .fillna(99)
    )

    summary = (
        summary
        .sort_values(
            ["PV_Share", "_scene_order", "BESS"]
        )
        .drop(columns="_scene_order")
        .reset_index(drop=True)
    )

    print("\n==============================")
    print("RQ2.1 PV UTILIZATION SUMMARY")
    print("==============================\n")

    print(
        summary.to_string(
            index=False,
            float_format=lambda x: f"{x:.2f}"
        )
    )

    return summary

def plot_pv_usage_breakdown(summary, scene="Uniform"):

    import numpy as np
    import matplotlib.pyplot as plt

    # -------------------------
    # Filter data
    # -------------------------

    df = summary.copy()

    df = df[
        (df["Scene"] == scene)
        &
        (df["BESS"].isin([0, 2]))
    ]

    df_b0 = (
        df[df["BESS"] == 0]
        .sort_values("PV_Share")
        .reset_index(drop=True)
    )

    df_b2 = (
        df[df["BESS"] == 2]
        .sort_values("PV_Share")
        .reset_index(drop=True)
    )

    # -------------------------
    # Layout
    # -------------------------

    labels = [
        f"PV{int(pv * 100)}"
        for pv in df_b0["PV_Share"]
    ]

    x = np.arange(len(labels))

    width = 0.28
    offset = 0.20

    fig, ax = plt.subplots(figsize=(10, 5))

    # -------------------------
    # B0 bars
    # -------------------------

    ax.bar(
        x - offset,
        df_b0["PV_Used_MWh"],
        width,
        color="tab:blue",
        label="Used"
    )

    ax.bar(
        x - offset,
        df_b0["PV_Curtailed_MWh"],
        width,
        bottom=df_b0["PV_Used_MWh"],
        color="tab:orange",
        label="Curtailed"
    )

    # -------------------------
    # B2 bars
    # -------------------------

    ax.bar(
        x + offset,
        df_b2["PV_Used_MWh"],
        width,
        color="tab:blue"
    )

    ax.bar(
        x + offset,
        df_b2["PV_Curtailed_MWh"],
        width,
        bottom=df_b2["PV_Used_MWh"],
        color="tab:orange"
    )

    # -------------------------
    # Labels inside used bars
    # -------------------------

    for i in range(len(df_b0)):

        used_b0 = df_b0.loc[i, "PV_Used_MWh"]
        used_b2 = df_b2.loc[i, "PV_Used_MWh"]

        ax.text(
            x[i] - offset,
            used_b0 / 2,
            f"{used_b0:.0f}",
            ha="center",
            va="center",
            fontsize=8,
            color="white",
            fontweight="bold"
        )

        ax.text(
            x[i] + offset,
            used_b2 / 2,
            f"{used_b2:.0f}",
            ha="center",
            va="center",
            fontsize=8,
            color="white",
            fontweight="bold"
        )

    # -------------------------
    # Total labels
    # -------------------------

    for i in range(len(df_b0)):

        total_b0 = (
            df_b0.loc[i, "PV_Used_MWh"]
            + df_b0.loc[i, "PV_Curtailed_MWh"]
        )

        total_b2 = (
            df_b2.loc[i, "PV_Used_MWh"]
            + df_b2.loc[i, "PV_Curtailed_MWh"]
        )

        ax.text(
            x[i] - offset,
            total_b0 + 8,
            f"{total_b0:.0f}",
            ha="center",
            va="bottom",
            fontsize=8
        )

        ax.text(
            x[i] + offset,
            total_b2 + 8,
            f"{total_b2:.0f}",
            ha="center",
            va="bottom",
            fontsize=8
        )

    # -------------------------
    # B0 / B2 labels
    # -------------------------

    for i in range(len(x)):

        ax.text(
            x[i] - offset,
            -20,
            "B0",
            ha="center",
            va="top",
            fontsize=8
        )

        ax.text(
            x[i] + offset,
            -20,
            "B2",
            ha="center",
            va="top",
            fontsize=8
        )

    # -------------------------
    # Axes
    # -------------------------

    ax.set_xticks(x)
    ax.set_xticklabels(labels)

    ax.set_xlabel("PV penetration scenario")
    ax.set_ylabel("PV energy [MWh/year]")

    ax.set_title(
        f"PV Utilization Breakdown ({scene})"
    )

    ax.set_ylim(bottom=-40)

    ax.grid(axis="y", alpha=0.3)

    # Remove duplicate legend entries
    handles, labels_legend = ax.get_legend_handles_labels()
    by_label = dict(zip(labels_legend, handles))
    ax.legend(by_label.values(), by_label.keys())

    plt.tight_layout()
    plt.show()

def plot_monthly_curtailment_with_price(
    results_root=".",
    scene="Line",
    bess=0,
    price_file="data/Netherlands hourly electricity price.csv",
    price_year=2025
):
    """
    Plot monthly PV curtailment for each PV penetration scenario,
    with monthly average electricity price and price spread on a
    secondary y-axis.

    Assumes pv_summary.csv has:
        bus,time,PV_used_kW,PV_curtailed_kW

    where time is an integer hour from 0 to 8759.
    """

    import os
    import glob
    import pandas as pd
    import matplotlib.pyplot as plt

    pv_levels = [1.00, 1.25, 1.50, 1.75, 2.00]

    month_names = [
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
    ]

    hours_per_month = {
        1: 31 * 24,
        2: 28 * 24,
        3: 31 * 24,
        4: 30 * 24,
        5: 31 * 24,
        6: 30 * 24,
        7: 31 * 24,
        8: 31 * 24,
        9: 30 * 24,
        10: 31 * 24,
        11: 30 * 24,
        12: 31 * 24,
    }

    month_edges = []
    current = 0

    for month, hours in hours_per_month.items():
        month_edges.append((month, current, current + hours))
        current += hours

    def hour_to_month(hour):
        for month, start, end in month_edges:
            if start <= hour < end:
                return month
        return 12

    # -------------------------
    # Curtailment plot
    # -------------------------

    fig, ax1 = plt.subplots(figsize=(10, 5))

    for pv_share in pv_levels:

        pattern = (
            f"results_*_RQ2.1_Scene={scene}"
            f"_PV{pv_share:.2f}"
            f"_Batt={bess:.2f}"
        )

        matches = glob.glob(
            os.path.join(results_root, pattern)
        )

        if len(matches) == 0:
            print(f"Missing scenario: {pattern}")
            continue

        folder = matches[0]
        pv_file = os.path.join(folder, "pv_summary.csv")

        if not os.path.exists(pv_file):
            print(f"Missing pv_summary.csv in {folder}")
            continue

        df = pd.read_csv(pv_file)

        df["time"] = df["time"].astype(int)
        df["month"] = df["time"].apply(hour_to_month)

        monthly = (
            df.groupby("month")["PV_curtailed_kW"]
            .sum()
            .reindex(range(1, 13), fill_value=0)
            / 1000
        )

        ax1.plot(
            range(1, 13),
            monthly.values,
            marker="o",
            linewidth=2,
            label=f"PV{int(pv_share * 100)}"
        )

    ax1.set_xticks(range(1, 13))
    ax1.set_xticklabels(month_names)

    ax1.set_xlabel("Month")
    ax1.set_ylabel("Curtailed PV energy [MWh]")
    ax1.grid(alpha=0.3)

    # -------------------------
    # Price plot on secondary axis
    # -------------------------

    prices = pd.read_csv(price_file)

    prices["Datetime (Local)"] = pd.to_datetime(
        prices["Datetime (Local)"]
    )

    prices = prices[
        prices["Datetime (Local)"].dt.year == price_year
    ].copy()

    prices["month"] = prices["Datetime (Local)"].dt.month

    price_monthly = (
        prices.groupby("month")["Price (EUR/MWhe)"]
        .agg(
            mean_price="mean",
            q10=lambda x: x.quantile(0.10),
            q90=lambda x: x.quantile(0.90)
        )
        .reindex(range(1, 13))
    )

    ax2 = ax1.twinx()

    ax2.plot(
        range(1, 13),
        price_monthly["mean_price"],
        color="black",
        marker="s",
        linewidth=2,
        linestyle="--",
        label="Average price"
    )

    ax2.fill_between(
        range(1, 13),
        price_monthly["q10"],
        price_monthly["q90"],
        color="black",
        alpha=0.12,
        label="Price 10--90 percentile"
    )

    ax2.set_ylabel("Electricity price [EUR/MWh]")

    # -------------------------
    # Combined legend
    # -------------------------

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()

    ax1.legend(
        lines1 + lines2,
        labels1 + labels2,
        loc="upper left",
        fontsize=8
    )

    plt.title(
        f"Monthly PV Curtailment and Electricity Prices ({scene}, B={int(bess)})"
    )

    plt.tight_layout()
    plt.show()

def plot_monthly_curtailment_with_price_outliers(
    results_root=".",
    scene="Uniform",
    bess=2,
    price_file="data/Netherlands hourly electricity price.csv",
    price_year=2025
):
    """
    Plot monthly PV curtailment for each PV penetration scenario,
    with monthly average electricity price and the average of the
    lowest 10% price hours on a secondary y-axis.

    This is useful because PV curtailment is expected to coincide more
    strongly with low-price or negative-price hours than with average prices.
    """

    import os
    import glob
    import pandas as pd
    import matplotlib.pyplot as plt

    pv_levels = [1.00, 1.25, 1.50, 1.75, 2.00]

    month_names = [
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
    ]

    hours_per_month = {
        1: 31 * 24,
        2: 28 * 24,
        3: 31 * 24,
        4: 30 * 24,
        5: 31 * 24,
        6: 30 * 24,
        7: 31 * 24,
        8: 31 * 24,
        9: 30 * 24,
        10: 31 * 24,
        11: 30 * 24,
        12: 31 * 24,
    }

    month_edges = []
    current = 0

    for month, hours in hours_per_month.items():
        month_edges.append((month, current, current + hours))
        current += hours

    def hour_to_month(hour):
        for month, start, end in month_edges:
            if start <= hour < end:
                return month
        return 12

    # -------------------------
    # Curtailment plot
    # -------------------------

    fig, ax1 = plt.subplots(figsize=(10, 5))

    for pv_share in pv_levels:

        pattern = (
            f"results_*_RQ2.1_Scene={scene}"
            f"_PV{pv_share:.2f}"
            f"_Batt={bess:.2f}"
        )

        matches = glob.glob(
            os.path.join(results_root, pattern)
        )

        if len(matches) == 0:
            print(f"Missing scenario: {pattern}")
            continue

        folder = matches[0]
        pv_file = os.path.join(folder, "pv_summary.csv")

        if not os.path.exists(pv_file):
            print(f"Missing pv_summary.csv in {folder}")
            continue

        df = pd.read_csv(pv_file)

        df["time"] = df["time"].astype(int)
        df["month"] = df["time"].apply(hour_to_month)

        monthly = (
            df.groupby("month")["PV_curtailed_kW"]
            .sum()
            .reindex(range(1, 13), fill_value=0)
            / 1000
        )

        ax1.plot(
            range(1, 13),
            monthly.values,
            marker="o",
            linewidth=2,
            label=f"PV{int(pv_share * 100)}"
        )

    ax1.set_xticks(range(1, 13))
    ax1.set_xticklabels(month_names)

    ax1.set_xlabel("Month")
    ax1.set_ylabel("Curtailed PV energy [MWh]")
    ax1.grid(alpha=0.3)

    # -------------------------
    # Price plot on secondary axis
    # -------------------------

    prices = pd.read_csv(price_file)

    prices["Datetime (Local)"] = pd.to_datetime(
        prices["Datetime (Local)"]
    )

    prices = prices[
        prices["Datetime (Local)"].dt.year == price_year
    ].copy()

    prices["month"] = prices["Datetime (Local)"].dt.month

    def bottom_10_percent_mean(x):
        cutoff = x.quantile(0.10)
        return x[x <= cutoff].mean()

    price_monthly = (
        prices.groupby("month")["Price (EUR/MWhe)"]
        .agg(
            mean_price="mean",
            bottom_10_mean=bottom_10_percent_mean
        )
        .reindex(range(1, 13))
    )

    ax2 = ax1.twinx()

    ax2.plot(
        range(1, 13),
        price_monthly["mean_price"],
        color="black",
        marker="s",
        linewidth=2,
        linestyle="--",
        label="Average price"
    )

    ax2.plot(
        range(1, 13),
        price_monthly["bottom_10_mean"],
        color="black",
        marker="v",
        linewidth=2,
        linestyle=":",
        label="Lowest 10% price hours"
    )

    ax2.fill_between(
        range(1, 13),
        price_monthly["bottom_10_mean"],
        price_monthly["mean_price"],
        color="black",
        alpha=0.08
    )

    ax2.set_ylabel("Electricity price [EUR/MWh]")

    # -------------------------
    # Combined legend
    # -------------------------

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()

    ax1.legend(
        lines1 + lines2,
        labels1 + labels2,
        loc="upper left",
        fontsize=8
    )

    plt.title(
        f"Monthly PV Curtailment and Low-Price Hours ({scene}, B={int(bess)})"
    )

    plt.tight_layout()
    plt.show()

def plot_monthly_curtailment_b0_b2_with_price_outliers(
    results_root=".",
    scene="Uniform",
    price_file="data/Netherlands hourly electricity price.csv",
    price_year=2025
):
    """
    Plot monthly PV curtailment for PV100, PV150, and PV200,
    comparing B0 and B2 in one figure.

    B0 is shown as a dashed line.
    B2 is shown as a solid line.

    The secondary y-axis shows:
        - monthly average electricity price
        - monthly average of the lowest 10% price hours
    """

    import os
    import glob
    import pandas as pd
    import matplotlib.pyplot as plt

    pv_levels = [1.00, 1.50, 2.00]
    bess_levels = [0.00, 2.00]

    month_names = [
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
    ]

    hours_per_month = {
        1: 31 * 24,
        2: 28 * 24,
        3: 31 * 24,
        4: 30 * 24,
        5: 31 * 24,
        6: 30 * 24,
        7: 31 * 24,
        8: 31 * 24,
        9: 30 * 24,
        10: 31 * 24,
        11: 30 * 24,
        12: 31 * 24,
    }

    month_edges = []
    current = 0

    for month, hours in hours_per_month.items():
        month_edges.append((month, current, current + hours))
        current += hours

    def hour_to_month(hour):
        for month, start, end in month_edges:
            if start <= hour < end:
                return month
        return 12

    fig, ax1 = plt.subplots(figsize=(11, 5.5))

    # -------------------------
    # Curtailment lines
    # -------------------------
    # Fixed colors by PV level
    pv_colors = {
        1.00: "tab:blue",     # PV100
        1.50: "tab:green",    # PV150
        2.00: "tab:purple"    # PV200
    }

    for pv_share in pv_levels:
        for bess in bess_levels:

            pattern = (
                f"results_*_RQ2.1_Scene={scene}"
                f"_PV{pv_share:.2f}"
                f"_Batt={bess:.2f}"
            )

            matches = glob.glob(
                os.path.join(results_root, pattern)
            )

            if len(matches) == 0:
                print(f"Missing scenario: {pattern}")
                continue

            folder = matches[0]
            pv_file = os.path.join(folder, "pv_summary.csv")

            if not os.path.exists(pv_file):
                print(f"Missing pv_summary.csv in {folder}")
                continue

            df = pd.read_csv(pv_file)

            df["time"] = df["time"].astype(int)
            df["month"] = df["time"].apply(hour_to_month)

            monthly = (
                df.groupby("month")["PV_curtailed_kW"]
                .sum()
                .reindex(range(1, 13), fill_value=0)
                / 1000
            )

            linestyle = "--" if bess == 0 else "-"
            marker = "o" if bess == 0 else "s"

            ax1.plot(
                range(1, 13),
                monthly.values,
                color=pv_colors[pv_share],
                linestyle=linestyle,
                marker=marker,
                linewidth=2,
                label=f"PV{int(pv_share*100)} B{int(bess)}"
            )

    ax1.set_xticks(range(1, 13))
    ax1.set_xticklabels(month_names)

    ax1.set_xlabel("Month")
    ax1.set_ylabel("Curtailed PV energy [MWh]")
    ax1.grid(alpha=0.3)

    # -------------------------
    # Price lines
    # -------------------------
    prices = pd.read_csv(price_file)

    prices["Datetime (Local)"] = pd.to_datetime(
        prices["Datetime (Local)"]
    )

    prices = prices[
        prices["Datetime (Local)"].dt.year == price_year
    ].copy()

    prices["month"] = prices["Datetime (Local)"].dt.month

    def bottom_10_percent_mean(x):
        cutoff = x.quantile(0.10)
        return x[x <= cutoff].mean()

    price_monthly = (
        prices.groupby("month")["Price (EUR/MWhe)"]
        .agg(
            mean_price="mean",
            bottom_10_mean=bottom_10_percent_mean
        )
        .reindex(range(1, 13))
    )

    ax2 = ax1.twinx()

    ax2.plot(
        range(1, 13),
        price_monthly["mean_price"],
        color="black",
        marker="^",
        linewidth=2,
        linestyle="-.",
        label="Average price"
    )

    ax2.plot(
        range(1, 13),
        price_monthly["bottom_10_mean"],
        color="black",
        marker="v",
        linewidth=2,
        linestyle=":",
        label="Lowest 10% price hours"
    )

    ax2.fill_between(
        range(1, 13),
        price_monthly["bottom_10_mean"],
        price_monthly["mean_price"],
        color="black",
        alpha=0.08
    )

    ax2.set_ylabel("Electricity price [EUR/MWh]")

    # -------------------------
    # Combined legend
    # -------------------------
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()

    ax1.legend(
        lines1 + lines2,
        labels1 + labels2,
        loc="upper left",
        fontsize=8,
        ncol=2
    )

    plt.title(
        f"Monthly PV Curtailment with and without BESS ({scene})"
    )

    plt.tight_layout()
    plt.show()

def plot_daily_profiles_pv_used_b0_b2(
    profile_file="data/Standaardprofielen elektriciteit 2026 versie 1.00.csv",
    results_root=".",
    scene="Uniform",
    pv_share=2.00,
    annual_demand_kwh=387_609
):
    """
    Plot average daily demand, PV generation, and PV used for B0 and B2.

    Left y-axis:
        - Average demand [kW]
        - Average PV generation [kW]

    Right y-axis:
        - Average PV used [kW] for B0 and B2 as bars

    Assumes pv_summary.csv contains:
        bus,time,PV_used_kW,PV_curtailed_kW

    where time is an integer hour from 0 to 8759.
    """

    import os
    import glob
    import pandas as pd
    import matplotlib.pyplot as plt

    # ==================================================
    # LOAD DEMAND AND PV PROFILES
    # ==================================================

    df_profile = pd.read_csv(
        profile_file,
        sep=";",
        decimal=".",
        encoding="utf-8",
        skiprows=6,
        header=0
    )

    df_profile["van"] = pd.to_datetime(
        df_profile["van"],
        format="%d-%m-%Y %H:%M"
    )

    # -------------------------
    # Demand profile
    # -------------------------

    demand = (
        df_profile[["van", "1.00_E1C_AMI_A"]]
        .set_index("van")
        .resample("h")
        .sum()
    )

    demand = demand / demand.sum()
    demand["hour"] = demand.index.hour

    demand["Demand_kW"] = (
        demand["1.00_E1C_AMI_A"]
        * annual_demand_kwh
    )

    hourly_demand = (
        demand.groupby("hour")["Demand_kW"]
        .mean()
        .reindex(range(24), fill_value=0)
    )

    # -------------------------
    # PV generation profile
    # -------------------------

    pv = (
        df_profile[["van", "1.00_E1C_AMI_I"]]
        .set_index("van")
        .resample("h")
        .sum()
    )

    pv = pv / pv.sum()
    pv["hour"] = pv.index.hour

    pv["PV_generation_kW"] = (
        pv["1.00_E1C_AMI_I"]
        * annual_demand_kwh
        * pv_share
    )

    hourly_pv_generation = (
        pv.groupby("hour")["PV_generation_kW"]
        .mean()
        .reindex(range(24), fill_value=0)
    )

    # ==================================================
    # LOAD PV USED DATA
    # ==================================================

    def load_hourly_pv_used(bess):

        pattern = (
            f"results_*_RQ2.1_Scene={scene}"
            f"_PV{pv_share:.2f}"
            f"_Batt={bess:.2f}"
        )

        matches = glob.glob(
            os.path.join(results_root, pattern)
        )

        if len(matches) == 0:
            raise FileNotFoundError(
                f"No scenario folder found for pattern: {pattern}"
            )

        if len(matches) > 1:
            print(
                f"[WARNING] Multiple folders found for {pattern}. "
                f"Using: {matches[0]}"
            )

        pv_summary_file = os.path.join(
            matches[0],
            "pv_summary.csv"
        )

        if not os.path.exists(pv_summary_file):
            raise FileNotFoundError(
                f"pv_summary.csv not found in {matches[0]}"
            )

        df = pd.read_csv(pv_summary_file)

        df["time"] = df["time"].astype(int)
        df["hour"] = df["time"] % 24

        # hourly_pv_used = (
        #     df.groupby("hour")["PV_used_kW"]
        #     .mean()
        #     .reindex(range(24), fill_value=0)
        # )
        hourly_pv_used = (
            df.groupby("hour")["PV_used_kW"]
            .sum()
            / 365
        )

        return hourly_pv_used

    hourly_pv_used_b0 = load_hourly_pv_used(0)
    hourly_pv_used_b2 = load_hourly_pv_used(2)

    # ==================================================
    # PLOT
    # ==================================================

    hours = list(range(24))

    fig, ax1 = plt.subplots(figsize=(11, 5))

    # -------------------------
    # Left axis: demand and PV generation
    # -------------------------

    ax1.plot(
        hours,
        hourly_demand.values,
        linestyle="--",
        linewidth=3,
        label="Average demand"
    )

    ax1.plot(
        hours,
        hourly_pv_generation.values,
        linewidth=3,
        label="Average PV generation"
    )

    ax1.set_xlabel("Hour of day")
    ax1.set_ylabel("Average demand / PV generation [kW]")
    ax1.set_xticks(range(0, 24, 2))
    ax1.grid(axis="y", alpha=0.3)

    # -------------------------
    # Right axis: PV used
    # -------------------------

    ax2 = ax1.twinx()

    bar_width = 0.35

    ax2.bar(
        [h - bar_width / 2 for h in hours],
        hourly_pv_used_b0.values,
        width=bar_width,
        alpha=0.45,
        label="PV used B0"
    )

    ax2.bar(
        [h + bar_width / 2 for h in hours],
        hourly_pv_used_b2.values,
        width=bar_width,
        alpha=0.45,
        label="PV used B2"
    )

    ax2.set_ylabel("Average PV used [kW]")

    # -------------------------
    # Combined legend
    # -------------------------

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()

    ax1.legend(
        lines1 + lines2,
        labels1 + labels2,
        loc="upper left"
    )

    plt.title(
        f"Average Daily Demand, PV Generation and PV Utilization\n"
        f"{scene}, PV{int(pv_share * 100)}"
    )

    plt.tight_layout()
    plt.show()

        # ==================================================
    # HOURLY PV UTILIZATION SUMMARY TABLE
    # ==================================================

    hourly_summary_df = pd.DataFrame({
        "Hour": range(24),
        "PV_Used_B0_kW": hourly_pv_used_b0.values,
        "PV_Used_B2_kW": hourly_pv_used_b2.values
    })

    hourly_summary_df["Increase_kW"] = (
        hourly_summary_df["PV_Used_B2_kW"]
        - hourly_summary_df["PV_Used_B0_kW"]
    )

    hourly_summary_df["Increase_%"] = (
        100
        * hourly_summary_df["Increase_kW"]
        / hourly_summary_df["PV_Used_B0_kW"]
    )

    hourly_summary_df["Increase_%"] = (
        hourly_summary_df["Increase_%"]
        .replace([float("inf"), -float("inf")], 0)
        .fillna(0)
    )

    hourly_summary_df.insert(
        0,
        "Scenario_ID",
        f"S4.{scene}.PV{int(pv_share * 100)}"
    )

    print("\n======================================")
    print("HOURLY PV UTILIZATION SUMMARY")
    print("======================================\n")

    print(
        hourly_summary_df.to_string(
            index=False,
            float_format=lambda x: f"{x:.2f}"
        )
    )
    

# summary = summarize_battery_locations_rq2_1()
# plot_bess_sizing_vs_pv(summary)

# summary = summarize_pv_utilization_rq2_1()
# plot_pv_usage_breakdown(summary)
# plot_monthly_curtailment_with_price()

# plot_monthly_curtailment_with_price_outliers()

plot_monthly_curtailment_b0_b2_with_price_outliers()

# plot_daily_profiles_pv_used_b0_b2(
#     scene="Bus",
#     pv_share=2.00
# )

# plot_daily_profiles_pv_used_b0_b2(
#     scene="Bus",
#     pv_share=1.00
# )

# plot_daily_profiles_pv_used_b0_b2(
#     scene="Bus",
#     pv_share=2.00
# )