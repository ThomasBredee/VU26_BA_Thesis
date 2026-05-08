from config import (
    NETWORK_CHOICE,
    TIME,
    DATA_PATH_DEMAND, DATA_PATH_ELECTRICITY_PRICE,
    CE, CP, SOC_MIN, SOC_MAX,
    PV_SHARE,
    BATTERY_EFFICIENCY, ALPHA, C_DEG, V_MIN, V_MAX, 
    VERSIONING_TITLE
)

from src.input.extract_network import extract_network_data
from src.input.load_data import load__demand_and_PV_profile_percentages, load_year_prices, convert_series_to_dict
from src.input.preprocess_data import build_pD, build_qD, test_network, build_PV, generate_base_PV, build_S_inv

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

    # Create network
    net = NETWORK_CHOICE 
    
    # test_network(net)
    # robustness_checker()

    data , base_demand, base_reactive_demand, qp_ratio = extract_network_data(net, verbose=False)

    # Create time array
    data['T'] = list(range(TIME))

    # Demand: load generate base demands, extract percentages, concat into noisy profiles
    demand_data_percentages, PV_data_percentages = load__demand_and_PV_profile_percentages(DATA_PATH_DEMAND, verbose_demand=False, verbose_PV=False)
    
    data['pD'] = build_pD(
        B=data['B'],
        T=data['T'],
        base_demand=base_demand,
        profile=demand_data_percentages,
        verbose=False
    )

    data['qD'] = build_qD(qp_ratio, data['pD'])

    # data["MP"] = data["Pmax_sub"]
    # data["ME"] = data["Pmax_sub"] * 12 #making it a 12 hour battery, more free then before.

    base_PV = generate_base_PV(data['B'], base_demand, PV_SHARE)
    data['PV'] = build_PV(
        B=data['B'],
        T=data['T'],
        base_demand=base_PV,
        profile=PV_data_percentages,
        verbose=False
    )
    data['S_inv'] =  build_S_inv(data['B'], data['T'], data['PV'])

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
    data['c_curt'] = {t: max(data['c'][t], 0) for t in data['T']} #as a curtailment price, take the energy price, or when negative 0.
        #t: 100000 for t in data['T']}


    # print("Building model constraints........")
    # model = build_model_reactive(data)

    # print("Solving model ....................")
    # solved_model = solve_model(model, tee=True)

    # if solved_model:
    #     # extract_results(model, results, data)

    #     print("Exporting thesis results........")
    #     export_thesis_results(model, data, versioning=VERSIONING_TITLE)

    # print("Pipeline executed successfully.")
    



     
if __name__ == "__main__":
    main()