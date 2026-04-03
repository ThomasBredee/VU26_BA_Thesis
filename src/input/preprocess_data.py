import numpy as np
import matplotlib.pyplot as plt

def generate_base_demand(B, low=2500, high=3000, seed=None):
    rng = np.random.default_rng(seed)
    return {i: rng.uniform(low, high) for i in B}

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



def plot_bus_profiles_window(pD, B, T, n_buses=3, start=0, horizon=168):
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


