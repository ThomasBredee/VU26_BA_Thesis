import os
import glob
import re
import pandas as pd
import matplotlib.pyplot as plt



def summarize_rq1_results(results_root="."):

    rows = []

    folders = glob.glob(
        os.path.join(
            results_root,
            "results_*_RQ1_Batt=*"
        )
    )

    for folder in folders:

        try:
            folder_name = os.path.basename(folder)

            batt_match = re.search(
                r"Batt=([\d\.]+)",
                folder_name
            )

            n_batt = (
                float(batt_match.group(1))
                if batt_match else None
            )

            # ==================================
            # VOLTAGES
            # ==================================

            df_v = pd.read_csv(
                os.path.join(
                    folder,
                    "voltage_profiles.csv"
                )
            )

            v_min = df_v["v_pu"].min()
            v_max = df_v["v_pu"].max()

            voltage_violations = (
                (df_v["v_pu"] < 0.95)
                |
                (df_v["v_pu"] > 1.05)
            ).sum()

            # ==================================
            # LINE FLOWS
            # ==================================

            df_line = pd.read_csv(
                os.path.join(
                    folder,
                    "line_flows.csv"
                )
            )

            max_loading = (
                df_line["loading_percent"]
                .max()
            )

            overload_hours = (
                df_line["loading_percent"]
                > 100
            ).sum()

            # ==================================
            # SUBSTATION
            # ==================================

            df_sub = pd.read_csv(
                os.path.join(
                    folder,
                    "substation.csv"
                )
            )

            annual_import = (
                df_sub["P_sub_kW"]
                .clip(lower=0)
                .sum()
                / 1000
            )

            peak_import = (
                df_sub["P_sub_kW"]
                .max()
                / 1000
            )

            peak_export = (
                df_sub["P_sub_kW"]
                .min()
                / 1000
            )

            # ==================================
            # PV CURTAILMENT
            # ==================================

            pv_file = os.path.join(
                folder,
                "pv_summary.csv"
            )

            curtailed = 0.0

            if os.path.exists(pv_file):

                df_pv = pd.read_csv(pv_file)

                curtailed = (
                    df_pv["PV_curtailed_kW"]
                    .sum()
                    / 1000
                )

            # ==================================
            # SAVE
            # ==================================

            rows.append({

                "Batteries":
                    n_batt,

                "Min_V":
                    round(v_min, 4),

                "Max_V":
                    round(v_max, 4),

                "Voltage_Violations":
                    int(voltage_violations),

                "Max_Loading_%":
                    round(max_loading, 2),

                "Overload_Hours":
                    int(overload_hours),

                "Peak_Import_MW":
                    round(peak_import, 3),

                "Peak_Export_MW":
                    round(peak_export, 3),

                "Annual_Import_MWh":
                    round(annual_import, 2),

                "PV_Curtailed_MWh":
                    round(curtailed, 2)
            })

        except Exception as e:

            print(
                f"Skipping {folder}: {e}"
            )

    summary = pd.DataFrame(rows)

    summary = summary.sort_values(
        "Batteries"
    )

    # summary.to_csv(
    #     "RQ1_summary.csv",
    #     index=False,
    #     float_format="%.2f"
    # )

    print("\n=== RQ1 SUMMARY ===\n")
    print(summary.to_string(index=False))

    return summary




def summarize_battery_locations(results_root="."):

    rows = []

    folders = glob.glob(
        os.path.join(
            results_root,
            "results_*_RQ2.1_Scene=*"
        )
    )

    for folder in folders:

        try:

            folder_name = os.path.basename(folder)

            batt_match = re.search(r"Batt=([\d\.]+)", folder_name)
            elec_match = re.search(r"elec=([\d\.]+)", folder_name)
            pv_match = re.search(r"P=([\d\.]+)", folder_name)

            if not batt_match:
                continue

            num_batts = float(batt_match.group(1))
            electrification = float(elec_match.group(1)) if elec_match else None
            pv_share = float(pv_match.group(1)) if pv_match else None

            battery_file = os.path.join(folder, "batteries.csv")

            if not os.path.exists(battery_file):
                continue

            df = pd.read_csv(battery_file)

            if "battery_installed" in df.columns:
                df = df[df["battery_installed"] > 0]

            if len(df) == 0:
                continue

            for _, row in df.iterrows():

                rows.append({
                    "Electrification": electrification,
                    "PV_Share": pv_share,
                    "Allowed_Batteries": num_batts,
                    "Bus": int(row["bus"]),
                    "Energy_kWh": row["Emax_kWh"] if "Emax_kWh" in df.columns else None,
                    "Power_kW": row["Pmax_kW"] if "Pmax_kW" in df.columns else None
                })

        except Exception as e:
            print(f"Skipping {folder}: {e}")

    summary = pd.DataFrame(rows)

    if len(summary) == 0:
        print("No batteries found.")
        return None

    summary = summary.sort_values(
        ["Electrification", "PV_Share", "Allowed_Batteries", "Bus"]
    )

    print("\n==============================")
    print("BATTERY PLACEMENT SUMMARY")
    print("==============================\n")

    print(
        summary.to_string(
            index=False,
            float_format=lambda x: f"{x:.2f}"
        )
    )

    return summary



