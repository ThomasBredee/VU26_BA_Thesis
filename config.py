import pandapower.networks as pn
from simbench.networks import get_simbench_net

NETWORK_CHOICE = get_simbench_net("1-LV-semiurb4--0-sw")

TIME = 8760

DATA_PATH_DEMAND = "data/Standaardprofielen elektriciteit 2026 versie 1.00.csv"
DATA_PATH_ELECTRICITY_PRICE = "data/Netherlands hourly electricity price.csv"

WEIGHT_ENERGY_COST = 20
WEIGHT_INVESTMENT_COST = 1
WEIGHT_CURTAILMENT_COST = 1
WEIGHT_DEGRADATION_PENALTY = 0.1
WEIGHT_SLACK_PENALTY = 10000

CP = 260
CE = 280

SOC_MIN = 0.2
SOC_MAX = 0.8

PV_SHARE = 0.15 #15 percent of demand is gerated by PV 
