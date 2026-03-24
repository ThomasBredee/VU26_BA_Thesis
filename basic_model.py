
from pyomo.environ import *

data = {
    'B': [0,1,2],
    'L': [(0,1),(1,2)],
    'T': [1,2,3],

    'pD': {(1,1):5, (1,2):6, (1,3):4},

    'Pmax_line': {(0,1):10, (1,2):10},
    'Pmax_sub': 15,

    'c': {1:50, 2:60, 3:55},

    'cP': 100,
    'cE': 50,
    'gamma': 1,

    'SOC_min': 0.2,
    'SOC_max': 0.8,

    'MP': 10,
    'ME': 50
}


def build_model(data):

    model = ConcreteModel()

    # -------------------------
    # Sets
    # -------------------------
    model.B = Set(initialize=data['B'])          # buses
    model.L = Set(within=model.B * model.B, initialize=data['L'])  # lines (i,j)
    model.T = Set(initialize=data['T'])          # time

    # -------------------------
    # Parameters
    # -------------------------
    model.pD = Param(model.B, model.T, initialize=data['pD'], default=0)
    model.Pmax_line = Param(model.L, initialize=data['Pmax_line'])
    model.Pmax_sub = Param(initialize=data['Pmax_sub'])
    model.c = Param(model.T, initialize=data['c'])

    model.cP = Param(initialize=data['cP'])
    model.cE = Param(initialize=data['cE'])
    model.gamma = Param(initialize=data['gamma'])

    model.SOC_min = Param(initialize=data['SOC_min'])
    model.SOC_max = Param(initialize=data['SOC_max'])

    model.MP = Param(initialize=data['MP'])   # Big-M power
    model.ME = Param(initialize=data['ME'])   # Big-M energy

    # -------------------------
    # Variables
    # -------------------------
    model.P = Var(model.L, model.T, domain=Reals)              # line flow
    model.P_sub = Var(model.T, domain=NonNegativeReals)        # substation
    model.p = Var(model.B, model.T, domain=Reals)              # net injection

    model.b = Var(model.B, domain=Binary)                      # placement

    model.Pmax = Var(model.B, domain=NonNegativeReals)
    model.Emax = Var(model.B, domain=NonNegativeReals)

    model.pCHA = Var(model.B, model.T, domain=NonNegativeReals)
    model.pDIS = Var(model.B, model.T, domain=NonNegativeReals)
    model.E = Var(model.B, model.T, domain=NonNegativeReals)

    # -------------------------
    # Objective
    # -------------------------
    def obj_rule(m):
        return (
            sum(m.c[t] * m.P_sub[t] for t in m.T)
            + sum(m.cP * m.Pmax[i] + m.cE * m.Emax[i] for i in m.B)
            + m.gamma * sum(m.pCHA[i, t] + m.pDIS[i, t] for i in m.B for t in m.T)
        )

    model.OBJ = Objective(rule=obj_rule, sense=minimize)

    # -------------------------
    # Constraints
    # -------------------------

    # Net injection
    def net_injection_rule(m, i, t):
        return m.p[i, t] == m.pDIS[i, t] - m.pCHA[i, t] - m.pD[i, t]
    model.NetInjection = Constraint(model.B, model.T, rule=net_injection_rule)

    # Power balance
    def power_balance_rule(m, i, t):
        inflow = sum(m.P[j, i, t] for (j, i2) in m.L if i2 == i)
        outflow = sum(m.P[i, j, t] for (i2, j) in m.L if i2 == i)
        return m.p[i, t] == inflow - outflow
    model.PowerBalance = Constraint(model.B, model.T, rule=power_balance_rule)

    # Line limits
    def line_limit_rule(m, i, j, t):
        return (-m.Pmax_line[i, j], m.P[i, j, t], m.Pmax_line[i, j])
    model.LineLimits = Constraint(model.L, model.T, rule=line_limit_rule)

    # Substation limits
    def substation_limit_rule(m, t):
        return m.P_sub[t] <= m.Pmax_sub
    model.SubstationLimit = Constraint(model.T, rule=substation_limit_rule)

    # SOC dynamics
    def soc_rule(m, i, t):
        if t == m.T.first():
            return m.E[i, t] == 0.5 * m.Emax[i]
        else:
            t_prev = m.T.prev(t)
            return m.E[i, t] == m.E[i, t_prev] + m.pCHA[i, t] - m.pDIS[i, t]
    model.SOC = Constraint(model.B, model.T, rule=soc_rule)

    # SOC limits
    def soc_limit_rule(m, i, t):
        return (
            m.SOC_min * m.Emax[i],
            m.E[i, t],
            m.SOC_max * m.Emax[i]
        )
    model.SOCLimits = Constraint(model.B, model.T, rule=soc_limit_rule)

    # Charging limits
    def charge_limit_rule(m, i, t):
        return m.pCHA[i, t] <= m.Pmax[i]
    model.ChargeLimit = Constraint(model.B, model.T, rule=charge_limit_rule)

    # Discharging limits
    def discharge_limit_rule(m, i, t):
        return m.pDIS[i, t] <= m.Pmax[i]
    model.DischargeLimit = Constraint(model.B, model.T, rule=discharge_limit_rule)

    # Big-M constraints
    def bigM_power_rule(m, i):
        return m.Pmax[i] <= m.MP * m.b[i]
    model.BigM_Power = Constraint(model.B, rule=bigM_power_rule)

    def bigM_energy_rule(m, i):
        return m.Emax[i] <= m.ME * m.b[i]
    model.BigM_Energy = Constraint(model.B, rule=bigM_energy_rule)

    def bigM_charge_rule(m, i, t):
        return m.pCHA[i, t] <= m.MP * m.b[i]
    model.BigM_Charge = Constraint(model.B, model.T, rule=bigM_charge_rule)

    def bigM_discharge_rule(m, i, t):
        return m.pDIS[i, t] <= m.MP * m.b[i]
    model.BigM_Discharge = Constraint(model.B, model.T, rule=bigM_discharge_rule)

    return model