def summarize_voltage_profiles(results_root=".", V_MIN=0.95, V_MAX=1.05):

    summaries = []

    folders = glob.glob(
        os.path.join(
            results_root,
            "results_*_RQ1.2_Batt=*_elec=*_P=*"
        )
    )

    for folder in folders:

        voltage_file = os.path.join(folder, "voltage_profiles.csv")

        if not os.path.exists(voltage_file):
            continue

        folder_name = os.path.basename(folder)

        batt_match = re.search(r"Batt=([\d\.]+)", folder_name)
        elec_match = re.search(r"elec=([\d\.]+)", folder_name)
        pv_match = re.search(r"P=([\d\.]+)", folder_name)

        batteries = float(batt_match.group(1)) if batt_match else None
        electrification = float(elec_match.group(1)) if elec_match else None
        pv_share = float(pv_match.group(1)) if pv_match else None

        df = pd.read_csv(voltage_file)

        avg_bus_voltage = df.groupby("bus")["v_sq_pu"].mean()
        # weakest_bus = int(avg_bus_voltage.idxmin())
        # weakest_bus_avg_voltage = avg_bus_voltage.min()

        bus_p1 = (df.groupby("bus")["v_sq_pu"].quantile(0.01))

        weakest_bus = int(bus_p1.idxmin())
        weakest_bus_p1 = bus_p1.min()

        min_v = df["v_sq_pu"].min()
        max_v = df["v_sq_pu"].max()
        p1 = df["v_sq_pu"].quantile(0.01)
        p99 = df["v_sq_pu"].quantile(0.99)


        summaries.append({
            "Electrification": electrification,
            "PV_Share": pv_share,
            "Batteries": batteries,
            "Min_V": min_v,
            "P1_V": p1,
            "Mean_V": df["v_sq_pu"].mean(),
            "P99_V": p99,
            "Max_V": max_v,
            # "Voltage_Spread": p99 - p1,
            # "Violations": violations,
            "Weakest_Bus_voltage": weakest_bus,
            "Weakest_Bus_Avg_V": weakest_bus_p1

        })

    summary_df = pd.DataFrame(summaries)

    if summary_df.empty:
        print("No voltage profile results found.")
        return None

    summary_df = summary_df.sort_values(
        ["Electrification", "PV_Share", "Batteries"]
    )

    print("\n==============================")
    print("VOLTAGE PROFILE SUMMARY")
    print("==============================")

    print(
        summary_df.round(4).to_string(index=False)
    )

    return summary_df



def weakest_bus_summary(results_root, experiment):
    """
    Creates a summary table for the weakest bus in each scenario.

    Columns:
    - Electrification
    - BESS
    - Weakest Bus
    - Min V
    - P1 V
    - Mean V
    - P99 V
    - Max V
    """

    V_MIN = 0.95
    V_MAX = 1.05

    pattern = os.path.join(
        results_root,
        f"results_*_{experiment}_Batt=*"
    )

    folders = glob.glob(pattern)

    rows = []

    for folder in folders:

        folder_name = os.path.basename(folder)

        batt_match = re.search(r"Batt=([0-9.]+)", folder_name)
        elec_match = re.search(r"elec=([0-9.]+)", folder_name)

        if batt_match is None:
            continue

        bess = float(batt_match.group(1))
        elec = float(elec_match.group(1)) if elec_match else 1.0

        voltage_file = os.path.join(
            folder,
            "voltage_profiles.csv"
        )

        if not os.path.exists(voltage_file):
            continue

        df = pd.read_csv(voltage_file)

        # Determine weakest bus
        avg_bus_voltage = (
            df.groupby("bus")["v_sq_pu"]
            .mean()
        )

        weakest_bus = int(
            avg_bus_voltage.idxmin()
        )

        # Select only weakest bus data
        df_bus = df[
            df["bus"] == weakest_bus
        ]

        violations = (
            (df_bus["v_sq_pu"] < V_MIN) |
            (df_bus["v_sq_pu"] > V_MAX)
        ).sum()

        rows.append({
            "Electrification": elec,
            "BESS": bess,
            "Weakest_Bus": weakest_bus,
            "Min_V": df_bus["v_sq_pu"].min(),
            "P1_V": df_bus["v_sq_pu"].quantile(0.01),
            "Mean_V": df_bus["v_sq_pu"].mean(),
            "P99_V": df_bus["v_sq_pu"].quantile(0.99),
            "Max_V": df_bus["v_sq_pu"].max(),
            "Violations": violations,
            "Hours_Below_0.95": (df_bus["v_sq_pu"] < V_MIN).sum(),
            "Hours_Above_1.05": (df_bus["v_sq_pu"] > V_MAX).sum()
        })

    result_df = pd.DataFrame(rows)

    if not result_df.empty:
        result_df = result_df.sort_values(
            ["Electrification"]
        )

    print("\n==============================")
    print("WEAKEST BUS VOLTAGE SUMMARY")
    print("==============================")
    print(
        result_df.round(4)
        .to_string(index=False)
    )

    return result_df



import os
import glob
import pandas as pd
import matplotlib.pyplot as plt


