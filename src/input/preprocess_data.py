import numpy as np
import matplotlib.pyplot as plt
import numpy as np
import pandapower as pp
import pandas as pd

def NLSI_calculation(net):
    # ---------
    # Base values
    # -----------------------------
    S_base = net.sn_mva

    # Sending buses
    from_bus = net.line["from_bus"]

    # -----------------------------
    # Line impedance in pu
    # -----------------------------
    V_base = net.bus.loc[from_bus, "vn_kv"].values
    Z_base = (V_base**2) / S_base

    R = (net.line["r_ohm_per_km"] * net.line["length_km"]).values / Z_base
    X = (net.line["x_ohm_per_km"] * net.line["length_km"]).values / Z_base

    # -----------------------------
    # Receiving-end line power (THIS is the key fix)
    # -----------------------------
    Pj = abs(net.res_line["p_to_mw"].values) / S_base
    Qj = abs(net.res_line["q_to_mvar"].values) / S_base

    # -----------------------------
    # Sending-end voltage
    # -----------------------------
    Vi = net.res_bus.loc[from_bus, "vm_pu"].values

    # -----------------------------
    # NLSI
    # -----------------------------
    net.line["NLSI"] = (R * Pj + X * Qj) / (0.25 * Vi**2)

    # Sort highest first
    ranking = net.line.sort_values("NLSI", ascending=False)

    # print(ranking[["from_bus", "to_bus", "NLSI"]])

def test_network(net):
    pp.runpp(net)

    NLSI_calculation(net)

    # ---------------------------
    # Bus voltage statistics
    # ---------------------------
    vm_pu = net.res_bus.vm_pu
    min_v = vm_pu.min()
    max_v = vm_pu.max()

    min_bus = vm_pu.idxmin()
    max_bus = vm_pu.idxmax()

    print("\n[Voltage Profile]")
    print(f"Min voltage        : {min_v:.4f} p.u. (Bus {min_bus})")
    print(f"Max voltage        : {max_v:.4f} p.u. (Bus {max_bus})")

    # ---------------------------
    # Substation power flow
    # ---------------------------
    ext = net.res_ext_grid.iloc[0]

    p_mw = ext.p_mw
    q_mvar = ext.q_mvar

    print("\n[Substation Flow]")
    print(f"P import           : {p_mw:.4f} MW")
    print(f"Q import           : {q_mvar:.4f} MVAr")

    # ---------------------------
    # Line loading
    # ---------------------------
    loading = net.res_line.loading_percent

    max_loading = loading.max()
    max_line_idx = loading.idxmax()

    # Get physical line info
    from_bus = net.line.loc[max_line_idx, "from_bus"]
    to_bus = net.line.loc[max_line_idx, "to_bus"]

    print("\n[Line Loading]")
    print(
        f"Max loading        : {max_loading:.2f} % "
        f"(Line {from_bus} -> {to_bus})"
    )





