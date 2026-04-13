
from pyomo.environ import *
from pyomo.environ import ConcreteModel, Set, Param, Var, Binary, NonNegativeReals, Reals, Objective, Constraint, minimize, value, quicksum


# def compute_bigM(data):
#     """
#     Compute Big-M parameters for battery installation.

#     Args:
#         data (dict): dictionary containing:
#             - 'B': list of buses
#             - 'L': list of lines as tuples (i,j)
#             - 'Pmax_line': dict {(i,j): capacity}
#             - 'pD': dict {(i,t): demand}
#             - 'T': list of time intervals

#     Returns:
#         dict: {'MP': dict {i: M_P}, 'ME': dict {i: M_E}}
#     """
#     B = data['B']
#     L = data['L']
#     Pmax_line = data['Pmax_line']
#     pD = data['pD']
#     T = data['T']

#     MP = {}
#     ME = {}

#     for i in B:
#         # max line capacity connected to bus i
#         connected_line_caps = [
#             Pmax_line[(i,j)] for (i2,j) in L if i2 == i
#         ] + [
#             Pmax_line[(j,i)] for (j,i2) in L if i2 == i
#         ]
#         max_line = max(connected_line_caps) if connected_line_caps else 0

#         # peak demand at bus i
#         peak_demand = max(pD.get((i, t), 0) for t in T)

#         # Big-M for battery power
#         MP[i] = min(max_line, peak_demand)

#         # Big-M for battery energy (4-hour assumption)
#         ME[i] = 4 * MP[i]