def voltage_checker(case1, case2, chosen_bus, results_root="."):

    # --------------------------------------------------
    # Find scenario folders
    # --------------------------------------------------

    case0_folder = glob.glob(
        os.path.join(
            results_root,
            case1
            #"resulXts_*_RQ1_Batt=0.00"
        )
    )

    case1_folder = glob.glob(
        os.path.join(
            results_root,
            case2
            #"results_*_RQ1.1_Batt=1.00"
        )
    )

    if len(case0_folder) == 0:
        raise FileNotFoundError(
            "No folder found for Batt=0.00"
        )

    if len(case1_folder) == 0:
        raise FileNotFoundError(
            "No folder found for Batt=1.00"
        )

    case0 = pd.read_csv(
        os.path.join(
            case0_folder[0],
            "voltage_profiles.csv"
        )
    )

    case1 = pd.read_csv(
        os.path.join(
            case1_folder[0],
            "voltage_profiles.csv"
        )
    )

    # --------------------------------------------------
    # IMPORTANT:
    # v_sq_pu actually contains sqrt(voltage)
    # --------------------------------------------------

    V_COL = "v_sq_pu"

    # --------------------------------------------------
    # BUS 14 ONLY
    # --------------------------------------------------

    bus = chosen_bus

    v0_bus = (
        case0[case0["bus"] == bus]
        .sort_values("time")[V_COL]
        .reset_index(drop=True)
    )

    v1_bus = (
        case1[case1["bus"] == bus]
        .sort_values("time")[V_COL]
        .reset_index(drop=True)
    )

    # --------------------------------------------------
    # Summary statistics
    # --------------------------------------------------

    summary = pd.DataFrame({
        "Metric": [
            "Mean",
            "Min",
            "Max",
            "1st Percentile",
            "99th Percentile",
            "Std Dev"
        ],
        "0 Batteries": [
            v0_bus.mean(),
            v0_bus.min(),
            v0_bus.max(),
            v0_bus.quantile(0.01),
            v0_bus.quantile(0.99),
            v0_bus.std()
        ],
        "1 Battery": [
            v1_bus.mean(),
            v1_bus.min(),
            v1_bus.max(),
            v1_bus.quantile(0.01),
            v1_bus.quantile(0.99),
            v1_bus.std()
        ]
    })

    print("\n==============================")
    print(f"BUS {chosen_bus:.2f} VOLTAGE STATISTICS")
    print("==============================")
    print(summary.round(5).to_string(index=False))

    # --------------------------------------------------
    # Difference statistics
    # --------------------------------------------------

    delta = v1_bus - v0_bus

    print("\n==============================")
    print("CHANGE DUE TO BATTERY")
    print("==============================")
    print(f"Mean voltage change : {delta.mean():.6f}")
    print(f"Maximum increase    : {delta.max():.6f}")
    print(f"Maximum decrease    : {delta.min():.6f}")
    print(f"Std difference      : {delta.std():.6f}")

    # --------------------------------------------------
    # Voltage violations
    # --------------------------------------------------

    viol0 = ((v0_bus < 0.95) | (v0_bus > 1.05)).sum()
    viol1 = ((v1_bus < 0.95) | (v1_bus > 1.05)).sum()

    print("\n==============================")
    print("VOLTAGE VIOLATIONS")
    print("==============================")
    print(f"0 batteries : {viol0}")
    print(f"1 battery   : {viol1}")

    # # --------------------------------------------------
    # # Time series
    # # --------------------------------------------------

    # plt.figure(figsize=(12, 5))

    # plt.plot(
    #     v0_bus.values,
    #     label="B0 | E100",
    #     linewidth=1
    # )

    # plt.plot(
    #     v1_bus.values,
    #     label="B2 | E250",
    #     linewidth=1
    # )

    # plt.axhline(
    #     0.95,
    #     linestyle="--"
    # )

    # plt.axhline(
    #     1.05,
    #     linestyle="--"
    # )

    # plt.title(f"Voltage Profile Comparison - Bus {chosen_bus}")
    # plt.xlabel("Hour")
    # plt.ylabel("Voltage [p.u.]")
    # plt.grid(True)
    # plt.legend()
    # plt.tight_layout()
    # plt.show()

    # --------------------------------------------------
    # Histogram
    # --------------------------------------------------

    plt.figure(figsize=(8, 5))

    plt.hist(
        v0_bus,
        bins=50,
        alpha=0.5,
        label="B0 | E125"
    )

    plt.hist(
        v1_bus,
        bins=50,
        alpha=0.5,
        label="B2 | E175"
    )

    plt.axvline(
        0.95,
        linestyle="--"
    )

    plt.axvline(
        1.05,
        linestyle="--"
    )

    plt.xlabel("Voltage [p.u.]")
    plt.ylabel("Frequency")
    plt.title(f"Voltage Distribution Comparison - Bus {chosen_bus}")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()

    return summary



def _resolve_folder(pattern):
    matches = glob.glob(pattern)
    if len(matches) == 0:
        raise FileNotFoundError(f"No folder found for pattern: {pattern}")
    if len(matches) > 1:
        print(f"[WARNING] multiple matches, using first: {matches[0]}")
    return matches[0]

def compare_line_loading(scenario1, scenario2, from_bus, to_bus):

    folder1 = _resolve_folder(scenario1)
    folder2 = _resolve_folder(scenario2)

    df1 = pd.read_csv(os.path.join(folder1, "line_flows.csv"))
    df2 = pd.read_csv(os.path.join(folder2, "line_flows.csv"))

    p95_1 = (
        df1.groupby(["from_bus", "to_bus"])["loading_percent"]
        .quantile(0.95)
        .reset_index(name="P95_Scenario1")
    )

    p95_2 = (
        df2.groupby(["from_bus", "to_bus"])["loading_percent"]
        .quantile(0.95)
        .reset_index(name="P95_Scenario2")
    )

    comparison = (
        p95_1.merge(
            p95_2,
            on=["from_bus", "to_bus"],
            how="outer"
        )
    )

    comparison["Difference"] = (
        comparison["P95_Scenario2"]
        - comparison["P95_Scenario1"]
    )

    comparison = comparison.sort_values(
        "Difference",
        ascending=False
    )

    print(comparison.round(2))

    line1 = df1[(df1["from_bus"] == from_bus) & (df1["to_bus"] == to_bus)]["loading_percent"]
    line2 = df2[(df2["from_bus"] == from_bus) & (df2["to_bus"] == to_bus)]["loading_percent"]

    summary = pd.DataFrame({
        "Metric": ["Mean","Min","Max","1st Percentile","99th Percentile","Std Dev"],
        "Scenario 1": [
            line1.mean(),
            line1.min(),
            line1.max(),
            line1.quantile(0.01),
            line1.quantile(0.99),
            line1.std()
        ],
        "Scenario 2": [
            line2.mean(),
            line2.min(),
            line2.max(),
            line2.quantile(0.01),
            line2.quantile(0.99),
            line2.std()
        ]
    })

    print("\n==============================")
    print(f"LINE {from_bus} → {to_bus}")
    print("==============================")
    print(summary.round(3).to_string(index=False))

    overload1 = (line1 > 100).sum()
    overload2 = (line2 > 100).sum()

    print("\nOverload hours:")
    print(f"Scenario 1: {overload1}")
    print(f"Scenario 2: {overload2}")

    

    plt.figure(figsize=(8, 5))

    plt.hist(line1,bins=50,alpha=0.5,label="B1 | Battery at bus 37")
    plt.hist(line2, bins=50,alpha=0.5, label="B2 | Battery at bus 34 & 38")
    plt.axvline(100,linestyle="--")
    plt.xlabel("Loading [%]")
    plt.ylabel("Frequency")

    plt.title(
        f"E250 - Loading Distribution ({from_bus} → {to_bus})"
    )

    plt.legend()
    plt.grid(True)

    plt.tight_layout()
    plt.show()


import os
import glob
import pandas as pd
import matplotlib.pyplot as plt


