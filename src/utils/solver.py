from pyomo.environ import SolverFactory, value
import matplotlib.pyplot as plt
import numpy as np
import math
from pyomo.environ import value
from pyomo.opt import TerminationCondition


def solve_model(model, tee=False):
    solver = SolverFactory("gurobi")

    # Optional solver settings
    solver.options['TimeLimit'] = 600      # seconds
    # solver.options['MIPGap'] = 0.005        # 0.5% optimality gap

    results = solver.solve(model, tee=tee)

    return results



def extract_results(model, results, data, max_print=10):
    """
    Safely extract and print results from a solved Pyomo model.
    """

    # -------------------------
    # 1. Check solver status
    # -------------------------
    tc = results.solver.termination_condition

    if tc == TerminationCondition.optimal:
        print("✅ Optimal solution found\n")
    else:
        print(f"⚠️ Solver status: {tc}")
        print("Skipping result extraction (solution may be invalid)\n")
        return

    # -------------------------
    # 2. Objective value
    # -------------------------
    try:
        print(f"Objective value: {value(model.OBJ):.2f}\n")
    except:
        print("Could not evaluate objective\n")

    # -------------------------
    # 3. Substation usage
    # -------------------------
    print("=== Substation usage (first timesteps) ===")
    for t in list(model.T)[5000:5000+max_print]:
        try:
            total_sub = sum(
                value(model.P_sub[s, t]) or 0
                for s in model.B_prime
            )
            print(f"t={t}: {total_sub:.2f}")
        except:
            print(f"t={t}: ERROR")
    print()

    # -------------------------
    # 4. Battery placement
    # -------------------------
    print("=== Battery placement ===")
    for i in model.B:
        try:
            if (value(model.b[i]) or 0) > 0.5:
                print(f"Battery installed at bus {i}")
        except:
            continue
    print()

    # -------------------------
    # 5. Battery sizes
    # -------------------------
    print("=== Battery sizes ===")
    for i in model.B:
        try:
            Pmax = value(model.Pmax[i]) or 0
            Emax = value(model.Emax[i]) or 0
            if Emax != 0:
                print(f"Bus {i}: Pmax={Pmax:.2f}, Emax={Emax:.2f}")
        except:
            print(f"Bus {i}: ERROR")

    

    # -----------------------------
    # Settings
    # -----------------------------
    T_plot = list(model.T)[3000:3750]  # first 1000 timesteps
    buses = list(model.B)           # battery buses
    substations = list(model.B_prime)

    # -----------------------------
    # Extract SOC and Substation power
    # -----------------------------
    SOC = {i: [model.E[i, t].value for t in T_plot] for i in buses}
    P_sub = {s: [model.P_sub[s, t].value for t in T_plot] for s in substations}

    # -----------------------------
    # Plot SOC per battery
    # -----------------------------
    plt.figure(figsize=(15,6))
    for i in buses:
        plt.plot(T_plot, SOC[i], label=f'Bus {i} SOC')
    plt.xlabel('Time [t]')
    plt.ylabel('State of Charge [E]')
    plt.title('Battery SOC over time (Timesteps 3000 to 3750 (hours))')
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()

    # -----------------------------
    # Plot Substation power
    # -----------------------------
    plt.figure(figsize=(15,4))
    for s in substations:
        plt.plot(T_plot, P_sub[s], label=f'Substation {s} Power')
    plt.xlabel('Time [t]')
    plt.ylabel('Power injected [P_sub]')
    plt.title('Substation Power over time (first 1000 timesteps)')
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()

    # -----------------------------
    # Optional: overlay SOC + substation
    # -----------------------------
    plt.figure(figsize=(15,6))
    for i in buses:
        plt.plot(T_plot, SOC[i], label=f'Bus {i} SOC')
    for s in substations:
        plt.plot(T_plot, P_sub[s], '--', label=f'Substation {s} Power')
    plt.xlabel('Time [t]')
    plt.ylabel('Energy / Power')
    plt.title('Battery SOC and Substation Power (first 1000 timesteps)')
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()

    # -----------------------------
    # Extract PV data
    # -----------------------------
    PV_used = {i: [model.pPV_used[i, t].value for t in T_plot] for i in buses}
    PV_curt = {i: [model.pPV_curt[i, t].value for t in T_plot] for i in buses}

    # Optional: original PV (parameter)
    PV_total = {i: [model.PV[i, t] for t in T_plot] for i in buses}


    PV_used_total = np.sum([PV_used[i] for i in buses], axis=0)
    PV_curt_total = np.sum([PV_curt[i] for i in buses], axis=0)
    PV_total_total = np.sum([PV_total[i] for i in buses], axis=0)



    plt.figure(figsize=(12, 6))

    plt.stackplot(
        T_plot,
        PV_used_total,
        PV_curt_total,
        labels=["PV Used", "PV Curtailed"],
        alpha=0.8
    )

    # Optional: overlay total PV as line
    plt.plot(T_plot, PV_total_total, linestyle='--', linewidth=2, label="Total PV")

    plt.xlabel("Time")
    plt.ylabel("Power / Energy")
    plt.title("PV Utilization vs Curtailment")
    plt.legend()
    plt.grid(True)

    plt.tight_layout()
    plt.show()


    energy_cost = sum(
        value(model.c[t]) * sum(value(model.P_sub[s, t]) for s in model.B_prime)
        for t in model.T
    )
    investment_cost = sum(
        value(model.cP) * value(model.Pmax[i]) + value(model.cE) * value(model.Emax[i])
        for i in model.B
    )
    degradation_penalty = 0.1 * sum(
        value(model.pCHA[i, t]) + value(model.pDIS[i, t])
        for i in model.B for t in model.T
    )
    curtailment_penalty = sum(
        value(model.c_curt[t]) * value(model.pPV_curt[i, t])
        for i in model.B for t in model.T
    )
    total_objective = value(model.OBJ)

    print("===== OBJECTIVE BREAKDOWN =====")
    print("Energy cost ($)     :", round(energy_cost,2))
    print("Investment cost ($) :", round(investment_cost,2))
    print("Degradation cost    :", degradation_penalty)
    print("Curtailment cost    :", curtailment_penalty)
    print("--------------------------------")
    print("TOTAL OBJECTIVE     :", total_objective)

    total_curtailment = sum(
        value(model.pPV_curt[i, t])
        for i in model.B for t in model.T
    )

    total_energy_price = sum(
        value(model.c[t])
        for t in model.T
    )

    print("===== OVERALL RESULTS =====")
    print("Total PV curtailed:", total_curtailment)
    print("Sum of energy prices:", total_energy_price)

    T_list = list(model.T)

    curtailment_ts = []
    price_ts = []

    for t in T_list:
        curt = sum(value(model.pPV_curt[i, t]) for i in model.B)
        price = value(model.c[t])

        curtailment_ts.append(curt)
        price_ts.append(price)

    fig, ax1 = plt.subplots(figsize=(18, 5))

    # PV curtailment
    ax1.plot(T_list, curtailment_ts, color='tab:orange', label='PV Curtailment')
    ax1.set_ylabel("PV Curtailment (kW)")
    ax1.set_xlabel("Time step")

    # Price on second axis
    ax2 = ax1.twinx()
    ax2.plot(T_list, price_ts, color='tab:blue', alpha=0.6, label='Energy Price')
    ax2.set_ylabel("Energy Price")

    plt.title("PV Curtailment vs Energy Price (first 1000 timesteps)")
    fig.tight_layout()
    plt.show()



    T = list(model.T)
    lines_from_1 = [(i, j) for (i, j) in model.L if i == 1]

    n = len(lines_from_1)
    cols = 2
    rows = math.ceil(n / cols)

    fig, axes = plt.subplots(rows, cols, figsize=(12, 4 * rows))
    axes = axes.flatten()

    for idx, (i, j) in enumerate(lines_from_1):
        ax = axes[idx]

        flow = [value(model.P[i, j, t]) for t in T]
        cap = data['Pmax_line'][(i, j)]

        ax.plot(T, flow)

        ax.hlines(cap, T[0], T[-1], linestyles='dotted')
        ax.hlines(-cap, T[0], T[-1], linestyles='dotted')

        ax.set_title(f"({i} → {j})")
        ax.set_xlabel("Time")
        ax.set_ylabel("Power")
        ax.grid(True)

    # remove unused subplots
    for k in range(len(lines_from_1), len(axes)):
        fig.delaxes(axes[k])

    plt.tight_layout()
    plt.show()





    T = list(model.T)
    # lines_from_1 = [(i, j) for (i, j) in model.L if i == 1]
    lines_from_1 = [(i, j) for (i, j) in model.L if i == 1]

    lines_from_32 = [(i, j) for (i, j) in model.L if i == 32 or j == 32]

    lines_selected = lines_from_1 + lines_from_32

    for (i, j) in lines_selected:
        flow = [value(model.P[i, j, t]) for t in T]
        cap = data['Pmax_line'][(i, j)]

        plt.figure(figsize=(10, 4))

        plt.plot(T, flow, label=f"P({i},{j})")

        # capacity bounds
        plt.hlines(cap, T[0], T[-1], linestyles='dotted')
        plt.hlines(-cap, T[0], T[-1], linestyles='dotted')

        # detect overload
        threshold = 0.9 * cap
        overload = [abs(f) > threshold for f in flow]

        plt.hlines(threshold, T[0], T[-1], linestyles='dashed')
        plt.hlines(-threshold, T[0], T[-1], linestyles='dashed')

        # highlight regions
        for k in range(len(T)):
            if overload[k]:
                plt.axvspan(T[k], T[k] + 1, alpha=0.3)

        plt.title(f"Line ({i} → {j}) with Overload Highlight")
        plt.xlabel("Time")
        plt.ylabel("Power Flow")
        plt.legend()
        plt.grid(True)

        plt.show()


    """
    Extract peak absolute line flows and compare with Pmax.
    """

    L = data['L']
    T = data['T']
    Pmax_line = data['Pmax_line']

    line_peak_results = {}

    print("\n=== LINE FLOW PEAKS ===\n")

    for (i, j) in L:
        flows = []

        for t in T:
            val = value(model.P[(i, j), t])
            
            if val is None:
                val = 0.0

            flows.append(abs(val))  # absolute flow

        peak_flow = max(flows)
        Pmax = Pmax_line.get((i, j), None)

        # Avoid division errors
        if Pmax is not None and Pmax > 0:
            loading = peak_flow / Pmax
        else:
            loading = None

        line_peak_results[(i, j)] = {
            "peak_flow": peak_flow,
            "Pmax": Pmax,
            "loading": loading
        }

        if loading is not None:
            print(f"Line ({i},{j}): "
                  f"Peak = {peak_flow:.2f} kW | "
                  f"Pmax = {Pmax:.2f} kW | "
                  f"Loading = {loading:.2%}")
        else:
            print(f"Line ({i},{j}): Peak = {peak_flow:.2f} kW | Pmax = None")

    return line_peak_results










