import pandapower.networks as pn

NETWORK_CHOICE = pn.simple_four_bus_system
TIME = 8760

ELECTRICITY_PRICE_CAP_AT_0 = True
# NOISE_LEVEL = 0.02
# # RESAMPLE_FREQ = "h"

DATA_PATH_DEMAND = "data/Standaardprofielen elektriciteit 2026 versie 1.00.csv"
DATA_PATH_ELECTRICITY_PRICE = "data/Netherlands hourly electricity price.csv"

CP = 260
CE = 280
GAMMA = 1

SOC_MIN = 0.2
SOC_MAX = 0.8

HOUSE_MIN_USAGE = 2500
HOUSE_MAX_USAGE = 3500