def plot_worst_voltage_week_rq12(
    results_root=".",
    data_root="data",
    electrification=1.50,
    pv_share=1.25,
    batteries=1.00,
    bus=39,
    week_hours=168,
    s_base_kva=1000,
    save_path=None
):
    """
    Finds and plots the worst voltage week for one RQ1.2 scenario.

    Worst week = rolling 168-hour window with the lowest average voltage
    at the selected bus.

    Uses:
        voltage_profiles.csv  -> bus,time,v_pu,v_sq_pu
        soc.csv               -> bus,time,SOC_kWh,Charge_kW,Discharge_kW
        data/pD_*.csv         -> bus,time,pD_pu
        data/PV_*.csv         -> bus,time,PV_pu
    """

    # -----------------------------
    # Find scenario folder
    # -----------------------------
    scenario_pattern = (
        f"results_*_RQ1.2_Batt={batteries:.2f}"
        f"_elec={electrification:.2f}_P={pv_share:.2f}"
    )

    folders = glob.glob(
        os.path.join(results_root, scenario_pattern)
    )

    if len(folders) == 0:
        raise FileNotFoundError(
            f"No result folder found for pattern: {scenario_pattern}"
        )

    folder = folders[0]

    print("\n======================================")
    print("WORST VOLTAGE WEEK ANALYSIS")
    print(f"Scenario folder: {os.path.basename(folder)}")
    print(f"Bus: {bus}")
    print("======================================")

    # -----------------------------
    # Load voltage
    # -----------------------------
    voltage_file = os.path.join(folder, "voltage_profiles.csv")
    df_v = pd.read_csv(voltage_file)

    # Use v_sq_pu because your export stores voltage magnitude there
    voltage_col = "v_sq_pu"

    df_v_bus = (
        df_v[df_v["bus"] == bus]
        .sort_values("time")
        .copy()
    )

    if df_v_bus.empty:
        raise ValueError(f"Bus {bus} not found in voltage file.")

    # -----------------------------
    # Find worst week
    # -----------------------------
    df_v_bus["rolling_mean_v"] = (
        df_v_bus[voltage_col]
        .rolling(window=week_hours, min_periods=week_hours)
        .mean()
    )

    worst_end_time = int(
        df_v_bus.loc[
            df_v_bus["rolling_mean_v"].idxmin(),
            "time"
        ]
    )

    week_start = worst_end_time - week_hours + 1
    week_end = worst_end_time

    print(f"Worst week: t = {week_start} to {week_end}")

    hours = list(range(week_start, week_end + 1))

    plot_df = pd.DataFrame({"time": hours})

    plot_df = plot_df.merge(
        df_v_bus[df_v_bus["time"].isin(hours)][["time", voltage_col]],
        on="time",
        how="left"
    )

    plot_df = plot_df.rename(
        columns={voltage_col: "voltage_pu"}
    )

    # -----------------------------
    # Load battery operation
    # -----------------------------
    soc_file = os.path.join(folder, "soc.csv")
    df_soc = pd.read_csv(soc_file)

    df_soc_bus = (
        df_soc[df_soc["bus"] == bus]
        .sort_values("time")
        .copy()
    )

    plot_df = plot_df.merge(
        df_soc_bus[
            df_soc_bus["time"].isin(hours)
        ][["time", "SOC_kWh", "Charge_kW", "Discharge_kW"]],
        on="time",
        how="left"
    )

    plot_df[["SOC_kWh", "Charge_kW", "Discharge_kW"]] = (
        plot_df[["SOC_kWh", "Charge_kW", "Discharge_kW"]]
        .fillna(0)
    )

    # -----------------------------
    # Load demand
    # -----------------------------
    demand_file = os.path.join(
        data_root,
        f"pD_elec={electrification:.2f}_PV={pv_share:.2f}.csv"
    )

    df_d = pd.read_csv(demand_file)

    df_d_bus = (
        df_d[df_d["bus"] == bus]
        .sort_values("time")
        .copy()
    )

    plot_df = plot_df.merge(
        df_d_bus[
            df_d_bus["time"].isin(hours)
        ][["time", "pD_pu"]],
        on="time",
        how="left"
    )

    plot_df["Demand_kW"] = plot_df["pD_pu"] * s_base_kva

    # -----------------------------
    # Load PV
    # -----------------------------
    pv_file = os.path.join(
        data_root,
        f"PV_elec={electrification:.2f}_PV={pv_share:.2f}.csv"
    )

    df_pv = pd.read_csv(pv_file)

    df_pv_bus = (
        df_pv[df_pv["bus"] == bus]
        .sort_values("time")
        .copy()
    )

    plot_df = plot_df.merge(
        df_pv_bus[
            df_pv_bus["time"].isin(hours)
        ][["time", "PV_pu"]],
        on="time",
        how="left"
    )

    plot_df["PV_kW"] = plot_df["PV_pu"] * s_base_kva

    # -----------------------------
    # Relative week hour
    # -----------------------------
    plot_df["hour_of_week"] = plot_df["time"] - week_start

    # -----------------------------
    # Print diagnostics
    # -----------------------------
    print("\nVoltage summary selected week:")
    print(
        plot_df["voltage_pu"]
        .describe(percentiles=[0.01, 0.05, 0.95, 0.99])
        .round(4)
        .to_string()
    )

    print("\nWeekly energy summary [kWh]:")
    print(f"Demand        : {plot_df['Demand_kW'].sum():.2f}")
    print(f"PV generation : {plot_df['PV_kW'].sum():.2f}")
    print(f"Charge        : {plot_df['Charge_kW'].sum():.2f}")
    print(f"Discharge     : {plot_df['Discharge_kW'].sum():.2f}")

    # -----------------------------
    # Cleaner plot: voltage + battery operation only
    # -----------------------------
    fig, ax1 = plt.subplots(figsize=(14, 5))

    # Voltage
    ax1.plot(
        plot_df["hour_of_week"],
        plot_df["voltage_pu"],
        linewidth=2,
        label=f"Voltage at bus {bus}"
    )

    ax1.axhline(0.95, linestyle="--", linewidth=1, label="Voltage limits")
    ax1.axhline(1.05, linestyle="--", linewidth=1)

    ax1.set_xlabel("Hour of selected week")
    ax1.set_ylabel("Voltage [p.u.]")
    ax1.set_ylim(0.92, 1.06)
    ax1.grid(True, alpha=0.4)

    # Battery operation
    ax2 = ax1.twinx()

    ax2.fill_between(
        plot_df["hour_of_week"],
        0,
        plot_df["Charge_kW"],
        alpha=0.25,
        label="Battery charge"
    )

    ax2.fill_between(
        plot_df["hour_of_week"],
        0,
        -plot_df["Discharge_kW"],
        alpha=0.25,
        label="Battery discharge"
    )

    ax2.set_ylabel("Battery power [kW]")

    # Combined legend
    lines_1, labels_1 = ax1.get_legend_handles_labels()
    lines_2, labels_2 = ax2.get_legend_handles_labels()

    ax1.legend(
        lines_1 + lines_2,
        labels_1 + labels_2,
        loc="lower right"
    )

    plt.title(
        f"Worst voltage week at bus {bus} "
        f"(E{electrification:.2f}, PV{pv_share:.2f}, B{batteries:.0f})"
    )

    plt.tight_layout()
    plt.show()

    return plot_df

