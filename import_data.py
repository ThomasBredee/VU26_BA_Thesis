import pandas as pd
import matplotlib.pyplot as plt
import pandapower.converter as pc

df = pd.read_csv(
    "Standaardprofielen elektriciteit 2026 versie 1.00.csv",
    sep=';',
    decimal='.',
    encoding="utf-8",
    skiprows=6,
    header=0
)

print("\n -------------------------------- \n The colums are: \n", df.columns)

df["van"] = pd.to_datetime(df["van"], format="%d-%m-%Y %H:%M")
df["tot"] = pd.to_datetime(df["van"], format="%d-%m-%Y %H:%M")


# Will use:
# https://opendata.cbs.nl/#/CBS/nl/dataset/83023NED/table?ts=1774355181788
# E1C_AMI_A (demand - with PV)
# E1C_AMI_I (PV generation)
# E1C_AMI_A (demand - no PV)

profile_1 = df[["van", "1.00_E1C_AMI_A"]]

profile_1 = profile_1.set_index("van")

profile_1 = profile_1.resample('h').sum()

print(profile_1)


import numpy as np

np.random.seed(42)

noise_level = 0.08
rho = 0.9  # correlation between hours

noise = np.zeros(len(profile_1))
eps = np.random.normal(0, noise_level, len(profile_1))

for t in range(1, len(noise)):
    noise[t] = rho * noise[t-1] + eps[t]

profile_noisy = profile_1.copy()
profile_noisy.iloc[:, 0] = profile_1.iloc[:, 0] * (1 + noise)
profile_noisy.iloc[:, 0] = profile_noisy.iloc[:, 0].clip(lower=0)

import matplotlib.pyplot as plt

plt.figure(figsize=(10,5))
plt.plot(profile_1.index[:200], profile_1.iloc[:200], label="Original")
plt.plot(profile_noisy.index[:200], profile_noisy.iloc[:200], label="Noisy")
plt.legend()
plt.title("Noise Injection (First 200 Hours)")
plt.show()


# # Daily (year basis) average PLOT
# daily = profile_1.resample('D').mean()
# daily.plot()
# plt.title("Daily Average Electricity Profile (2026)")
# plt.xlabel("Date")
# plt.ylabel("Value")
# plt.show()


# # Daily load pattern PLOT
# profile_1['hour'] = profile_1.index.hour
# hourly_pattern = profile_1.groupby('hour').mean()

# hourly_pattern.plot()
# plt.title("Average Daily Load Pattern")
# plt.xlabel("Hour of Day")
# plt.ylabel("Value")
# plt.show()