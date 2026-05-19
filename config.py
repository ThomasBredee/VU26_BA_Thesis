import pandapower.networks as pn
from simbench.networks import get_simbench_net


VERSIONING_TITLE = "1bat_DE"

NETWORK_CHOICE = get_simbench_net("1-LV-semiurb4--2-sw")
# "1-LV-semiurb4--0-sw" "1-LV-semiurb4--1-sw" "1-LV-semiurb4--2-sw"
TIME = 8760

DATA_PATH_DEMAND = "data/Standaardprofielen elektriciteit 2026 versie 1.00.csv"
DATA_PATH_ELECTRICITY_PRICE = "data/Netherlands hourly electricity price.csv"


BATTERY_EFFICIENCY = 0.95

CP = 360
CE = 210

def capital_recovery_factor(r=0.05, L=10):
    return (r * (1 + r) ** L) / ((1 + r) ** L - 1)
r_discount = 0.05
l_battery = 10
ALPHA = capital_recovery_factor(r_discount, l_battery)


def degradation_cost_per_kwh(cE, N_cycles):
    return cE / (2 * N_cycles)
n_cycles = 5000
C_DEG = degradation_cost_per_kwh(CE, n_cycles)

V_MIN = 0.95 
V_MAX = 1.05

SOC_MIN = 0.2
SOC_MAX = 0.8

AMOUNT_OF_BATTERIES = 1

ALLOW_ENERGY_EXPORT = False
OPTIMALITY_GAP_SOLVER = 0.01

USE_GERMAN_PROFILES = True

PV_SHARE = 0.25 #[0.0, 0.25, 0.50, 0.75, 1.0] #TODO: Run all these with a for-loop later.
PV_SCENARIO = 'LINE_STABILITY_INDEX'
                # 'WEAKEST_BUS_SEVERITY_SCORE'
                #'PV_EVERYWHERE'
                # 'LINE_STABILITY_INDEX', 
