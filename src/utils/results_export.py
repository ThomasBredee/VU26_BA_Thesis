# ============================================================
# THESIS OUTPUT PIPELINE
# ============================================================
#
# Creates a clean results folder structure:
#
# results/
# ├── objective.csv
# ├── substation.csv
# ├── batteries.csv
# ├── soc.csv
# ├── line_flows.csv
# ├── pv_summary.csv
# ├── voltage_profiles.csv
# ├── constraint_violations.csv
# ├── figures/
# │   ├── objective_breakdown.png
# │   ├── substation_power.png
# │   ├── battery_soc_bus_XX.png
# │   ├── pv_curtailment_pie.png
# │   ├── line_loading_1.png
# │   ├── line_loading_2.png
# │   └── line_loading_3.png
#
# ============================================================

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from pyomo.environ import value
from datetime import datetime






# ============================================================
# MAIN PIPELINE
# ============================================================

def export_thesis_results(model, data, versioning, results_dir="results"):

    timestamp = datetime.now().strftime("%m%d_%H%M")

    # Create versioned root folder
    output_dir = f"{timestamp}_{results_dir}_{versioning}"

    # Create directories
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(f"{output_dir}/figures", exist_ok=True)

    # Export all outputs
    export_objective_results(model, data, output_dir)
    export_substation_results(model, data, output_dir)
    export_battery_results(model, data, output_dir)
    export_soc_results(model, data, output_dir)
    export_line_flow_results(model, data, output_dir)
    export_pv_results(model, data, output_dir)
    export_voltage_results(model, data, output_dir)
    export_constraint_violations(model, data, output_dir)

    print(f"\nResults exported to: {output_dir}")


# ============================================================
# 1. OBJECTIVE / ECONOMICS
# ============================================================

def export_objective_results(model, data, results_dir):

    S_base = data['S_base_kVA']

    energy_cost = sum(
        value(model.c[t]) *
        value(model.P_sub[s, t]) * S_base *
        value(model.dt)
        for s in model.B_sub
        for t in model.T
    )

    investment_cost = value(model.alpha) * sum(
        value(model.cP) * value(model.Pmax[i]) * S_base +
        value(model.cE) * value(model.Emax[i]) * S_base
        for i in model.B
    )

    degradation_cost = value(model.c_deg) * sum(
        (value(model.pCHA[i, t]) + value(model.pDIS[i, t]))
        * S_base
        * value(model.dt)
        for i in model.B
        for t in model.T
    )

    curtailment_cost = sum(
        value(model.c_curt[t]) *
        value(model.pPV_curt[i, t]) *
        S_base *
        value(model.dt)
        for i in model.B
        for t in model.T
    )

    objective = value(model.OBJ)

    df = pd.DataFrame([{
        "objective_total_eur": objective,
        "energy_cost_eur": energy_cost,
        "investment_cost_eur": investment_cost,
        "degradation_cost_eur": degradation_cost,
        "curtailment_cost_eur": curtailment_cost
    }])

    df.to_csv(f"{results_dir}/objective.csv", index=False)

    # Pie chart
    plt.figure(figsize=(8, 8))

    labels = [
        "Energy",
        "Investment",
        "Degradation",
        "Curtailment"
    ]

    values = [
        energy_cost,
        investment_cost,
        degradation_cost,
        curtailment_cost
    ]

    plt.pie(values, labels=labels, autopct='%1.1f%%')
    plt.title("Objective Cost Breakdown")

    plt.savefig(
        f"{results_dir}/figures/objective_breakdown.png",
        dpi=300,
        bbox_inches='tight'
    )

    plt.close()


# ============================================================
# 2. SUBSTATION OPERATION
# ============================================================

def export_substation_results(model, data, results_dir):

    S_base = data['S_base_kVA']

    rows = []

    for s in model.B_sub:
        for t in model.T:

            p_kw = value(model.P_sub[s, t]) * S_base
            q_kvar = value(model.Q_sub[s, t]) * S_base

            rows.append({
                "time": t,
                "bus": s,
                "P_sub_kW": p_kw,
                "Q_sub_kVar": q_kvar
            })

    df = pd.DataFrame(rows)

    df.to_csv(f"{results_dir}/substation.csv", index=False)

    # Plot
    plt.figure(figsize=(14, 5))

    plt.plot(df["time"], df["P_sub_kW"])

    plt.xlabel("Time")
    plt.ylabel("Substation Power [kW]")
    plt.title("Substation Power Over Time")
    plt.grid(True)

    plt.savefig(
        f"{results_dir}/figures/substation_power.png",
        dpi=300,
        bbox_inches='tight'
    )

    plt.close()


# ============================================================
# 3. BATTERY RESULTS
# ============================================================

def export_battery_results(model, data, results_dir):

    S_base = data['S_base_kVA']

    rows = []

    for i in model.B:

        installed = round(value(model.b[i]))

        if installed == 1:

            rows.append({
                "bus": i,
                "installed": installed,
                "Pmax_kW": value(model.Pmax[i]) * S_base,
                "Emax_kWh": value(model.Emax[i]) * S_base
            })

    df = pd.DataFrame(rows)

    df.to_csv(f"{results_dir}/batteries.csv", index=False)


