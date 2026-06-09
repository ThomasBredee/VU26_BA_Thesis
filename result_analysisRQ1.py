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
            "results_*_RQ1.2_Batt=*"
        )
    )

    for folder in folders:

        try:

            folder_name = os.path.basename(folder)

            batt_match = re.search(
                r"Batt=([\d\.]+)",
                folder_name
            )

            if batt_match:
                num_batts = float(
                    batt_match.group(1)
                )
            else:
                continue

            battery_file = os.path.join(
                folder,
                "batteries.csv"
            )

            if not os.path.exists(battery_file):
                continue

            df = pd.read_csv(battery_file)

            # --------------------------
            # Detect installed batteries
            # --------------------------
            if "battery_installed" in df.columns:
                df = df[df["battery_installed"] > 0]

            if len(df) == 0:
                continue

            # --------------------------
            # One row per battery
            # --------------------------
            for _, row in df.iterrows():

                rows.append({
                    "Allowed_Batteries": num_batts,
                    "Bus": int(row["bus"]),

                    "Energy_kWh":
                        row["Emax_kWh"]
                        if "Emax_kWh" in df.columns
                        else None,

                    "Power_kW":
                        row["Pmax_kW"]
                        if "Pmax_kW" in df.columns
                        else None
                })

        except Exception as e:

            print(
                f"Skipping {folder}: {e}"
            )

    summary = pd.DataFrame(rows)

    if len(summary) == 0:
        print("No batteries found.")
        return None

    # summary = summary.sort_values(
    #     ["Allowed_Batteries", "Bus"]
    # )

    print("\n==============================")
    print("BATTERY PLACEMENT SUMMARY")
    print("==============================\n")

    print(
        summary.to_string(
            index=False,
            float_format=lambda x:
                f"{x:.2f}"
        )
    )

    return summary



def summarize_voltage_profiles(results_root, V_MIN=0.95, V_MAX=1.05):

    summaries = []

    folders = glob.glob(
        os.path.join(
            results_root,
            "results_*_RQ2_*_Batt=*_Elec=*"
        )
    )

    for folder in folders:

        voltage_file = os.path.join(
            folder,
            "voltage_profiles.csv"
        )

        if not os.path.exists(voltage_file):
            continue

        # -----------------------------
        # Extract battery count
        # -----------------------------
        match = re.search(
            r"Batt=(\d+\.?\d*)",
            folder
        )

        batteries = (
            float(match.group(1))
            if match else None
        )

        # -----------------------------
        # Load voltage data
        # -----------------------------
        df = pd.read_csv(voltage_file)

        # -----------------------------
        # Weakest bus
        # -----------------------------
        avg_bus_voltage = (
            df.groupby("bus")["v_sq_pu"]
            .mean()
        )

        weakest_bus = int(
            avg_bus_voltage.idxmin()
        )

        weakest_bus_avg_voltage = (
            avg_bus_voltage.min()
        )

        # -----------------------------
        # Global statistics
        # -----------------------------
        min_v = df["v_sq_pu"].min()
        max_v = df["v_sq_pu"].max()

        p1 = df["v_sq_pu"].quantile(0.01)
        p99 = df["v_sq_pu"].quantile(0.99)

        violations = (
            (
                df["v_sq_pu"] < V_MIN
            ) |
            (
                df["v_sq_pu"] > V_MAX
            )
        ).sum()

        summaries.append({
            "Batteries": batteries,
            "Min_V": min_v,
            "P1_V": p1,
            "Mean_V": df["v_sq_pu"].mean(),
            "P99_V": p99,
            "Max_V": max_v,
            "Voltage_Spread": p99 - p1,
            "Violations": violations,
            "Weakest_Bus": weakest_bus,
            "Weakest_Bus_Avg_V":
                weakest_bus_avg_voltage
        })

    summary_df = pd.DataFrame(
        summaries
    ).sort_values(
        "Batteries"
    )

    print("\n==============================")
    print("VOLTAGE PROFILE SUMMARY")
    print("==============================")
    print(
        summary_df.round(4)
        .to_string(index=False)
    )

    return summary_df

import os
import re
import glob
import pandas as pd


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


def voltage_checker(case1, case2, results_root="."):

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

    bus = 14

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
    print("BUS 14 VOLTAGE STATISTICS")
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

    # --------------------------------------------------
    # Time series
    # --------------------------------------------------

    plt.figure(figsize=(12, 5))

    plt.plot(
        v0_bus.values,
        label="B0 | E100",
        linewidth=1
    )

    plt.plot(
        v1_bus.values,
        label="B2 | E140",
        linewidth=1
    )

    plt.axhline(
        0.95,
        linestyle="--"
    )

    plt.axhline(
        1.05,
        linestyle="--"
    )

    plt.title("Voltage Profile Comparison - Bus 14")
    plt.xlabel("Hour")
    plt.ylabel("Voltage [p.u.]")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.show()

    # --------------------------------------------------
    # Histogram
    # --------------------------------------------------

    plt.figure(figsize=(8, 5))

    plt.hist(
        v0_bus,
        bins=50,
        alpha=0.5,
        label="B0 | E100"
    )

    plt.hist(
        v1_bus,
        bins=50,
        alpha=0.5,
        label="B2 | E140"
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
    plt.title("Voltage Distribution Comparison - Bus 14")
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

    plt.hist(line1,bins=50,alpha=0.5,label="No battery at node 39")
    plt.hist(line2, bins=50,alpha=0.5, label="Battery at node 39")
    plt.axvline(100,linestyle="--")
    plt.xlabel("Loading [%]")
    plt.ylabel("Frequency")

    plt.title(
        f"Loading Distribution ({from_bus} → {to_bus})"
    )

    plt.legend()
    plt.grid(True)

    plt.tight_layout()
    plt.show()


# summarize_battery_locations()
# summarize_voltage_profiles(results_root=".")
# weakest_bus_summary(".","RQ1.2")
# voltage_checker(case1="results_*_RQ1.2_Batt=0.00_elec=1.00",
#                 case2="results_*_RQ1.2_Batt=2.00_elec=1.40")

compare_line_loading(
    # scenario1="resulXts_0605_1037_RQ1_Batt=0.00",   #"results_0528_1632_RQ1.1_Batt=0.00",
    # scenario2="results_0603_1404_RQ1.1_Batt=1.00",   #"results_0528_1711_RQ1.1_Batt=1.00"
    scenario1="results_*_RQ2_Scene=WEAKEST_BUS_SEVERITY_SCORE_PV1.00_Batt=2.00_Elec=1.30",
    scenario2="results_*_RQ2_Scene=WEAKEST_BUS_SEVERITY_SCORE_PV1.10_Batt=2.00_Elec=1.30",
    from_bus=129,
    to_bus=14
)