import os
import glob
import pandas as pd
import matplotlib.pyplot as plt


def plot_average_voltage_battery_behavior_rq12(
    results_root=".",
    data_root="data",
    electrification=1.50,
    pv_share=1.25,
    batteries=1.00,
    bus=39,
    s_base_kva=1000,
    save_path=None
):
    """
    Plots average daily voltage and battery behaviour for one RQ1.2 scenario
    at a selected bus.

    Uses:
        voltage_profiles.csv  -> bus,time,v_pu,v_sq_pu
        soc.csv               -> bus,time,SOC_kWh,Charge_kW,Discharge_kW
        data/pD_*.csv         -> bus,time,pD_pu
        data/PV_*.csv         -> bus,time,PV_pu

    Note:
        v_sq_pu is used because in this project export it stores voltage magnitude.
    """

    # -----------------------------
    # Find scenario folder
    # -----------------------------
    scenario_pattern = (
        f"results_*_RQ1.2_Batt={batteries:.2f}"
        f"_elec={electrification:.2f}_P={pv_share:.2f}"
    )

    folders = glob.glob(
        os.path.join(results_root, scenario_pattern)
    )

    if len(folders) == 0:
        raise FileNotFoundError(
            f"No result folder found for pattern: {scenario_pattern}"
        )

    folder = folders[0]

    print("\n======================================")
    print("AVERAGE VOLTAGE AND BATTERY BEHAVIOUR")
    print(f"Scenario folder: {os.path.basename(folder)}")
    print(f"Bus: {bus}")
    print("======================================")

    # -----------------------------
    # Load voltage
    # -----------------------------
    voltage_file = os.path.join(folder, "voltage_profiles.csv")
    df_v = pd.read_csv(voltage_file)

    voltage_col = "v_sq_pu"

    df_v_bus = (
        df_v[df_v["bus"] == bus]
        .sort_values("time")
        .copy()
    )

    if df_v_bus.empty:
        raise ValueError(f"Bus {bus} not found in voltage_profiles.csv.")

    df_v_bus["hour_of_day"] = df_v_bus["time"] % 24

    avg_voltage = (
        df_v_bus
        .groupby("hour_of_day")[voltage_col]
        .mean()
        .reset_index()
        .rename(columns={voltage_col: "voltage_pu"})
    )

    # -----------------------------
    # Load battery operation
    # -----------------------------
    soc_file = os.path.join(folder, "soc.csv")
    df_soc = pd.read_csv(soc_file)

    df_soc_bus = (
        df_soc[df_soc["bus"] == bus]
        .sort_values("time")
        .copy()
    )

    if df_soc_bus.empty:
        avg_soc = pd.DataFrame({
            "hour_of_day": range(24),
            "SOC_kWh": 0.0,
            "Charge_kW": 0.0,
            "Discharge_kW": 0.0
        })
    else:
        df_soc_bus["hour_of_day"] = df_soc_bus["time"] % 24

        avg_soc = (
            df_soc_bus
            .groupby("hour_of_day")[["SOC_kWh", "Charge_kW", "Discharge_kW"]]
            .mean()
            .reset_index()
        )

    # -----------------------------
    # Load demand
    # -----------------------------
    demand_file = os.path.join(
        data_root,
        f"pD_elec={electrification:.2f}_PV={pv_share:.2f}.csv"
    )

    df_d = pd.read_csv(demand_file)

    df_d_bus = (
        df_d[df_d["bus"] == bus]
        .sort_values("time")
        .copy()
    )

    df_d_bus["hour_of_day"] = df_d_bus["time"] % 24
    df_d_bus["Demand_kW"] = df_d_bus["pD_pu"] * s_base_kva

    avg_demand = (
        df_d_bus
        .groupby("hour_of_day")["Demand_kW"]
        .mean()
        .reset_index()
    )

    # -----------------------------
    # Load PV
    # -----------------------------
    pv_file = os.path.join(
        data_root,
        f"PV_elec={electrification:.2f}_PV={pv_share:.2f}.csv"
    )

    df_pv = pd.read_csv(pv_file)

    df_pv_bus = (
        df_pv[df_pv["bus"] == bus]
        .sort_values("time")
        .copy()
    )

    df_pv_bus["hour_of_day"] = df_pv_bus["time"] % 24
    df_pv_bus["PV_kW"] = df_pv_bus["PV_pu"] * s_base_kva

    avg_pv = (
        df_pv_bus
        .groupby("hour_of_day")["PV_kW"]
        .mean()
        .reset_index()
    )

    # -----------------------------
    # Merge average profiles
    # -----------------------------
    plot_df = avg_voltage.merge(
        avg_soc,
        on="hour_of_day",
        how="left"
    )

    plot_df = plot_df.merge(
        avg_demand,
        on="hour_of_day",
        how="left"
    )

    plot_df = plot_df.merge(
        avg_pv,
        on="hour_of_day",
        how="left"
    )

    plot_df = plot_df.fillna(0)

    # -----------------------------
    # Print diagnostics
    # -----------------------------
    print("\nAverage daily voltage summary:")
    print(
        plot_df["voltage_pu"]
        .describe()
        .round(4)
        .to_string()
    )

    print("\nAverage daily energy summary [kWh/day]:")
    print(f"Demand        : {plot_df['Demand_kW'].sum():.2f}")
    print(f"PV generation : {plot_df['PV_kW'].sum():.2f}")
    print(f"Charge        : {plot_df['Charge_kW'].sum():.2f}")
    print(f"Discharge     : {plot_df['Discharge_kW'].sum():.2f}")

    # -----------------------------
    # Plot
    # -----------------------------
    fig, ax1 = plt.subplots(figsize=(12, 5))

    ax1.plot(
        plot_df["hour_of_day"],
        plot_df["voltage_pu"],
        linewidth=2,
        label=f"Average voltage at bus {bus}"
    )

    ax1.axhline(
        0.95,
        linestyle="--",
        linewidth=1,
        label="Voltage limits"
    )

    ax1.axhline(
        1.05,
        linestyle="--",
        linewidth=1
    )

    ax1.set_xlabel("Hour of day")
    ax1.set_ylabel("Voltage [p.u.]")
    ax1.set_ylim(0.92, 1.06)
    ax1.grid(True, alpha=0.4)

    ax2 = ax1.twinx()

    ax2.plot(
        plot_df["hour_of_day"],
        plot_df["Charge_kW"],
        linewidth=1.5,
        label="Average battery charge"
    )

    ax2.plot(
        plot_df["hour_of_day"],
        -plot_df["Discharge_kW"],
        linewidth=1.5,
        label="Average battery discharge"
    )

    ax2.plot(
        plot_df["hour_of_day"],
        plot_df["PV_kW"],
        linewidth=1.2,
        linestyle=":",
        label="Average PV generation"
    )

    ax2.plot(
        plot_df["hour_of_day"],
        plot_df["Demand_kW"],
        linewidth=1.2,
        linestyle=":",
        label="Average demand"
    )

    ax2.set_ylabel("Power [kW]")

    lines_1, labels_1 = ax1.get_legend_handles_labels()
    lines_2, labels_2 = ax2.get_legend_handles_labels()

    ax1.legend(
        lines_1 + lines_2,
        labels_1 + labels_2,
        loc="best"
    )

    plt.title(
        f"Average daily voltage and battery behaviour at bus {bus} "
        f"(E{electrification:.2f}, PV{pv_share:.2f}, B{batteries:.0f})"
    )

    plt.tight_layout()

    if save_path is not None:
        plt.savefig(save_path, dpi=300, bbox_inches="tight")
        print(f"Saved figure to: {save_path}")

    plt.show()

    return plot_df


