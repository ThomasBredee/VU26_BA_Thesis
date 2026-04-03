from config import (
    NETWORK_CHOICE,
    TIME,
    DATA_PATH_DEMAND, DATA_PATH_ELECTRICITY_PRICE,
    CE, CP, SOC_MIN, SOC_MAX, GAMMA
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

# import gurobipy as gp
import numpy as np

def sanitize_data_scalars(data):
    """
    Automatically converts any tuple or single-element list in `data` to scalar.
    Prints what it changed for transparency.
    """
    for key, value in data.items():
        if isinstance(value, tuple) and len(value) == 1:
            data[key] = value[0]
            print(f"🔧 Converted tuple to scalar for key '{key}': {value} -> {data[key]}")
        elif isinstance(value, list) and len(value) == 1:
            data[key] = value[0]
            print(f"🔧 Converted single-element list to scalar for key '{key}': {value} -> {data[key]}")
        elif isinstance(value, np.ndarray) and value.size == 1:
            data[key] = value.item()
            print(f"🔧 Converted 1-element ndarray to scalar for key '{key}': {value} -> {data[key]}")
        else:
            # Already scalar or multi-element, no change
            pass
    return data

def main():
    print('Starting pipeline................. \n')

    # Create network
    net = NETWORK_CHOICE() 
    data = extract_network_data(net)

    # Create time array
    data['T'] = list(range(TIME))

    # Create base demands based on busses
    base_demand = generate_base_demand(data['B'], seed=42)

    # Load demand data
    demand_data_percentages = load__demand_profile_percentages(DATA_PATH_DEMAND)

    # # Plot
    # plot_noise_comparison(profile, profile_noisy)
    # # plot_daily_average(profile)
    # # plot_hourly_pattern(profile)
    
    data['pD'] = build_pD(
        B=data['B'],
        T=data['T'],
        base_demand=base_demand,
        profile=demand_data_percentages,
        verbose=False
    )

    price_series = load_year_prices(DATA_PATH_ELECTRICITY_PRICE, year=2025, verbose=False)
    data['c'] = convert_series_to_dict(price_series, data['T'])

    data['cP'] = CP
    data['cE'] = CE
    data['gamma'] = GAMMA
    data['SOC_min'] = SOC_MIN
    data['SOC_max'] = SOC_MAX

    model = build_model(data)

    # print(data['pD'])
    # print(min(t for (_, t) in data['pD'].keys()))
    # print(max(t for (_, t) in data['pD'].keys()))
    # print(data['T'][0], data['T'][-1])
    
    # sanitize_data_scalars(data)

    # results = solve_model(model)


    from pyomo.environ import SolverFactory

    # Choose your solver
    solver = SolverFactory('gurobi')

    # Enable IIS detection
    solver.options['OutputFlag'] = 1  # Show solver messages
    solver.options['IIS'] = 1         # Ask Gurobi to generate IIS

    # Solve the model
    results = solver.solve(model, tee=True)

    # Check if infeasible
    if results.solver.termination_condition == 'infeasibleOrUnbounded':
        print("Model is infeasible. Writing IIS...")
        
        # Write IIS to a file (Gurobi writes .ilp with conflicting constraints)
        model.write('model_iis.ilp', format='lp')
        
        # In Gurobi, you can call the following to write the IIS itself:
        # (Pyomo doesn't expose IIS writer directly, so we trigger it via solver)
        solver.solve(model, options={'IIS': 1})
        print("IIS written. Check the .ilp file or Gurobi output to see problematic constraints.")
    else:
        print("Solver status:", results.solver.termination_condition)

    extract_results(model, results)
    
    print("Pipeline executed successfully.")

        


if __name__ == "__main__":
    main()