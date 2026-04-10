from config import (
    NETWORK_CHOICE,
    TIME,
    DATA_PATH_DEMAND, DATA_PATH_ELECTRICITY_PRICE,
    CE, CP, SOC_MIN, SOC_MAX, GAMMA,
    HOUSE_MIN_USAGE, HOUSE_MAX_USAGE
)

from src.input.extract_network import extract_network_data
from src.input.load_data import load__demand_profile_percentages, load_year_prices, convert_series_to_dict
from src.input.preprocess_data import build_pD, generate_base_demand, plot_bus_profiles_window
from src.models.basic_model import build_model
from src.utils.solver import solve_model, extract_results

from src.utils.plotting import (
    plot_noise_comparison,
    plot_daily_average,
    plot_hourly_pattern
)

from pyomo.environ import SolverFactory

def main():
    print('Starting pipeline................. \n')

    # Create network
    net = NETWORK_CHOICE() 
    data = extract_network_data(net, verbose=True)

    # Create time array
    data['T'] = list(range(TIME))

    # Demand: load generate base demands, extract percentages, concat into noisy profiles
    base_demand = generate_base_demand(data['B'], HOUSE_MIN_USAGE, HOUSE_MAX_USAGE, seed=42)
    demand_data_percentages = load__demand_profile_percentages(DATA_PATH_DEMAND, verbose=True)
    
    data['pD'] = build_pD(
        B=data['B'],
        T=data['T'],
        base_demand=base_demand,
        profile=demand_data_percentages,
        verbose=True
    )


    price_series = load_year_prices(DATA_PATH_ELECTRICITY_PRICE, year=2025, verbose=True)
    data['c'] = convert_series_to_dict(price_series, data['T'])

    data['cP'] = CP
    data['cE'] = CE
    data['gamma'] = GAMMA
    data['SOC_min'] = SOC_MIN
    data['SOC_max'] = SOC_MAX

    model = build_model(data)
    # print("Pmax_sub: ", data['Pmax_sub'])
    

    # print("B: ", data['B'])
    # print("B_prime: ", data['B_prime'])
    # print("L: ", data['L'])

    # t0 = min(t for (_, t) in data['pD'].keys())

    # for i in data['B']:
    #     print(f"pD[{i}, {t0}] =", data['pD'].get((i, t0), 0))

    # from pyomo.opt import SolverFactory, TerminationCondition

    # solver = SolverFactory('gurobi_persistent')
    # solver.set_instance(model)
    # results = solver.solve(tee=True)
    # if results.solver.termination_condition in [
    #     TerminationCondition.infeasible,
    #     TerminationCondition.infeasibleOrUnbounded
    # ]:
    #     print("\nModel infeasible — computing IIS...\n")
    #     gurobi_model = solver._solver_model
    #     gurobi_model.computeIIS()
    #     gurobi_model.write("model.ilp")
    #     print("IIS written to model.ilp")

    

    #DEZE UITEINDLEIJK WEER AANZETTEN!!!
    results = solve_model(model)
    extract_results(model, results)

    #Testing::
    system_balance_check = False
    if system_balance_check:
        print("\n=== System balance check ===")
        T_list = list(model.T)

        for t in T_list[0:50]:
            total_demand = sum(data['pD'].get((i, t), 0) for i in model.B)
            total_discharge = sum(model.pDIS[i, t].value for i in model.B)
            total_charge = sum(model.pCHA[i, t].value for i in model.B)
            total_sub = sum(model.P_sub[s, t].value for s in model.B_prime)

            net_battery = total_discharge - total_charge

            print(f"t={t}: demand={total_demand:.2f}, "
                f"battery_net={net_battery:.2f}, "
                f"substation={total_sub:.2f}")
        
        T_list = list(model.T)

        for i in model.B:
            soc_values = [model.E[i, t].value for t in T_list[:50]]
            print(f"Bus {i}: {soc_values}")



    print("Pipeline executed successfully.")

        


if __name__ == "__main__":
    main()