import os
import glob
import pandas as pd
import matplotlib.pyplot as plt


def plot_average_worst_voltage_days_rq12(
    results_root=".",
    data_root="data",
    electrification=1.50,
    pv_share=1.25,
    batteries=1.00,
    bus=39,
    n_worst_days=20,
    s_base_kva=1000,
    save_path=None
):
    """
    Finds the n worst voltage days at a selected bus and plots the average
    daily voltage and battery behaviour over those days.

    Worst days are selected by the lowest daily minimum voltage at the bus.

    Uses:
        voltage_profiles.csv  -> bus,time,v_pu,v_sq_pu
        soc.csv               -> bus,time,SOC_kWh,Charge_kW,Discharge_kW
        data/pD_*.csv         -> bus,time,pD_pu
        data/PV_*.csv         -> bus,time,PV_pu

    Note:
        v_sq_pu is used because in your export this column stores voltage magnitude.
    """

    # -----------------------------
    # Find scenario folder
    # -----------------------------
    scenario_pattern = (
        f"results_*_RQ1.2_Batt={batteries:.2f}"
        f"_elec={electrification:.2f}_P={pv_share:.2f}"
    )

    folders = glob.glob(
        os.path.join(results_root, scenario_pattern)
    )

    if len(folders) == 0:
        raise FileNotFoundError(
            f"No result folder found for pattern: {scenario_pattern}"
        )

    folder = folders[0]

    print("\n======================================")
    print("AVERAGE WORST VOLTAGE DAYS ANALYSIS")
    print(f"Scenario folder: {os.path.basename(folder)}")
    print(f"Bus: {bus}")
    print(f"Worst days selected: {n_worst_days}")
    print("======================================")

    # -----------------------------
    # Load voltage
    # -----------------------------
    voltage_file = os.path.join(folder, "voltage_profiles.csv")

    df_v = pd.read_csv(voltage_file)

    voltage_col = "v_sq_pu"

    df_v_bus = (
        df_v[df_v["bus"] == bus]
        .sort_values("time")
        .copy()
    )

    if df_v_bus.empty:
        raise ValueError(f"Bus {bus} not found in voltage_profiles.csv.")

    df_v_bus["day"] = df_v_bus["time"] // 24
    df_v_bus["hour_of_day"] = df_v_bus["time"] % 24

    # -----------------------------
    # Select worst voltage days
    # -----------------------------
    daily_voltage = (
        df_v_bus
        .groupby("day")
        .agg(
            daily_min_v=(voltage_col, "min"),
            daily_mean_v=(voltage_col, "mean")
        )
        .reset_index()
    )

    worst_days = (
        daily_voltage
        .sort_values(["daily_min_v", "daily_mean_v"], ascending=[True, True])
        .head(n_worst_days)["day"]
        .tolist()
    )

    print("\nSelected worst days:")
    print(worst_days)

    df_v_worst = df_v_bus[
        df_v_bus["day"].isin(worst_days)
    ].copy()

    avg_voltage = (
        df_v_worst
        .groupby("hour_of_day")[voltage_col]
        .mean()
        .reset_index()
        .rename(columns={voltage_col: "voltage_pu"})
    )

    # -----------------------------
    # Load battery operation
    # -----------------------------
    soc_file = os.path.join(folder, "soc.csv")
    df_soc = pd.read_csv(soc_file)

    df_soc_bus = (
        df_soc[df_soc["bus"] == bus]
        .sort_values("time")
        .copy()
    )

    if df_soc_bus.empty:
        avg_soc = pd.DataFrame({
            "hour_of_day": range(24),
            "SOC_kWh": 0.0,
            "Charge_kW": 0.0,
            "Discharge_kW": 0.0
        })
    else:
        df_soc_bus["day"] = df_soc_bus["time"] // 24
        df_soc_bus["hour_of_day"] = df_soc_bus["time"] % 24

        df_soc_worst = df_soc_bus[
            df_soc_bus["day"].isin(worst_days)
        ].copy()

        avg_soc = (
            df_soc_worst
            .groupby("hour_of_day")[["SOC_kWh", "Charge_kW", "Discharge_kW"]]
            .mean()
            .reset_index()
        )

    # -----------------------------
    # Load demand
    # -----------------------------
    demand_file = os.path.join(
        data_root,
        f"pD_elec={electrification:.2f}_PV={pv_share:.2f}.csv"
    )

    df_d = pd.read_csv(demand_file)

    df_d_bus = (
        df_d[df_d["bus"] == bus]
        .sort_values("time")
        .copy()
    )

    df_d_bus["day"] = df_d_bus["time"] // 24
    df_d_bus["hour_of_day"] = df_d_bus["time"] % 24
    df_d_bus["Demand_kW"] = df_d_bus["pD_pu"] * s_base_kva

    df_d_worst = df_d_bus[
        df_d_bus["day"].isin(worst_days)
    ].copy()

    avg_demand = (
        df_d_worst
        .groupby("hour_of_day")["Demand_kW"]
        .mean()
        .reset_index()
    )

    # -----------------------------
    # Load PV
    # -----------------------------
    pv_file = os.path.join(
        data_root,
        f"PV_elec={electrification:.2f}_PV={pv_share:.2f}.csv"
    )

    df_pv = pd.read_csv(pv_file)

    df_pv_bus = (
        df_pv[df_pv["bus"] == bus]
        .sort_values("time")
        .copy()
    )

    df_pv_bus["day"] = df_pv_bus["time"] // 24
    df_pv_bus["hour_of_day"] = df_pv_bus["time"] % 24
    df_pv_bus["PV_kW"] = df_pv_bus["PV_pu"] * s_base_kva

    df_pv_worst = df_pv_bus[
        df_pv_bus["day"].isin(worst_days)
    ].copy()

    avg_pv = (
        df_pv_worst
        .groupby("hour_of_day")["PV_kW"]
        .mean()
        .reset_index()
    )

    # -----------------------------
    # Merge average profiles
    # -----------------------------
    plot_df = avg_voltage.merge(
        avg_soc,
        on="hour_of_day",
        how="left"
    )

    plot_df = plot_df.merge(
        avg_demand,
        on="hour_of_day",
        how="left"
    )

    plot_df = plot_df.merge(
        avg_pv,
        on="hour_of_day",
        how="left"
    )

    plot_df = plot_df.fillna(0)

    # -----------------------------
    # Diagnostics
    # -----------------------------
    print("\nVoltage summary over selected worst days:")
    print(
        df_v_worst[voltage_col]
        .describe(percentiles=[0.01, 0.05, 0.95, 0.99])
        .round(4)
        .to_string()
    )

    print("\nAverage daily energy over selected worst days [kWh/day]:")
    print(f"Demand        : {plot_df['Demand_kW'].sum():.2f}")
    print(f"PV generation : {plot_df['PV_kW'].sum():.2f}")
    print(f"Charge        : {plot_df['Charge_kW'].sum():.2f}")
    print(f"Discharge     : {plot_df['Discharge_kW'].sum():.2f}")

    # -----------------------------
    # Plot
    # -----------------------------
    fig, ax1 = plt.subplots(figsize=(12, 5))

    ax1.plot(
        plot_df["hour_of_day"],
        plot_df["voltage_pu"],
        linewidth=2,
        label=f"Average voltage at bus {bus}"
    )

    ax1.axhline(
        0.95,
        linestyle="--",
        linewidth=1,
        label="Voltage limits"
    )

    ax1.axhline(
        1.05,
        linestyle="--",
        linewidth=1
    )

    ax1.set_xlabel("Hour of day")
    ax1.set_ylabel("Voltage [p.u.]")
    ax1.set_ylim(0.92, 1.06)
    ax1.grid(True, alpha=0.4)

    ax2 = ax1.twinx()

    ax2.fill_between(
        plot_df["hour_of_day"],
        0,
        plot_df["Charge_kW"],
        alpha=0.25,
        label="Average battery charge"
    )

    ax2.fill_between(
        plot_df["hour_of_day"],
        0,
        -plot_df["Discharge_kW"],
        alpha=0.25,
        label="Average battery discharge"
    )

    ax2.plot(
        plot_df["hour_of_day"],
        plot_df["PV_kW"],
        linewidth=1.3,
        linestyle=":",
        label="Average PV generation"
    )

    ax2.plot(
        plot_df["hour_of_day"],
        plot_df["Demand_kW"],
        linewidth=1.3,
        linestyle=":",
        label="Average demand"
    )

    ax2.set_ylabel("Power [kW]")

    lines_1, labels_1 = ax1.get_legend_handles_labels()
    lines_2, labels_2 = ax2.get_legend_handles_labels()

    ax1.legend(
        lines_1 + lines_2,
        labels_1 + labels_2,
        loc="best"
    )

    plt.title(
        f"Average behaviour during {n_worst_days} worst voltage days at bus {bus} "
        f"(E{electrification:.2f}, PV{pv_share:.2f}, B{batteries:.0f})"
    )

    plt.tight_layout()

    if save_path is not None:
        plt.savefig(save_path, dpi=300, bbox_inches="tight")
        print(f"Saved figure to: {save_path}")

    plt.show()

    return plot_df, worst_days

