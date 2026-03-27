import numpy as np


def resample(profile, freq="h"):
    return profile.resample(freq).sum()


def add_noise(profile, noise_level=0.02, seed=42):
    np.random.seed(seed)

    noise = np.random.normal(0, noise_level, len(profile))

    noisy = profile.copy()
    noisy.iloc[:, 0] = noisy.iloc[:, 0] * (1 + noise)

    # prevent negative values
    noisy.iloc[:, 0] = noisy.iloc[:, 0].clip(lower=0)

    return noisy




# np.random.seed(42)
# noise_level = 0.08
# rho = 0.9  # correlation between hours

# noise = np.zeros(len(profile_1))
# eps = np.random.normal(0, noise_level, len(profile_1))

# for t in range(1, len(noise)):
#     noise[t] = rho * noise[t-1] + eps[t]

# profile_noisy = profile_1.copy()
# profile_noisy.iloc[:, 0] = profile_1.iloc[:, 0] * (1 + noise)
# profile_noisy.iloc[:, 0] = profile_noisy.iloc[:, 0].clip(lower=0)