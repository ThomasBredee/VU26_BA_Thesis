import pandas as pd


def load_profile(filepath):
    df = pd.read_csv(
        filepath,
        sep=';',
        decimal='.',
        encoding="utf-8",
        skiprows=6,
        header=0
    )

    df["van"] = pd.to_datetime(df["van"], format="%d-%m-%Y %H:%M")
    df["tot"] = pd.to_datetime(df["tot"], format="%d-%m-%Y %H:%M")

    profile = df[["van", "1.00_E1C_AMI_A"]]
    profile = profile.set_index("van")

    return profile