import os
import glob
import pandas as pd
import matplotlib.pyplot as plt


def plot_soc_comparison_rq12(
    results_root=".",
    electrification=1.75,
    pv_share=1.38,
    summer_start_day=180,
    summer_week_hours=168,
    save_dir=None
):
    """
    Compares battery state-of-charge for:
        - B1: sum SOC of the one installed battery
        - B2: sum SOC of the two installed batteries

    Creates two plots:
        1. One representative summer week
        2. Average weekly SOC profile over the full year

    Required file:
        soc.csv with columns:
            bus,time,SOC_kWh,Charge_kW,Discharge_kW
    """

    def find_result_folder(batteries):
        pattern = (
            f"results_*_RQ1.2_Batt={batteries:.2f}"
            f"_elec={electrification:.2f}_P={pv_share:.2f}"
        )

        folders = glob.glob(os.path.join(results_root, pattern))

        if len(folders) == 0:
            raise FileNotFoundError(
                f"No result folder found for pattern: {pattern}"
            )

        return folders[0]

    def load_total_soc(folder):
        soc_file = os.path.join(folder, "soc.csv")

        if not os.path.exists(soc_file):
            raise FileNotFoundError(f"Missing soc.csv in {folder}")

        df = pd.read_csv(soc_file)

        required_cols = {"bus", "time", "SOC_kWh"}
        missing = required_cols - set(df.columns)

        if missing:
            raise ValueError(f"soc.csv is missing columns: {missing}")

        df_total = (
            df.groupby("time", as_index=False)["SOC_kWh"]
            .sum()
            .sort_values("time")
        )

        return df_total

    # --------------------------------------------------
    # Load B1 and B2 SOC
    # --------------------------------------------------
    folder_b1 = find_result_folder(1.00)
    folder_b2 = find_result_folder(2.00)

    print("\n======================================")
    print("SOC COMPARISON RQ1.2")
    print(f"B1 folder: {os.path.basename(folder_b1)}")
    print(f"B2 folder: {os.path.basename(folder_b2)}")
    print("======================================")

    soc_b1 = load_total_soc(folder_b1).rename(
        columns={"SOC_kWh": "SOC_B1_kWh"}
    )

    soc_b2 = load_total_soc(folder_b2).rename(
        columns={"SOC_kWh": "SOC_B2_kWh"}
    )

    df = soc_b1.merge(
        soc_b2,
        on="time",
        how="inner"
    )

    # --------------------------------------------------
    # Plot 1: Summer week
    # --------------------------------------------------
    summer_start_hour = summer_start_day * 24
    summer_end_hour = summer_start_hour + summer_week_hours - 1

    summer_df = df[
        (df["time"] >= summer_start_hour) &
        (df["time"] <= summer_end_hour)
    ].copy()

    if summer_df.empty:
        raise ValueError(
            "Summer week selection is empty. "
            "Check summer_start_day and time index."
        )

    summer_df["hour_of_week"] = (
        summer_df["time"] - summer_start_hour
    )

    fig, ax = plt.subplots(figsize=(13, 5))

    ax.plot(
        summer_df["hour_of_week"],
        summer_df["SOC_B1_kWh"],
        linewidth=2,
        label="SOC, one battery"
    )

    ax.plot(
        summer_df["hour_of_week"],
        summer_df["SOC_B2_kWh"],
        linewidth=2,
        label="SOC, two batteries combined"
    )

    ax.set_xlabel("Hour of selected summer week")
    ax.set_ylabel("State of charge [kWh]")
    ax.set_title(
        f"Battery state of charge during summer week "
        f"(E{electrification:.2f}, PV{pv_share:.2f})"
    )
    ax.grid(True, alpha=0.4)
    ax.legend(loc="best")

    plt.tight_layout()

    if save_dir is not None:
        os.makedirs(save_dir, exist_ok=True)
        summer_path = os.path.join(
            save_dir,
            f"SOC_summer_week_E{electrification:.2f}_PV{pv_share:.2f}.png"
        )
        plt.savefig(summer_path, dpi=300, bbox_inches="tight")
        print(f"Saved summer week figure to: {summer_path}")

    plt.show()

    # --------------------------------------------------
    # Plot 2: Average week over full year
    # --------------------------------------------------
    df["hour_of_week"] = df["time"] % 168

    avg_week_df = (
        df.groupby("hour_of_week", as_index=False)
        [["SOC_B1_kWh", "SOC_B2_kWh"]]
        .mean()
    )

    fig, ax = plt.subplots(figsize=(13, 5))

    ax.plot(
        avg_week_df["hour_of_week"],
        avg_week_df["SOC_B1_kWh"],
        linewidth=2,
        label="SOC, one battery"
    )

    ax.plot(
        avg_week_df["hour_of_week"],
        avg_week_df["SOC_B2_kWh"],
        linewidth=2,
        label="SOC, two batteries combined"
    )

    ax.set_xlabel("Hour of average week")
    ax.set_ylabel("Average state of charge [kWh]")
    ax.set_title(
        f"Average weekly battery state of charge "
        f"(E{electrification:.2f}, PV{pv_share:.2f})"
    )
    ax.grid(True, alpha=0.4)
    ax.legend(loc="best")

    plt.tight_layout()

    if save_dir is not None:
        avg_path = os.path.join(
            save_dir,
            f"SOC_average_week_E{electrification:.2f}_PV{pv_share:.2f}.png"
        )
        plt.savefig(avg_path, dpi=300, bbox_inches="tight")
        print(f"Saved average week figure to: {avg_path}")

    plt.show()

    # --------------------------------------------------
    # Diagnostics
    # --------------------------------------------------
    print("\nSOC summary:")
    print(
        df[["SOC_B1_kWh", "SOC_B2_kWh"]]
        .describe()
        .round(2)
        .to_string()
    )

    return summer_df, avg_week_df

