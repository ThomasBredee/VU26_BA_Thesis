import os
import glob
import pandas as pd
import numpy as np


def rank_buses_voltage_problems(
    results_root=".",
    scenario_pattern="results_*_RQ2.1_Scene=Bus_PV2.00_Batt=0.00",
    v_min=0.95,
    v_max=1.05
):
    folders = glob.glob(
        os.path.join(results_root, scenario_pattern)
    )

    if len(folders) == 0:
        raise FileNotFoundError(
            f"No folders found for pattern: {scenario_pattern}"
        )

    folder = folders[0]
    voltage_file = os.path.join(folder, "voltage_profiles.csv")

    if not os.path.exists(voltage_file):
        raise FileNotFoundError(
            f"Missing voltage_profiles.csv in {folder}"
        )

    df = pd.read_csv(voltage_file)

    # Safety: use voltage magnitude, not squared voltage
    if "v_pu" not in df.columns:
        if "v_sq_pu" in df.columns:
            df["v_pu"] = df["v_sq_pu"]
        else:
            raise ValueError(
                "voltage_profiles.csv must contain either v_pu or v_sq_pu"
            )

    df["undervoltage"] = df["v_pu"] < v_min
    df["overvoltage"] = df["v_pu"] > v_max

    df["lower_deviation"] = (v_min - df["v_pu"]).clip(lower=0)
    df["upper_deviation"] = (df["v_pu"] - v_max).clip(lower=0)
    df["total_violation_deviation"] = (
        df["lower_deviation"] + df["upper_deviation"]
    )

    summary = (
        df.groupby("bus")
        .agg(
            min_v_pu=("v_pu", "min"),
            p01_v_pu=("v_pu", lambda x: x.quantile(0.01)),
            mean_v_pu=("v_pu", "mean"),
            p99_v_pu=("v_pu", lambda x: x.quantile(0.99)),
            max_v_pu=("v_pu", "max"),
            undervoltage_hours=("undervoltage", "sum"),
            overvoltage_hours=("overvoltage", "sum"),
            total_violation_hours=("total_violation_deviation", lambda x: (x > 0).sum()),
            max_violation_deviation=("total_violation_deviation", "max"),
            mean_violation_deviation=("total_violation_deviation", "mean"),
        )
        .reset_index()
    )

    summary["voltage_range"] = (
        summary["max_v_pu"] - summary["min_v_pu"]
    )

    # Main ranking score:
    # first buses with most violation hours,
    # then buses closest to voltage limits / worst voltage spread
    summary = summary.sort_values(
        by=[
            "total_violation_hours",
            "max_violation_deviation",
            "voltage_range",
            "p01_v_pu",
        ],
        ascending=[False, False, False, True]
    ).reset_index(drop=True)

    summary["rank"] = summary.index + 1

    summary = summary[
        [
            "rank",
            "bus",
            "min_v_pu",
            "p01_v_pu",
            "mean_v_pu",
            "p99_v_pu",
            "max_v_pu",
            "voltage_range",
            "undervoltage_hours",
            "overvoltage_hours",
            "total_violation_hours",
            "max_violation_deviation",
            "mean_violation_deviation",
        ]
    ]

    print("\n======================================")
    print("BUS VOLTAGE PROBLEM RANKING")
    print(f"Scenario folder: {os.path.basename(folder)}")
    print("======================================\n")

    print(
        summary.round(4).to_string(index=False)
    )

    return summary


import os
import glob
import pandas as pd
import numpy as np


def rank_lines_loading_problems(
    results_root=".",
    scenario_pattern="results_*_RQ1.2_Batt=0.00_elec=1.25_P=1.12"
):
    folders = glob.glob(
        os.path.join(results_root, scenario_pattern)
    )

    if len(folders) == 0:
        raise FileNotFoundError(
            f"No folders found for pattern: {scenario_pattern}"
        )

    folder = folders[0]
    line_file = os.path.join(folder, "line_flows.csv")

    if not os.path.exists(line_file):
        raise FileNotFoundError(
            f"Missing line_flows.csv in {folder}"
        )

    df = pd.read_csv(line_file)

    summary = (
        df.groupby(["from_bus", "to_bus"])
        .agg(
            min_loading=("loading_percent", "min"),
            p01_loading=("loading_percent", lambda x: x.quantile(0.01)),
            mean_loading=("loading_percent", "mean"),
            p95_loading=("loading_percent", lambda x: x.quantile(0.95)),
            p99_loading=("loading_percent", lambda x: x.quantile(0.99)),
            max_loading=("loading_percent", "max"),
        )
        .reset_index()
    )

    summary["loading_range"] = (
        summary["max_loading"] -
        summary["min_loading"]
    )

    summary = summary.sort_values(
        by=[
            "p99_loading",
            "max_loading",
            "mean_loading"
        ],
        ascending=False
    ).reset_index(drop=True)

    summary["rank"] = summary.index + 1

    summary = summary[
        [
            "rank",
            "from_bus",
            "to_bus",
            "min_loading",
            "p01_loading",
            "mean_loading",
            "p95_loading",
            "p99_loading",
            "max_loading",
            "loading_range",
        ]
    ]

    print("\n======================================")
    print("LINE LOADING PROBLEM RANKING")
    print(f"Scenario folder: {os.path.basename(folder)}")
    print("======================================\n")

    print(
        summary.round(2).to_string(index=False)
    )

    return summary

# Tested these:

# # RQ1.2 Electrification scenario
# "results_*_RQ1.2_Batt=0.00_elec=1.25_P=1.12"

# # RQ2.1 Uniform PV placement
# "results_*_RQ2.1_Scene=Uniform_PV2.00_Batt=0.00"

# # RQ2.1 Bus-based PV placement
# "results_*_RQ2.1_Scene=Bus_PV2.00_Batt=0.00"

# # RQ2.1 Line-based PV placement
# "results_*_RQ2.1_Scene=Line_PV2.00_Batt=0.00"

# rank_buses_voltage_problems(".")

rank_lines_loading_problems(".",
                            scenario_pattern= "results_*_RQ2.1_Scene=Line_PV2.00_Batt=0.00"
                            )