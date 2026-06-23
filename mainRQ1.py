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

import os
import pandas as pd


def save_timeseries_dict_to_csv(timeseries_dict, output_path, value_col):
    """
    Saves a dictionary with keys (bus, time) to CSV.
    Example input:
        data['pD'][(bus, t)] = value
        data['PV'][(bus, t)] = value
    """

    df = pd.DataFrame(
        [
            {
                "bus": bus,
                "time": time,
                value_col: value
            }
            for (bus, time), value in timeseries_dict.items()
        ]
    )

    df = df.sort_values(["bus", "time"])

    df.to_csv(output_path, index=False)

    print(f"Saved: {output_path}")

def main():
    print('Starting pipeline.................')

    net = NETWORK_CHOICE 
    
    # test_network(net)
    # robustness_checker()

    data , base_demand_original, base_reactive_demand, qp_ratio = extract_network_data(net, verbose=False)



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

    
    # bus_ranking = rank_buses_for_PV(PV_SCENARIO, data, verbose = True)
    for num_battery in AMOUNT_OF_BATTERIES:
        for electrification, pv_share in zip(ELECTRIFICATION_FACTOR, PV_SHARE):

            base_demand = {
                bus: value * electrification
                for bus, value in base_demand_original.items()
            }

            if USE_GERMAN_PROFILES:
                data['pD'] = build_pD_from_simbench(net, data['B'], data['T'], data["S_base_kVA"], verbose=True)
                data['qD'] = build_qD_from_simbench(net, data['B'], data['T'], data["S_base_kVA"], verbose=True)
            else:
                data['pD'] = build_pD(
                    B=data['B'],
                    T=data['T'],
                    base_demand=base_demand,
                    profile=demand_data_percentages,
                    verbose=False
                )
                data['qD'] = build_qD(qp_ratio, data['pD'])

            print("PV share: ",pv_share)
            print("PV scene: ",PV_SCENARIO)
            base_PV = generate_base_PV(data['B'], base_demand, pv_share, PV_SCENARIO)

            print("Base_PV: ", base_PV)

            data['PV'] = build_PV(
                B=data['B'],
                T=data['T'],
                base_demand=base_PV,
                profile=PV_data_percentages,
                verbose=False
            )
            
            data['S_inv'] = build_S_inv(data['B'],data['T'],data['PV'])

            os.makedirs("data", exist_ok=True)

            scenario_name = (
                f"elec={electrification:.2f}_PV={pv_share:.2f}"
            )

            save_timeseries_dict_to_csv(
                data["pD"],
                output_path=f"data/pD_{scenario_name}.csv",
                value_col="pD_pu"
            )

            save_timeseries_dict_to_csv(
                data["PV"],
                output_path=f"data/PV_{scenario_name}.csv",
                value_col="PV_pu"
            )
    

            # print("\n======================================")
            # print(f"Running BESS {num_battery} + ELECTRIFICATION scenario: {electrification} + PV_share {pv_share} ")
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
            #         versioning=f"{VERSIONING_TITLE}_Batt={num_battery:.2f}_elec={electrification:.2f}_P={pv_share:.2f}"
            #     )

            #     print(f"Finished BESS scenario {num_battery:.2f}, elec: {electrification:.2f}, pv: {pv_share:.2f}")

    print("\nPipeline executed successfully.")
    
     
if __name__ == "__main__":
    main()