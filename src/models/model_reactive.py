from pyomo.environ import *
from pyomo.environ import ConcreteModel, Set, Param, Var, Binary, NonNegativeReals, Reals, Objective, Constraint, minimize, value, quicksum
import math
from config import NO_BATTERIES

def build_model_reactive(data):

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
        - cP, cE: battery costs for Power and Energy
        - SOC_min, SOC_max: SOC limits
        - MP, ME: Big-M parameters (can be precomputed)
    """


    model = ConcreteModel()

    # -------------------------
    # Sets
    # -------------------------
    model.B = Set(initialize=data['B'])                    # distribution buses, set: [0,1,2,3,....]
    model.B0 = Set(initialize=data['B_0'])             # substation bus + all buses , set: [129] + [0,1,2,3,....]
    model.B_sub = Set(initialize=data['B_sub'])         #substation bus only
    model.L = Set(dimen=2, initialize=data['L'])
    model.T = Set(initialize=data['T'])                    # time intervals, t=[0, 1, 2, ..., 8759]

    # -------------------------
    # Parameters
    # -------------------------
    model.r = Param(model.L, initialize=data['r_pu'])   # resistance (p.u.)
    model.x = Param(model.L, initialize=data['x_pu'])   # reactance (p.u.) 
    model.Smax_line = Param(model.L, initialize=data['Pmax_line'])     # Line apparent power limit (kVA or p.u. consistent)
    model.v_min = Param(initialize=data['V_min']**2)   # (0.95)^2     # Voltage limits (squared p.u.)
    model.v_max = Param(initialize=data['V_max']**2)   # (1.05)^2     # Voltage limits (squared p.u.)
    
    model.pD = Param(model.B, model.T, initialize=data['pD'], default=0)   # Active demand
    model.qD = Param(model.B, model.T, initialize=data['qD'], default=0)   # Reactive demand

    
    model.S_inv = Param(model.B, initialize=data['S_inv'])     # PV inverter apparent power rating
    model.eta = Param(initialize=data['eta'])  # ~0.9747     # Battery efficiency (one-way)
    model.dt = Param(initialize=1)     # Time step
    model.alpha = Param(initialize=data['alpha'])     # Annuity factor
    model.c_deg = Param(initialize=data['c_deg'])     # Degradation cost per kWh throughput
    
    model.E_CAP = Param(initialize=4 * data['Pmax_sub']) #Big-M constraint.

    model.c = Param(model.T, initialize=data['c'])                          # electricity price at substation for every time t in T.

    model.cP = Param(initialize=data['cP'])                                 # battery power cost
    model.cE = Param(initialize=data['cE'])                                 # battery energy cost

    model.SOC_min = Param(initialize=data['SOC_min'])     # SOC minimum for batteries
    model.SOC_max = Param(initialize=data['SOC_max'])     # SOC maximum for batteries

    model.PV = Param(model.B, model.T, initialize=data['PV'], default=0)
    model.c_curt = Param(model.T, initialize=data['c_curt'])  # €/kWh penalty


    # -------------------------
    # Variables
    # -------------------------
    model.P = Var(model.L, model.T, domain=Reals)               # Active power flow on lines (i -> j, parent-to-child convention)
    model.P_sub = Var(model.B_sub, model.T, domain=Reals)     # Substation power (now allows export as well → Reals, NOT NonNegative)

    model.b = Var(model.B, domain=Binary)                       # install battery or not
    model.Pmax = Var(model.B, domain=NonNegativeReals)          # battery power rating (kW or p.u.)
    model.Emax = Var(model.B, domain=NonNegativeReals)          # battery energy capacity (kWh or p.u.)

    model.pCHA = Var(model.B, model.T, domain=NonNegativeReals) # charging power
    model.pDIS = Var(model.B, model.T, domain=NonNegativeReals) # discharging power
    model.E = Var(model.B, model.T, domain=NonNegativeReals)    # state of charge (SOC)

    model.pPV_used = Var(model.B, model.T, domain=NonNegativeReals)
    model.pPV_curt = Var(model.B, model.T, domain=NonNegativeReals)

    model.Q = Var(model.L, model.T, domain=Reals)               # Reactive power flow on lines (parent -> child)
    model.v = Var(model.B0, model.T, domain=NonNegativeReals)   # Squared voltage magnitude (p.u.^2)
    model.Q_sub = Var(model.B_sub, model.T, domain=Reals)     # Reactive power at substation (grid exchange)
    model.qPV = Var(model.B, model.T, domain=Reals)             # PV reactive power injection (can be positive or negative)

    # -------------------------
    # Objective (LinDistFlow-consistent)
    # -------------------------
    def obj_rule(m):
        energy_cost = sum(
            m.c[t] * (m.P_sub[s, t] * data['S_base_kVA']) * m.dt
            for s in m.B_sub
            for t in m.T
        )
        investment_cost = m.alpha * sum(
            m.cP * m.Pmax[i] * data['S_base_kVA'] + m.cE * m.Emax[i] * data['S_base_kVA']
            for i in m.B
        )
        degradation_cost = m.c_deg * sum(
            (m.pCHA[i, t] + m.pDIS[i, t]) * data['S_base_kVA'] * m.dt
            for i in m.B
            for t in m.T
        )
        curtailment_cost = sum(
            m.c_curt[t] * m.pPV_curt[i, t] * data['S_base_kVA'] * m.dt
            for i in m.B
            for t in m.T
        )
        return energy_cost + investment_cost + degradation_cost + curtailment_cost
    model.OBJ = Objective(rule=obj_rule, sense=minimize)

    # -------------------------
    # Constraints
    # -------------------------

    # NOTE: THESE 2 CONSTRAINTS ARE JUST KEPT HERE FOR QUICK DEBUGGING RUNS..................
    # # Fixing batteries of the model OR force battery placement somewhere:
    # def fixing_batteries(m,i ):
    #     if i in [17, 32]:
    #         return m.b[i] == 1
    #     else:
    #         return m.b[i] == 0
    # model.LinearRelaxation = Constraint(model.B, rule = fixing_batteries)

    # #OR this battery rule:
    if NO_BATTERIES:
        def battery_budget_rule(m):
            return sum(m.b[i] for i in m.B) <= 0
        model.BatteryBudget = Constraint(rule=battery_budget_rule)
        


    # # Active power balance rule for all buses.
    def active_balance_rule(m, j, t):
        parent = data['parent_map'].get(j, None)
        children = data['children_map'].get(j, [])

        inflow = 0
        if parent is not None:
            inflow += m.P[parent, j, t]

        return inflow - sum(m.P[j, k, t] for k in children) == (
            m.pD[j, t] - m.pPV_used[j, t] + m.pCHA[j, t] - m.pDIS[j, t]
        )
    model.ActiveBalance = Constraint(model.B, model.T, rule=active_balance_rule)

    # # Reactive power balance rule for all buses.
    def reactive_balance_rule(m, j, t):
        parent = data['parent_map'].get(j, None)
        children = data['children_map'].get(j, [])

        inflow = 0
        if parent is not None:
            inflow += m.Q[parent, j, t]

        return inflow - sum(m.Q[j, k, t] for k in children) == (
            m.qD[j, t] - m.qPV[j, t]
        )
    model.ReactiveBalance = Constraint(model.B, model.T, rule=reactive_balance_rule)

        # # Substation active balance
    def substation_balance_P(m, t):
        s = list(m.B_sub)[0]
        return m.P_sub[s, t] == sum(m.P[i, j, t] for (i, j) in m.L if i == s)
    model.SubstationP = Constraint(model.T, rule=substation_balance_P)

    # Substation reactive balance
    def substation_balance_Q(m, t):
        s = list(m.B_sub)[0]
        return m.Q_sub[s, t] == sum(m.Q[i, j, t] for (i, j) in m.L if i == s)
    model.SubstationQ = Constraint(model.T, rule=substation_balance_Q)




    # Voltage drop (LinDistFlow)
    def voltage_drop_rule(m, i, j, t):
        return m.v[j, t] == m.v[i, t] - 2 * (
            m.r[i, j] * m.P[i, j, t] +
            m.x[i, j] * m.Q[i, j, t]
        )
    model.VoltageDrop = Constraint(model.L, model.T, rule=voltage_drop_rule)

    # Substation Slack (fix substation at 1 p.u.)
    def slack_voltage_rule(m, t):
        s = list(m.B_sub)[0]
        return m.v[s, t] == 1.025**2 ### Updated, instead of 1.0, based on the fact that net.ext_grid.vm_pu = 1.025^2
    model.SlackVoltage = Constraint(model.T, rule=slack_voltage_rule)


    # Voltage limits
    def voltage_limits_rule(m, i, t):
        return (m.v_min, m.v[i, t], m.v_max)
    model.VoltageLimits = Constraint(model.B, model.T, rule=voltage_limits_rule)


    # Precompute angles.
    K = 8
    theta_list = [2 * math.pi * k / K for k in range(K)]
    model.K = RangeSet(0, K - 1)
    model.theta = Param(model.K, initialize={k: theta_list[k] for k in range(K)})


    # Line apparent power limits (polygon)
    def line_limit_rule(m, i, j, t, k):
        theta = m.theta[k]
        return (
            m.P[i, j, t] * math.cos(theta) +
            m.Q[i, j, t] * math.sin(theta)
            <= m.Smax_line[i, j]
        )
    model.LineLimits = Constraint(model.L, model.T, model.K, rule=line_limit_rule)

    ########  THIS FUNCTION IS DROPPED BECAUSE LINE 129 -> 14 IS ADDED #################
    # # Substation apparent power limit
    # def substation_limit_rule(m, t, k):
    #     theta = m.theta[k]
    #     return (
    #         m.P_sub[t] * math.cos(theta) +
    #         m.Q_sub[t] * math.sin(theta)
    #         <= m.S_trafo
    #     )
    # model.SubstationLimits = Constraint(model.T, model.K, rule=substation_limit_rule)


    #PV linking:
    def pv_split_rule(m, i, t):
        return m.pPV_used[i, t] + m.pPV_curt[i, t] == m.PV[i, t]
    model.PVSplit = Constraint(model.B, model.T, rule=pv_split_rule)
    
    # PV inverter apparent power constraint (polygon)
    def pv_inverter_limit_rule(m, i, t, k):
        theta = m.theta[k]
        return (
            m.pPV_used[i, t] * math.cos(theta) +
            m.qPV[i, t] * math.sin(theta)
            <= m.S_inv[i]
        )
    model.PVInverterLimits = Constraint(model.B, model.T, model.K, rule=pv_inverter_limit_rule)


    # SOC dynamics (correct efficiency form)
    def soc_rule(m, i, t):
        t_first = m.T.first()
        
        if t == t_first:
            return Constraint.Skip   # no fixed initial SOC
        else:
            t_prev = m.T.prev(t)
            return m.E[i, t] == (
                m.E[i, t_prev]
                + m.eta * m.pCHA[i, t] * m.dt
                - (1 / m.eta) * m.pDIS[i, t] * m.dt
            )
    model.SOC = Constraint(model.B, model.T, rule=soc_rule)


    # Cyclic SOC constraint
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


    def power_energy_coupling_rule(m, i):
        return m.Pmax[i] == m.Emax[i] / 4
    model.PowerEnergyCoupling = Constraint(model.B, rule=power_energy_coupling_rule)

 

    def bigM_energy_rule(m, i):
        return m.Emax[i] <= m.E_CAP * m.b[i]
    model.BigM_Energy = Constraint(model.B, rule=bigM_energy_rule)
    
        

    return model