#     return {'MP': MP, 'ME': ME}
def compute_bigM(data, duration_hours=12, safety_factor=1.1):
    """
    Compute Big-M parameters for battery installation in Watts and Watt-hours.

    Args:
        data (dict): must contain keys:
            - 'B': list of buses
            - 'L': list of lines as tuples (i,j)
            - 'Pmax_line': dict {(i,j): line capacity in W}
            - 'pD': dict {(i,t): demand in W}
            - 'T': list of time intervals
        duration_hours (float): assumed hours for full battery discharge
        safety_factor (float): small multiplier >1 to ensure feasibility

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
        # Maximum line capacity connected to this bus (single line, not sum)
        connected_line_caps = [
            Pmax_line[(i,j)] for (i2,j) in L if i2 == i
        ] + [
            Pmax_line[(j,i)] for (j,i2) in L if i2 == i
        ]
        max_line = max(connected_line_caps) if connected_line_caps else 0

        # Peak demand at this bus
        peak_demand = max(pD.get((i, t), 0) for t in T)

        # Big-M for battery power (W): the largest feasible instantaneous injection
        MP[i] = safety_factor * max(max_line, peak_demand)

        # Big-M for battery energy (Wh): assume battery can store duration_hours of MP
        ME[i] = safety_factor * MP[i] * duration_hours

    return {'MP': MP, 'ME': ME}

from pyomo.environ import ConcreteModel, Set, Param, Var, Objective, Constraint, Reals, NonNegativeReals, Binary, minimize

def build_model(data):
    
    # compute Big-M parameters
    # bigM_values = compute_bigM(data)
    # print(bigM_values)
    # update data dictionary
    # data['MP'] = bigM_values['MP']
    # data['ME'] = bigM_values['ME']

    # print(data['MP'], data['ME'])


    MP = {i: 250 for i in data['B']} #TODO: stond eerst op 6 stiill needs to be adjusted!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    ME = {i: 700 for i in data['B']}
    data['MP'] = MP
    data['ME'] = ME


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
    model.B = Set(initialize=data['B'])                    # distribution buses, set: [1,2,3,....]
    model.B_prime = Set(initialize=data['B_prime'])        # substation bus(es), set: [0]
    # TOO General... model.L = Set(within=(model.B | model.B_prime) * (model.B | model.B_prime), initialize=data['L'])  # lines (i,j)
    model.L = Set(dimen=2, initialize=data['L'])
    model.T = Set(initialize=data['T'])                    # time intervals, t=[0, 1, 2, ..., 8759]

    # -------------------------
    # Parameters
    # -------------------------
    model.pD = Param(model.B, model.T, initialize=data['pD'], default=0)   # demand at buses [1,2,3,...]
    model.Pmax_line = Param(model.L, initialize=data['Pmax_line'])         # line capacities 
    model.Pmax_sub = Param(model.B_prime, initialize=data['Pmax_sub'])     # substation max supply per timestep
    model.c = Param(model.T, initialize=data['c'])                          # electricity price at substation for every time t in T.

    model.cP = Param(initialize=data['cP'])                                 # battery power cost
    model.cE = Param(initialize=data['cE'])                                 # battery energy cost
    model.gamma = Param(initialize=data['gamma'])                            # battery operation weight 

    model.SOC_min = Param(initialize=data['SOC_min'])     # SOC minimum for batteries
    model.SOC_max = Param(initialize=data['SOC_max'])     # SOC maximum for batteries

    model.MP = Param(model.B, initialize=data['MP'])  # Big-M power per bus
    model.ME = Param(model.B, initialize=data['ME'])  # Big-M energy per bus

    # -------------------------
    # Variables
    # -------------------------
    model.P = Var(model.L, model.T, domain=Reals)                     # line flows of power, positive means i -> j, negative means j -> i
    model.P_sub = Var(model.B_prime, model.T, domain=NonNegativeReals)  # substation injection of electricity into the first bus.
    model.p = Var(model.B, model.T, domain=Reals)                     # net injection at bus

    model.b = Var(model.B, domain=Binary)                              # battery installation 1=yes, 0=no
    model.Pmax = Var(model.B, domain=NonNegativeReals)                 # installed battery power at bus
    model.Emax = Var(model.B, domain=NonNegativeReals)                 # installed battery energy at bus
    model.pCHA = Var(model.B, model.T, domain=NonNegativeReals)        # charging power at timestep t, at bus b
    model.pDIS = Var(model.B, model.T, domain=NonNegativeReals)        # discharging power at timestep t, at bus b
    model.E = Var(model.B, model.T, domain=NonNegativeReals)           # SOC of battery at timestep t, at bus b
    model.u = Var(model.B, model.T, domain=Binary)                     # Binary variable for charging OR discharging at battery

    # -------------------------
    # Objective
    # -------------------------
    def obj_rule(m):
        energy_cost = sum(
            m.c[t] * sum(m.P_sub[s, t] for s in m.B_prime) for t in m.T
        )
        investment_cost = sum(
            m.cP * m.Pmax[i] + m.cE * m.Emax[i] for i in m.B
        )
        operation_cost = 0.1*sum(
            m.pCHA[i, t] + m.pDIS[i, t] for i in m.B for t in m.T
        )
        return energy_cost + investment_cost + operation_cost
    model.OBJ = Objective(rule=obj_rule, sense=minimize)

    # -------------------------
    # Constraints
    # -------------------------

    # # Linear relaxation of the model OR force battery placement somewhere:
    def linear_relaxation(m, i):
        if i == 1:
            return m.b[i] == 0
        if i == 2:
            return m.b[i] == 0
        if i == 3:
            return m.b[i] == 1
    model.LinearRelaxation = Constraint(model.B, rule = linear_relaxation)
    
     # Net injection at each bus
    def net_injection_rule(m, i, t):
        if i == 1:
            #Bus 1 gets the powerinjection from the substation extra!!
            return m.p[i,t] == m.pDIS[i, t] - m.pCHA[i, t] - m.pD[i, t] + m.P_sub[0,t]
        return m.p[i, t] == m.pDIS[i, t] - m.pCHA[i, t] - m.pD[i, t]
    model.NetInjection = Constraint(model.B, model.T, rule=net_injection_rule)
    
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

    def soc_cycle_rule(m, i):
        t_first = m.T.first()
        t_last = m.T.last()
        return m.E[i, t_last] == m.E[i, t_first]
    model.SOCCycle = Constraint(model.B, rule=soc_cycle_rule)

    # SOC >= SOC_min * Emax
    def soc_lower_limit_rule(m, i, t):
        return m.E[i, t] >= m.SOC_min * m.Emax[i]
    model.SOCLowerLimits = Constraint(model.B, model.T, rule=soc_lower_limit_rule)

    # SOC <= SOC_max * Emax
    def soc_upper_limit_rule(m, i, t):
        return m.E[i, t] <= m.SOC_max * m.Emax[i]
    model.SOCUpperLimits = Constraint(model.B, model.T, rule=soc_upper_limit_rule)

    # Upper bound: discharging <= Pmax
    def discharge_upper_rule(m, i, t):
        return m.pDIS[i, t] <= m.Pmax[i]
    model.DischargeUpper = Constraint(model.B, model.T, rule=discharge_upper_rule)
    # Upper bound: charging <= Pmax
    def charge_upper_rule(m, i, t):
        return m.pCHA[i, t] <= m.Pmax[i]
    model.ChargeUpper = Constraint(model.B, model.T, rule=charge_upper_rule)

    # Charging only if u = 1
    def charge_switch_rule(m, i, t):
        return m.pCHA[i, t] <= m.Pmax[i] * m.u[i, t]
    model.ChargeSwitch = Constraint(model.B, model.T, rule=charge_switch_rule)

    # Discharging only if u = 0
    def discharge_switch_rule(m, i, t):
        return m.pDIS[i, t] <= m.Pmax[i] * (1 - m.u[i, t])
    model.DischargeSwitch = Constraint(model.B, model.T, rule=discharge_switch_rule)


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


    # Constraint to make sure that when a battery is placed, it actually has capacity
    def min_power_rule(m, i):
        return m.Pmax[i] >= 0.01 * m.b[i]
    model.MinPower = Constraint(model.B, rule=min_power_rule)

    def min_energy_rule(m, i):
        return m.Emax[i] >= 0.01 * m.b[i]
    model.MinEnergy = Constraint(model.B, rule=min_energy_rule)


    # Power-energy coupling: Pmax <= 0.25 * Emax
    def power_energy_coupling_rule(m, i):
        return m.Pmax[i] <= 0.25 * m.Emax[i]
    model.PowerEnergyCoupling = Constraint(model.B, rule=power_energy_coupling_rule)

    return model