def generate_base_PV(B, base_demand, pv_penetration, scenario):
    base_PV = {}

    if scenario == 'PV_EVERYWHERE':
        for b in B:
            demand = base_demand.get(b, 0)
            # PV energy proportional to local demand
            base_PV[b] = pv_penetration * demand
    
    if scenario == "WEAKEST_BUS_SEVERITY_SCORE":

        # ==========================================
        # Initialize all buses with zero PV
        # ==========================================
        for b in B:
            base_PV[b] = 0.0

        # ==========================================
        # Total PV budget
        # ==========================================
        total_demand = sum(base_demand.values())

        total_pv_budget = (
            pv_penetration * total_demand
        )

        # ==========================================
        # Top-N weakest buses
        # ==========================================
        topN = 15

        bus_ranking = pd.read_csv(
            "data/bus_ranking_bus_voltage.csv"
        )

        top = bus_ranking.head(topN).copy()

        # expected columns:
        # rank | bus | severity_score

        # ==========================================
        # Add local demand
        # ==========================================
        top["demand"] = (
            top["bus"]
            .map(base_demand)
            .fillna(0)
        )

        # ==========================================
        # Hybrid weighting parameters
        # ==========================================
        alpha = 0.7   # electrical severity importance
        beta  = 0.3   # demand importance

        # ==========================================
        # Hybrid score
        # ==========================================
        top["hybrid_score"] = (
            np.log1p(top["severity_score"]) ** alpha
            *
            np.power(top["demand"], beta)
        )

        # ==========================================
        # Normalize weights
        # ==========================================
        total_score = top["hybrid_score"].sum()

        top["weight"] = (
            top["hybrid_score"]
            / total_score
        )

        # ==========================================
        # Allocate PV
        # ==========================================
        for _, row in top.iterrows():

            bus = int(row["bus"])

            base_PV[bus] = (
                row["weight"]
                * total_pv_budget
            )

        # ==========================================
        # Optional diagnostics
        # ==========================================
        # print("\n======================================")
        # print("PV ALLOCATION (Voltage Severity)")
        # print("======================================")

        # print(
        #     top[
        #         [
        #             "rank",
        #             "bus",
        #             "severity_score",
        #             "demand",
        #             "hybrid_score",
        #             "weight"
        #         ]
        #     ].to_string(index=False)
        # )


    if scenario == "LINE_STABILITY_INDEX":

        # ==========================================
        # Initialize all buses with zero PV
        # ==========================================
        for b in B:
            base_PV[b] = 0.0

        # ==========================================
        # Total PV budget
        # ==========================================
        total_demand = sum(base_demand.values())

        total_pv_budget = (
            pv_penetration * total_demand
        )

        # ==========================================
        # Top-N buses with highest NLSI
        # ==========================================
        topN = 15

        bus_ranking = pd.read_csv(
            "data/bus_ranking_NLSI.csv"
        )

        top = bus_ranking.head(topN).copy()

        # expected columns:
        # rank | bus | nlsi_max

        # ==========================================
        # Add local demand
        # ==========================================
        top["demand"] = (
            top["bus"]
            .map(base_demand)
            .fillna(0)
        )

        # ==========================================
        # Hybrid weighting parameters
        # ==========================================
        alpha = 0.7
        beta  = 0.3

        # ==========================================
        # Hybrid score
        # ==========================================
        top["hybrid_score"] = (
            np.log1p(top["nlsi_max"]) ** alpha
            *
            np.power(top["demand"], beta)
        )

        # ==========================================
        # Normalize weights
        # ==========================================
        total_score = top["hybrid_score"].sum()

        top["weight"] = (
            top["hybrid_score"]
            / total_score
        )

        # ==========================================
        # Allocate PV
        # ==========================================
        for _, row in top.iterrows():

            bus = int(row["bus"])

            base_PV[bus] = (
                row["weight"]
                * total_pv_budget
            )

        # ==========================================
        # Optional diagnostics
        # ==========================================
        # print("\n======================================")
        # print("PV ALLOCATION (NLSI)")
        # print("======================================")

        # print(
        #     top[
        #         [
        #             "rank",
        #             "bus",
        #             "nlsi_max",
        #             "demand",
        #             "hybrid_score",
        #             "weight"
        #         ]
        #     ].to_string(index=False)
        # )

    return base_PV

def normalize_profile(profile):
    values = profile.values.flatten()
    return values / values.sum()


# def add_noise(profile, noise_level=0.02, seed=42):
#     np.random.seed(seed)

#     noise = np.random.normal(0, noise_level, len(profile))

#     noisy = profile.copy()
#     noisy.iloc[:, 0] = noisy.iloc[:, 0] * (1 + noise)

#     # prevent negative values
#     noisy.iloc[:, 0] = noisy.iloc[:, 0].clip(lower=0)

#     return noisy

def add_ARIMA_noise(profile, noise_level=0.08, rho=0.9, seed=42):
    import numpy as np

    # Local random generator (no global side effects)
    rng = np.random.default_rng(seed)

    n = len(profile)

    noise = np.zeros(n)
    eps = rng.normal(0, noise_level, n)

    for t in range(1, n):
        noise[t] = rho * noise[t - 1] + eps[t]

    profile_noisy = profile.copy()

    values = profile.iloc[:, 0].to_numpy()
    noisy_values = values * (1 + noise)
    profile_noisy.iloc[:, 0] = np.clip(noisy_values, 0, None)

    return profile_noisy

