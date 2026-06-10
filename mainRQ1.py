from config import *

from src.input.extract_network import extract_network_data
from src.input.load_data import load__demand_and_PV_profile_percentages, load_year_prices, convert_series_to_dict
from src.input.preprocess_data import build_pD, build_qD, test_network, build_PV, generate_base_PV, build_S_inv, rank_buses_for_PV
from src.input.german_profiles import *


# from models.depracted_old_models.basic_model import build_model
# from models.depracted_old_models.model_PV import build_model_PV
# from models.depracted_old_models.model_PV_Slack import build_model_PV_Slack
from src.models.model_reactive import build_model_reactive

from src.utils.solver import solve_model, extract_results

from src.utils.plotting import (
    plot_noise_comparison,
    plot_daily_average,
    plot_hourly_pattern
)

from src.utils.results import *
from src.utils.results_plotting import *
from src.utils.results_export import *

from src.utils.robustness_check import *

def main():
    print('Starting pipeline.................')

    net = NETWORK_CHOICE 
    
    # test_network(net)
    # robustness_checker()

    data , base_demand, base_reactive_demand, qp_ratio = extract_network_data(net, verbose=False)


    print(sum(base_demand.values()))

    data['T'] = list(range(TIME))
    demand_data_percentages, PV_data_percentages = load__demand_and_PV_profile_percentages(DATA_PATH_DEMAND, verbose_demand=False, verbose_PV=False)
    
    


    data['eta'] = BATTERY_EFFICIENCY ** (0.5)
    data['alpha'] = ALPHA
    data['c_deg'] = C_DEG
    data['V_min'] = V_MIN
    data['V_max'] = V_MAX

    price_series = load_year_prices(DATA_PATH_ELECTRICITY_PRICE, year=2025, verbose=False)
    data['c'] = convert_series_to_dict(price_series, data['T'])

    data['cP'] = CP
    data['cE'] = CE
    data['SOC_min'] = SOC_MIN
    data['SOC_max'] = SOC_MAX
    data['c_curt'] = {t: max(data['c'][t], 0) for t in data['T']} 

    print("start base demand", base_demand)
    # bus_ranking = rank_buses_for_PV(PV_SCENARIO, data, verbose = True)
    for num_battery in AMOUNT_OF_BATTERIES:
        for electrification in ELECTRIFICATION_FACTOR:

            pv_share = electrification

            if electrification != 1.0:
                base_demand = {
                    bus: value * electrification
                    for bus, value in base_demand.items()
                }

            print(pv_share)
            print(base_demand[0])
            # if USE_GERMAN_PROFILES:
            #     data['pD'] = build_pD_from_simbench(net, data['B'], data['T'], data["S_base_kVA"], verbose=True)
            #     data['qD'] = build_qD_from_simbench(net, data['B'], data['T'], data["S_base_kVA"], verbose=True)
            # else:
            #     data['pD'] = build_pD(
            #         B=data['B'],
            #         T=data['T'],
            #         base_demand=base_demand,
            #         profile=demand_data_percentages,
            #         verbose=False
            #     )
            #     data['qD'] = build_qD(qp_ratio, data['pD'])

            # base_PV = generate_base_PV(data['B'], base_demand, pv_share, PV_SCENARIO)

            # data['PV'] = build_PV(
            #     B=data['B'],
            #     T=data['T'],
            #     base_demand=base_PV,
            #     profile=PV_data_percentages,
            #     verbose=False
            # )
            
            # data['S_inv'] = build_S_inv(data['B'],data['T'],data['PV'])
    

            # print("\n======================================")
            # print(f"Running BESS {num_battery} + ELECTRIFICATION scenario: {electrification} ")
            # print("======================================")

            # print("Building model constraints........")
            # model = build_model_reactive(data, 
            #                             num_batteries = num_battery
            #                             )

            # print("Solving model ....................")
            # solved_model = solve_model(model, tee=True)

            # if solved_model:
            #     print("Exporting thesis results........")

            #     export_thesis_results(
            #         model,
            #         data,
            #         num_battery,
            #         pv_share,
            #         versioning=f"{VERSIONING_TITLE}_Batt={num_battery:.2f}_elec={electrification:.2f}"
            #     )

            #     print(f"Finished BESS scenario {num_battery:.2f}, elec: {electrification:.2f}")

    print("\nPipeline executed successfully.")
    
     
if __name__ == "__main__":
    main()