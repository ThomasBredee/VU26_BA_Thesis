from pyomo.environ import value


def to_physical(model, data):
    S_base = data['S_base_kVA']

    def P(x):  # kW
        return x * S_base

    def E(x):  # kWh (assuming dt=1h)
        return x * S_base

    def Euro(x):
        return x  # already monetary in model

    return P, E

import matplotlib.pyplot as plt

def plot_1_economic_performance(model, data):
    P, E = to_physical(model, data)
    S_base = data['S_base_kVA']

    energy_cost = sum(
        value(model.c[t]) * P(value(model.P_sub[s, t]))
        for s in model.B_sub for t in model.T
    )

    investment_cost = value(model.alpha) * sum(
        (value(model.cP) * value(model.Pmax[i]) +
         value(model.cE) * value(model.Emax[i])) * S_base
        for i in model.B
    )

    degradation_cost = value(model.c_deg) * sum(
        (value(model.pCHA[i, t]) + value(model.pDIS[i, t])) * S_base
        for i in model.B for t in model.T
    )

    curtailment_cost = sum(
        value(model.c_curt[t]) * value(model.pPV_curt[i, t]) * S_base
        for i in model.B for t in model.T
    )

    labels = ['Energy', 'Investment', 'Degradation', 'Curtailment']
    values = [energy_cost, investment_cost, degradation_cost, curtailment_cost]

    plt.figure()
    plt.pie(values, labels=labels, autopct='%1.1f%%')
    plt.title("System-Level Economic Breakdown")
    plt.show()


def plot_2_substation_operation(model, data):
    P, _ = to_physical(model, data)

    T = list(model.T)

    P_sub = [
        sum(P(value(model.P_sub[s, t])) for s in model.B_sub)
        for t in T
    ]

    plt.figure()
    plt.plot(T, P_sub)
    plt.title("Substation Power Over Time")
    plt.ylabel("kW")
    plt.xlabel("Time")
    plt.axhline(0, linestyle='--')
    plt.show()

def plot_3_storage(model, data):
    P, E = to_physical(model, data)

    T = list(model.T)
    batteries = [i for i in model.B if value(model.b[i]) > 0.5]

    for i in batteries:
        soc = [E(value(model.E[i, t])) for t in T]

        plt.figure()
        plt.plot(T, soc)
        plt.title(f"Battery SOC at bus {i}")
        plt.ylabel("kWh")
        plt.xlabel("Time")
        plt.show()


def plot_4_pv(model, data):
    P, _ = to_physical(model, data)

    pv_total = sum(P(value(model.PV[i, t]))
                   for i in model.B for t in model.T)

    pv_used = sum(P(value(model.pPV_used[i, t]))
                  for i in model.B for t in model.T)

    pv_curt = sum(P(value(model.pPV_curt[i, t]))
                  for i in model.B for t in model.T)

    plt.figure()
    plt.pie([pv_used, pv_curt],
            labels=["Used", "Curtailed"],
            autopct='%1.1f%%')
    plt.title("PV Utilization")
    plt.show()


def plot_5_network(model, data):
    P, _ = to_physical(model, data)

    T = list(model.T)

    line_usage = {}

    for (i, j) in model.L:
        flow = [abs(P(value(model.P[i, j, t]))) for t in T]
        line_usage[(i, j)] = max(flow)

    top3 = sorted(line_usage.items(),
                  key=lambda x: x[1],
                  reverse=True)[:3]

    for (i, j), _ in top3:
        flows = [P(value(model.P[i, j, t])) for t in T]

        plt.figure()
        plt.plot(T, flows)
        plt.title(f"Line {i}->{j} Flow")
        plt.axhline(value(model.Smax_line[i, j]) * data['S_base_kVA'], linestyle='--')
        plt.axhline(-value(model.Smax_line[i, j]) * data['S_base_kVA'], linestyle='--')
        plt.show()


def plot_6_violations(model, data):
    violations = 0

    for (i, j) in model.L:
        for t in model.T:
            lhs = value(model.v[j, t])
            rhs = value(model.v[i, t]) - 2 * (
                value(model.r[i, j]) * value(model.P[i, j, t]) +
                value(model.x[i, j]) * value(model.Q[i, j, t])
            )

            if abs(lhs - rhs) > 1e-4:
                violations += 1

    print("Total constraint violations:", violations)

    