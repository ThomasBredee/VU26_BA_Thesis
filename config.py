import pandapower.networks as pn

NETWORK_CHOICE = pn.case33bw#case30#simple_four_bus_system##
TIME = 8760

# ELECTRICITY_PRICE_CAP_AT_0 = False
# # NOISE_LEVEL = 0.02
# # # RESAMPLE_FREQ = "h"

DATA_PATH_DEMAND = "data/Standaardprofielen elektriciteit 2026 versie 1.00.csv"
DATA_PATH_ELECTRICITY_PRICE = "data/Netherlands hourly electricity price.csv"

WEIGHT_ENERGY_COST = 20
WEIGHT_INVESTMENT_COST = 1
WEIGHT_CURTAILMENT_COST = 1
WEIGHT_DEGRADATION_PENALTY = 0.1
WEIGHT_SLACK_PENALTY = 10000

CP = 260
CE = 280
GAMMA = 1

SOC_MIN = 0.2
SOC_MAX = 0.8

PV_SHARE = 0.15 #15 percent of demand is gerated by PV 