from config import (
    NETWORK_CHOICE,
    TIME,
    DATA_PATH_DEMAND, DATA_PATH_ELECTRICITY_PRICE,
    CE, CP, SOC_MIN, SOC_MAX, GAMMA,
    HOUSE_MIN_USAGE, HOUSE_MAX_USAGE,
    ELECTRICITY_PRICE_CAP_AT_0,
    PV_GENERATION
)

from src.input.extract_network import extract_network_data
from src.input.load_data import load__demand_and_PV_profile_percentages, load_year_prices, convert_series_to_dict
from src.input.preprocess_data import build_pD, build_PV, generate_base_demand, generate_base_PV, network_limits, calculate_Big_M
from src.models.basic_model import build_model
from src.models.model_PV import build_model_PV
from src.utils.solver import solve_model, extract_results

from src.utils.plotting import (
    plot_noise_comparison,
    plot_daily_average,
    plot_hourly_pattern
)

def main():
    print('Starting pipeline................. \n')

    # Create network
    net = NETWORK_CHOICE() 
    data , base_demand = extract_network_data(net, verbose=False)

    # # Create time array
    data['T'] = list(range(TIME))

    # # Demand: load generate base demands, extract percentages, concat into noisy profiles
    # base_demand = generate_base_demand(data['B'], HOUSE_MIN_USAGE, HOUSE_MAX_USAGE, seed=42)
    base_PV = generate_base_PV(data['B'], PV_GENERATION, seed=42)
    demand_data_percentages, PV_data_percentages = load__demand_and_PV_profile_percentages(DATA_PATH_DEMAND, verbose_demand=False, verbose_PV=False)
    
    data['pD'] = build_pD(
        B=data['B'],
        T=data['T'],
        base_demand=base_demand,
        profile=demand_data_percentages,
        verbose=False
    )

    # data['Pmax_line'], data['Pmax_sub'] = network_limits(B=data['B'], L=data['L'], T=data['T'], pD=data['pD'], verbose=False)

    data['PV'] = build_PV(
        B=data['B'],
        T=data['T'],
        base_demand=base_PV,
        profile=PV_data_percentages,
        verbose=False
    )

    price_series = load_year_prices(DATA_PATH_ELECTRICITY_PRICE, year=2025, priced_capped=ELECTRICITY_PRICE_CAP_AT_0, verbose=False)
    data['c'] = convert_series_to_dict(price_series, data['T'])

    data['cP'] = CP
    data['cE'] = CE
    data['gamma'] = GAMMA
    data['SOC_min'] = SOC_MIN
    data['SOC_max'] = SOC_MAX
    data['c_curt'] = {t: max(data['c'][t], 0) for t in data['T']} #as a curtailment price, take the energy price, or when negative 0.
        #t: 100000 for t in data['T']}

    data['ME'], data['MP'] = calculate_Big_M(data['B'], data['T'], data['pD'], verbose = False)

    model = build_model_PV(data)

    results = solve_model(model, tee=True)

    extract_results(model, results, data)




    #Testing:
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
        
        # T_list = list(model.T)

        # for i in model.B:
        #     soc_values = [model.E[i, t].value for t in T_list[:50]]
        #     print(f"Bus {i}: {soc_values}")



    print("Pipeline executed successfully.")

     
if __name__ == "__main__":
    main()