# ============================================================
# 4. SOC RESULTS
# ============================================================

def export_soc_results(model, data, results_dir):

    S_base = data['S_base_kVA']

    rows = []

    installed_buses = []

    for i in model.B:

        if round(value(model.b[i])) == 1:
            installed_buses.append(i)

        for t in model.T:

            rows.append({
                "bus": i,
                "time": t,
                "SOC_kWh": value(model.E[i, t]) * S_base,
                "Charge_kW": value(model.pCHA[i, t]) * S_base,
                "Discharge_kW": value(model.pDIS[i, t]) * S_base
            })

    df = pd.DataFrame(rows)

    df.to_csv(f"{results_dir}/soc.csv", index=False)

    # Plot SOC for installed batteries
    for bus in installed_buses:

        df_bus = df[df["bus"] == bus]

        plt.figure(figsize=(14, 5))

        plt.plot(df_bus["time"], df_bus["SOC_kWh"])

        plt.xlabel("Time")
        plt.ylabel("SOC [kWh]")
        plt.title(f"Battery SOC - Bus {bus}")

        plt.grid(True)

        plt.savefig(
            f"{results_dir}/figures/battery_soc_bus_{bus}.png",
            dpi=300,
            bbox_inches='tight'
        )

        plt.close()


# ============================================================
# 5. PV RESULTS
# ============================================================

def export_pv_results(model, data, results_dir):

    S_base = data['S_base_kVA']

    used = 0
    curtailed = 0

    rows = []

    for i in model.B:
        for t in model.T:

            pv_used = value(model.pPV_used[i, t]) * S_base
            pv_curt = value(model.pPV_curt[i, t]) * S_base

            used += pv_used
            curtailed += pv_curt

            rows.append({
                "bus": i,
                "time": t,
                "PV_used_kW": pv_used,
                "PV_curtailed_kW": pv_curt
            })

    df = pd.DataFrame(rows)

    df.to_csv(f"{results_dir}/pv_summary.csv", index=False)

    # Pie chart
    plt.figure(figsize=(8, 8))

    plt.pie(
        [used, curtailed],
        labels=["Used", "Curtailed"],
        autopct='%1.1f%%'
    )

    plt.title("PV Utilization")

    plt.savefig(
        f"{results_dir}/figures/pv_curtailment_pie.png",
        dpi=300,
        bbox_inches='tight'
    )

    plt.close()


# ============================================================
# 6. LINE FLOWS
# ============================================================

def export_line_flow_results(model, data, results_dir):

    S_base = data['S_base_kVA']

    rows = []

    max_loading = {}

    for (i, j) in model.L:

        limit = value(model.Smax_line[i, j]) * S_base

        loading_series = []

        for t in model.T:

            p = value(model.P[i, j, t]) * S_base

            loading = abs(p) / limit

            loading_series.append(loading)

            rows.append({
                "from_bus": i,
                "to_bus": j,
                "time": t,
                "P_kW": p,
                "loading_percent": loading * 100
            })

        max_loading[(i, j)] = max(loading_series)

    df = pd.DataFrame(rows)

    df.to_csv(f"{results_dir}/line_flows.csv", index=False)

    # Top 3 congested lines
    top3 = sorted(
        max_loading.items(),
        key=lambda x: x[1],
        reverse=True
    )[:3]

    for idx, ((i, j), _) in enumerate(top3, start=1):

        df_line = df[
            (df["from_bus"] == i) &
            (df["to_bus"] == j)
        ]

        limit = value(model.Smax_line[i, j]) * S_base

        plt.figure(figsize=(14, 5))

        plt.plot(df_line["time"], df_line["P_kW"])

        plt.axhline(limit, linestyle='--')
        plt.axhline(-limit, linestyle='--')

        plt.xlabel("Time")
        plt.ylabel("Power Flow [kW]")

        plt.title(f"Line Flow ({i} → {j})")

        plt.grid(True)

        plt.savefig(
            f"{results_dir}/figures/line_loading_{idx}.png",
            dpi=300,
            bbox_inches='tight'
        )

        plt.close()


# ============================================================
# 7. VOLTAGES
# ============================================================

def export_voltage_results(model, data, results_dir):

    rows = []

    for i in model.B0:
        for t in model.T:

            v_sq = value(model.v[i, t])

            rows.append({
                "bus": i,
                "time": t,
                "voltage_pu": np.sqrt(v_sq)
            })

    df = pd.DataFrame(rows)

    df.to_csv(f"{results_dir}/voltage_profiles.csv", index=False)


# ============================================================
# 8. CONSTRAINT VIOLATIONS
# ============================================================

def export_constraint_violations(model, data, results_dir):

    rows = []

    # Voltage violations
    for i in model.B:
        for t in model.T:

            v = np.sqrt(value(model.v[i, t]))

            if v < np.sqrt(value(model.v_min)) or \
               v > np.sqrt(value(model.v_max)):

                rows.append({
                    "type": "voltage",
                    "bus_or_line": i,
                    "time": t,
                    "value": v
                })

    df = pd.DataFrame(rows)

    df.to_csv(
        f"{results_dir}/constraint_violations.csv",
        index=False
    )