
from pyomo.environ import *

# data = {
#     'B': [0,1,2],
#     'L': [(0,1),(1,2)],
#     'T': [1,2,3],

#     'pD': {(1,1):5, (1,2):6, (1,3):4},

#     'Pmax_line': {(0,1):10, (1,2):10},
#     'Pmax_sub': 15,

#     'c': {1:50, 2:60, 3:55},

#     'cP': 100,
#     'cE': 50,
#     'gamma': 1,

#     'SOC_min': 0.2,
#     'SOC_max': 0.8,

#     'MP': 10,
#     'ME': 50
# }

def compute_bigM(data):
    """
    Compute Big-M parameters for battery installation.

    Args:
        data (dict): dictionary containing:
            - 'B': list of buses
            - 'L': list of lines as tuples (i,j)
            - 'Pmax_line': dict {(i,j): capacity}
            - 'pD': dict {(i,t): demand}
            - 'T': list of time intervals

    Returns:
        dict: {'MP': dict {i: M_P}, 'ME': dict {i: M_E}}
    """
    B = data['B']
    L = data['L']
    Pmax_line = data['Pmax_line']
    pD = data['pD']
    T = data['T']

    MP = {}
    ME = {}

    for i in B:
        # max line capacity connected to bus i
        connected_line_caps = [
            Pmax_line[(i,j)] for (i2,j) in L if i2 == i
        ] + [
            Pmax_line[(j,i)] for (j,i2) in L if i2 == i
        ]
        max_line = max(connected_line_caps) if connected_line_caps else 0

        # peak demand at bus i
        peak_demand = max(pD.get((i, t), 0) for t in T)

        # Big-M for battery power
        MP[i] = min(max_line, peak_demand)

        # Big-M for battery energy (4-hour assumption)
        ME[i] = 4 * MP[i]

    return {'MP': MP, 'ME': ME}

from pyomo.environ import ConcreteModel, Set, Param, Var, Objective, Constraint, Reals, NonNegativeReals, Binary, minimize