def build_pD(B, T, base_demand, profile, verbose=False):
    pD = {}

    for i, bus in enumerate(B):
        noisy_profile_df = add_ARIMA_noise(profile, seed=42 + i)

        noisy_profile = noisy_profile_df.iloc[:, 0].values
        noisy_profile = noisy_profile / noisy_profile.sum()

        for t_idx, t in enumerate(T):
            pD[(bus, t)] = base_demand[bus] * noisy_profile[t_idx]

    if verbose:
        plot_bus_profiles_window(pD, B, T)

    return pD

def build_qD(qp_ratio, pD):
    """
    Construct reactive demand time series from active demand.

    Parameters:
        qp_ratio (dict): {bus: q/p ratio}
        pD (dict): {(bus, t): active demand}

    Returns:
        dict: {(bus, t): reactive demand}
    """
    qD = {}

    for (i, t), p_it in pD.items():
        ratio = qp_ratio.get(i, 0.0)
        qD[(i, t)] = p_it * ratio

    return qD

def network_limits(B, L, T, pD, line_factor=5.0, substation_factor=1, verbose=False):

    total_demand_t = {}

    for t in T:
        total = sum(pD[(i, t)] for i in B)
        total_demand_t[t] = total

    peak_demand = max(total_demand_t.values())

    if verbose:
        print(f"Peak demand: {peak_demand:.2f} kW")

    line_capacity = line_factor * peak_demand
    Pmax_line = {(i, j): line_capacity for (i, j) in L}

    Pmax_sub_value = substation_factor * peak_demand
    Pmax_sub = {0: Pmax_sub_value}

    if verbose:
        print(f"Line capacity: {line_capacity:.2f} kW")
        print(f"Substation capacity: {Pmax_sub_value:.2f} kW")

    return Pmax_line, Pmax_sub

def build_S_inv(B, T, PV):
    S_inv = {}

    for i in B:
        peak_pv = max(PV[(i, t)] for t in T)
        S_inv[i] = 1.1 * peak_pv   # 10% headroom

    return S_inv

