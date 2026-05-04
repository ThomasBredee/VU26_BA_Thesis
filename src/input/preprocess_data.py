import numpy as np
import matplotlib.pyplot as plt
import numpy as np
import pandapower as pp

def test_network(net):
    pp.runpp(net)

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
    max_line = loading.idxmax()

    print("\n[Line Loading]")
    print(f"Max loading        : {max_loading:.2f} % (Line {max_line})")



def generate_base_PV(B, base_demand, pv_share, n_pv=8, seed=42):

    rng = np.random.default_rng(seed)
    B = list(B)

    total_demand = sum(base_demand[b] for b in B)
    total_PV_target = pv_share * total_demand

    pv_buses = set(rng.choice(B, size=min(n_pv, len(B)), replace=False))

    base_PV = {}

    total_demand_pv_buses = sum(base_demand[b] for b in pv_buses)
    for b in B:
        if b in pv_buses and total_demand_pv_buses > 0:
            share = base_demand[b] / total_demand_pv_buses
            base_PV[b] = share * total_PV_target
        else:
            base_PV[b] = 0.0  # IMPORTANT: explicitly zero

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

def build_pQ(qp_ratio, pD):
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

    T_window = T[start:start + horizon]

    for bus in B[2:2+n_buses]:
        values = [pD[(bus, t)] for t in T_window]
        plt.plot(T_window, values, label=f'Bus {bus}')

    plt.legend()
    plt.xlabel("Time (hours)")
    plt.ylabel("Demand")
    plt.title(f"Bus Demand Profiles (t={start} to {start+horizon})")
    plt.show()


