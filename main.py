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

    

    results = solve_model(model)
    results = solve_model(model)

    extract_results(model, results)
    
    print("Pipeline executed successfully.")

        


if __name__ == "__main__":
    main()