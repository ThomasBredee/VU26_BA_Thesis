from pyomo.environ import SolverFactory, value

def solve_model(model, tee=True):
    solver = SolverFactory("gurobi")

    # Optional solver settings
    # solver.options['TimeLimit'] = 300      # seconds
    # solver.options['MIPGap'] = 0.01        # 1% optimality gap

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
    for t in list(model.T)[:max_print]:
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