import pandas as pd

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

import matplotlib.pyplot as plt
profile_1['hour'] = profile_1.index.hour
hourly_pattern = profile_1.groupby('hour').mean()

hourly_pattern.plot()
plt.title("Average Daily Load Pattern")
plt.xlabel("Hour of Day")
plt.ylabel("Value")
plt.show()