def build_model(data):
    
    # compute Big-M parameters
    bigM_values = compute_bigM(data)
    # update data dictionary
    data['MP'] = bigM_values['MP']
    data['ME'] = bigM_values['ME']

    
    """
    Build a Pyomo MILP model including an explicit substation bus.

    data: dict containing:
        - B: list of distribution buses
        - B_prime: list of substation buses (e.g., ['Substation'])
        - L: list of lines as tuples (i,j)
        - Pmax_line: dict {(i,j): capacity}
        - Pmax_sub: maximum substation injection
        - T: list of time intervals
        - pD: dict {(i,t): demand}
        - c: dict {t: price}
        - cP, cE, gamma: battery costs and operational weight
        - SOC_min, SOC_max: SOC limits
        - MP, ME: Big-M parameters (can be precomputed)
    """




    model = ConcreteModel()

    # -------------------------
    # Sets
    # -------------------------
    model.B = Set(initialize=data['B'])                    # distribution buses
    model.B_prime = Set(initialize=data['B_prime'])        # substation bus(es)
    model.L = Set(within=(model.B | model.B_prime) * (model.B | model.B_prime), initialize=data['L'])  # lines (i,j)
    model.T = Set(initialize=data['T'])                    # time intervals

    # -------------------------
    # Parameters
    # -------------------------
    model.pD = Param(model.B, model.T, initialize=data['pD'], default=0)   # demand at buses
    model.Pmax_line = Param(model.L, initialize=data['Pmax_line'])         # line capacities
    model.Pmax_sub = Param(model.B_prime, initialize=data['Pmax_sub'])     # substation max
    model.c = Param(model.T, initialize=data['c'])                          # electricity price

    model.cP = Param(initialize=data['cP'])                                 # battery power cost
    model.cE = Param(initialize=data['cE'])                                 # battery energy cost
    model.gamma = Param(initialize=data['gamma'])                            # battery operation weight

    model.SOC_min = Param(initialize=data['SOC_min'])
    model.SOC_max = Param(initialize=data['SOC_max'])

    model.MP = Param(model.B, initialize=data['MP'])  # Big-M power per bus
    model.ME = Param(model.B, initialize=data['ME'])  # Big-M energy per bus

    # -------------------------
    # Variables
    # -------------------------
    model.P = Var(model.L, model.T, domain=Reals)                     # line flows
    model.P_sub = Var(model.B_prime, model.T, domain=NonNegativeReals)  # substation injection
    model.p = Var(model.B, model.T, domain=Reals)                     # net injection at bus

    model.b = Var(model.B, domain=Binary)                              # battery installation
    model.Pmax = Var(model.B, domain=NonNegativeReals)                 # installed battery power
    model.Emax = Var(model.B, domain=NonNegativeReals)                 # installed battery energy
    model.pCHA = Var(model.B, model.T, domain=NonNegativeReals)        # charging
    model.pDIS = Var(model.B, model.T, domain=NonNegativeReals)        # discharging
    model.E = Var(model.B, model.T, domain=NonNegativeReals)           # SOC

    # -------------------------
    # Objective
    # -------------------------
    def obj_rule(m):
        return (
            sum(m.c[t] * sum(m.P_sub[s, t] for s in m.B_prime) for t in m.T)
            + sum(m.cP * m.Pmax[i] + m.cE * m.Emax[i] for i in m.B)
            + m.gamma * sum(m.pCHA[i, t] + m.pDIS[i, t] for i in m.B for t in m.T)
        )
    model.OBJ = Objective(rule=obj_rule, sense=minimize)

    # -------------------------
    # Constraints
    # -------------------------

    # Net injection at each bus
    def net_injection_rule(m, i, t):
        return m.p[i, t] == m.pDIS[i, t] - m.pCHA[i, t] - m.pD[i, t]
    model.NetInjection = Constraint(model.B, model.T, rule=net_injection_rule)

    # Power balance: inflow - outflow = net injection
    def power_balance_rule(m, i, t):
        inflow = sum(m.P[j, i, t] for (j, i2) in m.L if i2 == i)
        outflow = sum(m.P[i, j, t] for (i2, j) in m.L if i2 == i)
        return m.p[i, t] == inflow - outflow
    model.PowerBalance = Constraint(model.B, model.T, rule=power_balance_rule)

    # Line capacity limits
    def line_limit_rule(m, i, j, t):
        return (-m.Pmax_line[i, j], m.P[i, j, t], m.Pmax_line[i, j])
    model.LineLimits = Constraint(model.L, model.T, rule=line_limit_rule)

    # Substation limits
    def substation_limit_rule(m, s, t):
        return (0, m.P_sub[s, t], m.Pmax_sub[s])
    model.SubstationLimit = Constraint(model.B_prime, model.T, rule=substation_limit_rule)

    # SOC dynamics
    def soc_rule(m, i, t):
        t_first = m.T.first()
        if t == t_first:
            return m.E[i, t] == 0.5 * m.Emax[i]
        else:
            t_prev = m.T.prev(t)
            return m.E[i, t] == m.E[i, t_prev] + m.pCHA[i, t] - m.pDIS[i, t]
    model.SOC = Constraint(model.B, model.T, rule=soc_rule)

    # SOC limits
    def soc_limit_rule(m, i, t):
        return (m.SOC_min * m.Emax[i], m.E[i, t], m.SOC_max * m.Emax[i])
    model.SOCLimits = Constraint(model.B, model.T, rule=soc_limit_rule)

    # Charging and discharging limits
    def charge_limit_rule(m, i, t):
        return (0, m.pCHA[i, t], m.Pmax[i])
    model.ChargeLimit = Constraint(model.B, model.T, rule=charge_limit_rule)

    def discharge_limit_rule(m, i, t):
        return (0, m.pDIS[i, t], m.Pmax[i])
    model.DischargeLimit = Constraint(model.B, model.T, rule=discharge_limit_rule)

    # Big-M constraints
    def bigM_power_rule(m, i):
        return m.Pmax[i] <= m.MP[i] * m.b[i]
    model.BigM_Power = Constraint(model.B, rule=bigM_power_rule)

    def bigM_energy_rule(m, i):
        return m.Emax[i] <= m.ME[i] * m.b[i]
    model.BigM_Energy = Constraint(model.B, rule=bigM_energy_rule)

    def bigM_charge_rule(m, i, t):
        return m.pCHA[i, t] <= m.MP[i] * m.b[i]
    model.BigM_Charge = Constraint(model.B, model.T, rule=bigM_charge_rule)

    def bigM_discharge_rule(m, i, t):
        return m.pDIS[i, t] <= m.MP[i] * m.b[i]
    model.BigM_Discharge = Constraint(model.B, model.T, rule=bigM_discharge_rule)

    # Power-energy coupling: Pmax <= 0.25 * Emax
    def power_energy_coupling_rule(m, i):
        return m.Pmax[i] <= 0.25 * m.Emax[i]
    model.PowerEnergyCoupling = Constraint(model.B, rule=power_energy_coupling_rule)

    return model