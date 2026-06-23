import os
import re
import glob
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np


def collect_objective_results(
    results_root,
    experiment
):
    """
    Collect objective breakdown from all result folders.

    Example folder:
    results_0607_2300_RQ1.2_Batt=2.00_elec=1.00

    Returns:
    DataFrame with:
        BESS
        Electrification
        Total_Cost_EUR
        Energy_Cost_EUR
        Investment_Cost_EUR
        Degradation_Cost_EUR
        Curtailment_Cost_EUR
    """

    pattern = os.path.join(
        results_root,
        f"results_*_{experiment}_Batt=*_elec=*"
    )

    folders = glob.glob(pattern)

    rows = []

    for folder in folders:

        folder_name = os.path.basename(folder)

        # -----------------------------------------
        # Extract BESS
        # -----------------------------------------
        bess_match = re.search(
            r"Batt=([0-9.]+)",
            folder_name
        )

        bess = (
            float(bess_match.group(1))
            if bess_match else None
        )

        # -----------------------------------------
        # Extract electrification
        # -----------------------------------------
        elec_match = re.search(
            r"elec=([0-9.]+)",
            folder_name
        )

        electrification = (
            float(elec_match.group(1))
            if elec_match else None
        )

        # -----------------------------------------
        # Objective file
        # -----------------------------------------
        objective_file = os.path.join(
            folder,
            "objective.csv"
        )

        if not os.path.exists(objective_file):
            print(
                f"[WARNING] Missing objective.csv in "
                f"{folder_name}"
            )
            continue

        df_obj = pd.read_csv(objective_file)

        if df_obj.empty:
            continue

        obj = df_obj.iloc[0]

        rows.append({
            "BESS": bess,
            "Electrification": electrification,

            "Total_Cost_EUR":
                obj["objective_total_eur"],

            "Energy_Cost_EUR":
                obj["energy_cost_eur"],

            "Investment_Cost_EUR":
                obj["investment_cost_eur"],

            "Degradation_Cost_EUR":
                obj["degradation_cost_eur"],

            "Curtailment_Cost_EUR":
                obj["curtailment_cost_eur"],
        })

    result_df = pd.DataFrame(rows)

    if not result_df.empty:

        result_df = result_df.sort_values(
            ["Electrification", "BESS"]
        ).reset_index(drop=True)

    print("\n===================================")
    print(f"OBJECTIVE BREAKDOWN ({experiment})")
    print("===================================")

    if not result_df.empty:
        print(result_df.round(2).to_string(index=False))
    else:
        print("No matching scenarios found.")

    BASE_DEMAND_MWH = 387.60927316075
    result_df["Total_Energy_kWh"] = (BASE_DEMAND_MWH *result_df["Electrification"])

    return result_df


def plot_cost_breakdown(df):
    """
    Stacked cost breakdown for every solved scenario.

    Requires columns:
        BESS
        Electrification
        Energy_Cost_EUR
        Investment_Cost_EUR
        Degradation_Cost_EUR
        Curtailment_Cost_EUR
    """

    df = df.sort_values(
        ["BESS", "Electrification"]
    ).reset_index(drop=True)

    labels = [
        f"B{int(row.BESS)}\nE{row.Electrification:.2f}"
        for _, row in df.iterrows()
    ]

    x = np.arange(len(df))

    energy = df["Energy_Cost_EUR"]
    invest = df["Investment_Cost_EUR"]
    degr = df["Degradation_Cost_EUR"]
    curt = df["Curtailment_Cost_EUR"]

    plt.figure(figsize=(12, 6))

    plt.bar(
        x,
        energy,
        width=0.6,
        label="Energy"
    )

    plt.bar(
        x,
        invest,
        bottom=energy,
        width=0.6,
        label="Investment"
    )

    plt.bar(
        x,
        degr,
        bottom=energy + invest,
        width=0.6,
        label="Degradation"
    )

    plt.bar(
        x,
        curt,
        bottom=energy + invest + degr,
        width=0.6,
        label="Curtailment"
    )

    plt.xticks(
        x,
        labels,
        rotation=45
    )

    totals = energy + invest + degr + curt

    for i, total in enumerate(totals):
        plt.text(
            i,
            total,
            f"€{total:,.0f}",
            ha="center",
            va="bottom",
            fontsize=8,
            rotation=0
        )

    plt.ylabel("Annual Cost [€]")
    plt.xlabel("Scenario")
    plt.title("Objective Function Cost Breakdown")
    plt.legend()
    plt.grid(axis="y")

    plt.tight_layout()
    plt.show()

def plot_optimal_battery_size(df):

    plot_df = (
        df[df["BESS"] > 0]
        .sort_values(["BESS", "Electrification"])
    )

    plt.figure(figsize=(10, 6))

    for bess in sorted(plot_df["BESS"].unique()):

        subset = plot_df[
            plot_df["BESS"] == bess
        ]

        plt.plot(
            subset["Electrification"],
            subset["Total_Energy_kWh"],
            marker="o",
            label=f"{int(bess)} BESS"
        )

    plt.xlabel("Electrification / PV Factor")
    plt.ylabel("Installed Battery Energy [kWh]")

    plt.title(
        "Optimal Battery Capacity under Increasing Electrification"
    )

    plt.legend()
    plt.grid(True)

    plt.tight_layout()
    plt.show()



df = collect_objective_results(".", "RQ1.2")
plot_cost_breakdown(df)
# plot_optimal_battery_size(df)