def rank_buses_for_PV(pv_scenario, data, verbose = False):
    if pv_scenario == 'WEAKEST_BUS_SEVERITY_SCORE':   
        RESULTS_DIR = "results_0513_1123_0_batteries_and_PV"
        
        df = pd.read_csv(f"{RESULTS_DIR}/voltage_profiles.csv")

        # expected columns:
        # bus,time,v_pu,v_sq_pu

        # ---------------------------------------------------
        # Aggregate per bus
        # ---------------------------------------------------
        summary = (
            df.groupby("bus")["v_pu"]
            .agg(
                v_min="min",
                v_max="max",
                v_mean="mean",
                v_std="std"
            )
            .reset_index()
        )

        # ---------------------------------------------------
        # Compute ranking metrics
        # ---------------------------------------------------
        summary["spread"] = summary["v_max"] - summary["v_min"]

        summary["max_deviation"] = summary.apply(
            lambda row: max(
                abs(row["v_min"] - 1.0),
                abs(row["v_max"] - 1.0)
            ),
            axis=1
        )

        # Combined severity score
        summary["severity_score"] = (
            summary["spread"] +
            summary["max_deviation"]
        )

        # ---------------------------------------------------
        # Rank worst -> best
        # ---------------------------------------------------
        summary = summary.sort_values(
            "severity_score",
            ascending=False
        ).reset_index(drop=True)

        summary["rank"] = summary.index + 1

        # reorder columns
        summary = summary[
            [
                "rank",
                "bus",
                "v_min",
                "v_max",
                "spread",
                "max_deviation",
                "v_mean",
                "v_std",
                "severity_score",
            ]
        ]
        summary.to_csv(
            "data/bus_ranking_bus_voltage.csv",
            index=False
        )
        if verbose:
            # ---------------------------------------------------
            # Print top 10 worst buses
            # ---------------------------------------------------
            print("\n==============================")
            print("BUS VOLTAGE RANKING (Worst → Best)")
            print("==============================")

            print(summary.head(40).to_string(index=False))
        
        return summary
    
    if pv_scenario == "LINE_STABILITY_INDEX":

        RESULTS_DIR = "results_0513_1123_0_batteries_and_PV"

        # ------------------------------------------
        # Load exported model results
        # ------------------------------------------
        df_flow = pd.read_csv(
            f"{RESULTS_DIR}/line_flows.csv"
        )

        df_v = pd.read_csv(
            f"{RESULTS_DIR}/voltage_profiles.csv"
        )

        # Need Q values
        # line_flows.csv should contain:
        # from_bus,to_bus,time,P_kW,Q_kVar,...
        if "Q_kVar" not in df_flow.columns:
            raise ValueError(
                "line_flows.csv must contain Q_kVar "
                "for LINE_STABILITY_INDEX ranking."
            )

        # ------------------------------------------
        # Convert to p.u.
        # ------------------------------------------
        S_base = 1000.0   # kVA (assuming 1 MVA base)

        df_flow["P_pu"] = (
            df_flow["P_kW"].abs() / S_base
        )

        df_flow["Q_pu"] = (
            df_flow["Q_kVar"].abs() / S_base
        )

        # ------------------------------------------
        # Compute NLSI per row
        # ------------------------------------------
        nlsi_values = []

        for _, row in df_flow.iterrows():

            i = int(row["from_bus"])
            j = int(row["to_bus"])
            t = int(row["time"])

            P = row["P_pu"]
            Q = row["Q_pu"]

            # sending bus voltage
            Vi = df_v[
                (df_v["bus"] == i) &
                (df_v["time"] == t)
            ]["v_pu"].values[0]

            # line parameters
            R = data["r_pu"][(i, j)]
            X = data["x_pu"][(i, j)]

            # NLSI
            nlsi = (
                (R * P + X * Q)
                / (0.25 * Vi**2)
            )

            nlsi_values.append({
                "bus": j,
                "time": t,
                "nlsi": nlsi
            })

        df_nlsi = pd.DataFrame(nlsi_values)

        # ------------------------------------------
        # Aggregate per bus
        # ------------------------------------------
        summary = (
            df_nlsi.groupby("bus")["nlsi"]
            .agg(
                nlsi_max="max",
                nlsi_mean="mean",
                nlsi_std="std"
            )
            .reset_index()
        )

        # ------------------------------------------
        # Rank worst -> best
        # ------------------------------------------
        summary = summary.sort_values(
            "nlsi_max",
            ascending=False
        ).reset_index(drop=True)

        summary["rank"] = (
            summary.index + 1
        )

        summary = summary[
            [
                "rank",
                "bus",
                "nlsi_max",
                "nlsi_mean",
                "nlsi_std"
            ]
        ]
        summary.to_csv(
            "data/bus_ranking_NLSI.csv",
            index=False
        )

        if verbose:
            print("\n==============================")
            print("BUS NLSI RANKING (Worst → Best)")
            print("==============================")

            print(
                summary.head(40)
                .to_string(index=False)
            )

        return summary

def build_PV(B, T, base_demand, profile, verbose=False):
    PV = {}

    for i in B:
        for t_idx, t in enumerate(T):
            PV[(i, t)] = base_demand[i] * profile[t_idx]

    if verbose:
        plot_bus_profiles_window(PV, B, T)

    return PV

def plot_bus_profiles_window(pD, B, T, n_buses=3, start=0, horizon=300):
    """
    Plot a smaller time window (default: 1 week = 168 hours)
    """

    T_window = range(3000,3300) #T[start:start + horizon]

    bus_choice = [B[6], B[7], B[22]]

    for bus in bus_choice:#B[2:2+n_buses]:
        values = [pD[(bus, t)] for t in T_window]
        plt.plot(T_window, values, label=f'Bus {bus}')

    plt.legend()
    plt.xlabel("Time (hours)")
    plt.ylabel("Demand")
    plt.title(f"Bus Demand Profiles - AR(1) shifted")
    plt.show()


