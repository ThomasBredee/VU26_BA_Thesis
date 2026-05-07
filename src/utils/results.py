from pyomo.environ import value

def economic_performance(model, data):
    S_base = data['S_base_kVA']
    T = list(model.T)

    # --- Objective value ---
    total_cost = value(model.OBJ)

    # --- Cost breakdown (convert to € properly) ---
    energy_cost = sum(
        value(model.c[t]) * value(model.P_sub[s, t]) * S_base
        for s in model.B_sub for t in T
    )

    investment_cost = value(model.alpha) * sum(
        (value(model.cP) * value(model.Pmax[i]) +
         value(model.cE) * value(model.Emax[i])) * S_base
        for i in model.B
    )

    degradation_cost = value(model.c_deg) * sum(
        (value(model.pCHA[i, t]) + value(model.pDIS[i, t])) * S_base
        for i in model.B for t in T
    )

    curtailment_cost = sum(
        value(model.c_curt[t]) * value(model.pPV_curt[i, t]) * S_base
        for i in model.B for t in T
    )

    # --- Optional metrics ---
    total_energy_served = sum(
        value(model.pD[i, t]) * S_base
        for i in model.B for t in T
    )

    cost_per_kWh = total_cost / (total_energy_served + 1e-9)

    return {
        "total_cost": total_cost,
        "energy_cost": energy_cost,
        "investment_cost": investment_cost,
        "degradation_cost": degradation_cost,
        "curtailment_cost": curtailment_cost,
        "cost_per_kWh": cost_per_kWh
    }

def substation_operation(model, data):
    S_base = data['S_base_kVA']
    T = list(model.T)

    P_sub_time = {
        t: sum(value(model.P_sub[s, t]) for s in model.B_sub) * S_base
        for t in T
    }

    total_import = sum(max(P_sub_time[t], 0) for t in T)
    total_export = sum(min(P_sub_time[t], 0) for t in T)

    peak_import = max(P_sub_time.values())
    peak_export = min(P_sub_time.values())

    load_factor = sum(P_sub_time.values()) / (len(T) * (peak_import + 1e-9))

    return {
        "P_sub_time_series": P_sub_time,
        "total_import_kW": total_import,
        "total_export_kW": total_export,
        "peak_import_kW": peak_import,
        "peak_export_kW": peak_export,
        "load_factor": load_factor
    }

def storage_performance(model, data):
    S_base = data['S_base_kVA']
    T = list(model.T)

    installed_batteries = [
        i for i in model.B if value(model.b[i]) > 0.5
    ]

    SOC = {
        i: [value(model.E[i, t]) * S_base for t in T]
        for i in installed_batteries
    }

    installed_sizes = {
        i: {
            "Pmax_kW": value(model.Pmax[i]) * S_base,
            "Emax_kWh": value(model.Emax[i]) * S_base
        }
        for i in installed_batteries
    }

    total_charge = sum(
        value(model.pCHA[i, t]) * S_base for i in model.B for t in T
    )

    total_discharge = sum(
        value(model.pDIS[i, t]) * S_base for i in model.B for t in T
    )

    utilization = total_discharge / (sum(installed_sizes[i]["Emax_kWh"] for i in installed_batteries) + 1e-9)

    return {
        "installed_batteries": installed_batteries,
        "SOC_time_series": SOC,
        "installed_sizes": installed_sizes,
        "charge_kWh": total_charge,
        "discharge_kWh": total_discharge,
        "utilization_rate": utilization
    }

def pv_performance(model, data):
    S_base = data['S_base_kVA']
    T = list(model.T)

    PV_total = sum(
        value(model.PV[i, t]) * S_base
        for i in model.B for t in T
    )

    PV_used = sum(
        value(model.pPV_used[i, t]) * S_base
        for i in model.B for t in T
    )

    PV_curt = sum(
        value(model.pPV_curt[i, t]) * S_base
        for i in model.B for t in T
    )

    self_consumption_ratio = PV_used / (PV_total + 1e-9)
    curtailment_ratio = PV_curt / (PV_total + 1e-9)

    return {
        "PV_total_kWh": PV_total,
        "PV_used_kWh": PV_used,
        "PV_curt_kWh": PV_curt,
        "self_consumption_ratio": self_consumption_ratio,
        "curtailment_ratio": curtailment_ratio
    }

def network_operation(model, data):
    S_base = data['S_base_kVA']
    T = list(model.T)

    # compute congestion score per line
    line_usage = {}

    for (i, j) in model.L:
        flows = [
            abs(value(model.P[i, j, t])) * S_base
            for t in T
        ]
        max_flow = max(flows)
        capacity = value(model.Smax_line[i, j]) * S_base

        line_usage[(i, j)] = {
            "max_flow_kW": max_flow,
            "capacity_kW": capacity,
            "utilization": max_flow / (capacity + 1e-9)
        }

    top3 = sorted(line_usage.items(),
                  key=lambda x: x[1]["utilization"],
                  reverse=True)[:3]

    return {
        "line_usage": line_usage,
        "top_3_congested": top3
    }

def constraint_violations(model, data):
    violations = []

    for (i, j) in model.L:
        for t in model.T:
            lhs = value(model.v[j, t])
            rhs = value(model.v[i, t]) - 2 * (
                value(model.r[i, j]) * value(model.P[i, j, t]) +
                value(model.x[i, j]) * value(model.Q[i, j, t])
            )

            if abs(lhs - rhs) > 1e-4:
                violations.append((i, j, t, lhs - rhs))

    return {
        "num_violations": len(violations),
        "sample": violations[:10]
    }


