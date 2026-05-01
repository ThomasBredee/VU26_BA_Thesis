import numpy as np
import matplotlib.pyplot as plt

def generate_base_demand(B, low=2500, high=3000, seed=None):
    rng = np.random.default_rng(seed)
    return {i: rng.uniform(low, high) for i in B}

import numpy as np

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


def add_ARIMA_noise(profile, noise_level = 0.08, rho = 0.9, seed=42):
    
    #rho is correlation between hours.
    
    np.random.seed(seed)
    
    noise = np.zeros(len(profile))
    eps = np.random.normal(0, noise_level, len(profile))

    for t in range(1, len(noise)):
        noise[t] = rho * noise[t-1] + eps[t]

    profile_noisy = profile.copy()
    profile_noisy.iloc[:, 0] = profile.iloc[:, 0] * (1 + noise)
    profile_noisy.iloc[:, 0] = profile_noisy.iloc[:, 0].clip(lower=0)

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

def calculate_Big_M(B, T, pD, verbose=False):
    ME = {}
    MP = {}

    for i in B:
        total_demand = sum(pD.get((i, t), 0) for t in T)
        ME[i] = 0.05 * total_demand
        MP[i] = 0.25 * ME[i] # making sure its an 4 hour battery
    if verbose:
        print("\n === Big-M Calculation === \n")
        print("ME is: ", ME[1])
        print("MP is: ", MP[1])

    return ME, MP


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

    for bus in B[:n_buses]:
        values = [pD[(bus, t)] for t in T_window]
        plt.plot(T_window, values, label=f'Bus {bus}')

    plt.legend()
    plt.xlabel("Time (hours)")
    plt.ylabel("Demand")
    plt.title(f"Bus Demand Profiles (t={start} to {start+horizon})")
    plt.show()


