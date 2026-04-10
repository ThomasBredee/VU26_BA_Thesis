from pyomo.environ import SolverFactory, value
import matplotlib.pyplot as plt
import numpy as np

def solve_model(model, tee=True):
    solver = SolverFactory("gurobi")

    # Optional solver settings
    # solver.options['TimeLimit'] = 300      # seconds
    # solver.options['MIPGap'] = 0.005        # 0.5% optimality gap

    results = solver.solve(model, tee=tee)

    return results

from pyomo.environ import value
from pyomo.opt import TerminationCondition


def extract_results(model, results, max_print=10):
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
            print(f"Bus {i}: Pmax={Pmax:.2f}, Emax={Emax:.2f}")
        except:
            print(f"Bus {i}: ERROR")

    

    # -----------------------------
    # Settings
    # -----------------------------
    T_plot = list(model.T)[:1000]  # first 1000 timesteps
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
    plt.title('Battery SOC over time (first 1000 timesteps)')
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