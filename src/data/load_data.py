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

import pandas as pd

def load_year_prices(filepath, year, datetime_col='Datetime (Local)', price_col='Price (EUR/MWhe)'):
    """
    Load hourly electricity prices from CSV and return only data for a specified year.

    Parameters
    ----------
    filepath : str
        Path to the CSV file.
    year : int
        Year to filter (e.g., 2015).
    datetime_col : str, optional
        Name of the datetime column in the CSV, by default 'Datetime'.
    price_col : str, optional
        Name of the price column in the CSV, by default 'Price'.

    Returns
    -------
    pd.DataFrame
        DataFrame with columns ['Datetime', 'Price'] filtered by the given year,
        sorted by datetime and with a proper DatetimeIndex.
    """
    # Load CSV
    df = pd.read_csv(filepath)

    # Convert datetime column to pandas datetime
    df[datetime_col] = pd.to_datetime(df[datetime_col])

    # Filter by year
    df = df[df[datetime_col].dt.year == year].copy()

    # Keep only relevant columns and rename
    df = df[[datetime_col, price_col]].rename(columns={datetime_col: 'Datetime', price_col: 'Price'})

    # Set DatetimeIndex and sort
    df.set_index('Datetime', inplace=True)
    df.sort_index(inplace=True)

    return df