# summarize_battery_locations()
# summarize_voltage_profiles(results_root=".")
# weakest_bus_summary(".","RQ1.2")
# voltage_checker(case1="results_*_RQ1.2_Batt=1.00_elec=2.50_*",
#                 case2="results_*_RQ1.2_Batt=2.00_elec=2.50_*",
#                 chosen_bus=14)



# compare_line_loading(
#     # scenario1="resulXts_0605_1037_RQ1_Batt=0.00",   #"results_0528_1632_RQ1.1_Batt=0.00",
#     # scenario2="results_0603_1404_RQ1.1_Batt=1.00",   #"results_0528_1711_RQ1.1_Batt=1.00"
#     scenario1="results_*_RQ1.2_Batt=0.00_elec=1.25_*",
#     scenario2="results_*_RQ1.2_Batt=2.00_elec=1.50_*",
#     from_bus=14,
#     to_bus=34
# )

# worst_week_df = plot_worst_voltage_week_rq12(
#     results_root=".",
#     data_root="data",
#     electrification=1.75,
#     pv_share=1.375,
#     batteries=1.00,
#     bus=39,
#     save_path="worst_voltage_week_E150_P125_B1_bus39.png"
# )

# avg_df = plot_average_voltage_battery_behavior_rq12(
#     results_root=".",
#     data_root="data",
#     electrification=1.75,
#     pv_share=1.38,
#     batteries=1.00,
#     bus=39,
#     save_path="avg_voltage_battery_bus39_E175_B1.png"
# )

# DEZE HEB IK GEBRUIKT VOOR 2 PLOTS VOOR CHAPTER 5.2
# avg_worst_days_df, worst_days = plot_average_worst_voltage_days_rq12(
#     results_root=".",
#     data_root="data",
#     electrification=2.00,#1.75,
#     pv_share=1.50,
#     batteries=1.00,
#     bus=39,
#     n_worst_days=30,
#     save_path="avg_20_worst_voltage_days_bus39_E200_B1.png"
# )

summer_soc_df, avg_week_soc_df = plot_soc_comparison_rq12(
    results_root=".",
    electrification=2.50,
    pv_share=1.75,
    summer_start_day=180,
    save_dir="figures"
)