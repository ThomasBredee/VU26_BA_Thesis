import pandas as pd
import matplotlib.pyplot as plt

from src.utils.plotting import (
    plot_daily_average,
    plot_hourly_pattern
)

# Will use:
# https://opendata.cbs.nl/#/CBS/nl/dataset/83023NED/table?ts=1774355181788
# E1C_AMI_A (demand - with PV)
# E1C_AMI_I (PV generation)
# E1C_AMI_A (demand - no PV)

def load__demand_and_PV_profile_percentages(filepath, verbose_demand=False, verbose_PV=False):
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
    resampled_profile = profile.resample("h").sum()

    profile_PV = df[["van", "1.00_E1C_AMI_I"]]
    profile_PV = profile_PV.set_index("van")
    resampled_profile_PV = profile_PV.resample("h").sum()

    resampled_profile = resampled_profile / resampled_profile.sum()
    resampled_profile_PV = resampled_profile_PV / resampled_profile_PV.sum()

    if verbose_demand:
        plot_daily_average(resampled_profile)
        plot_hourly_pattern(resampled_profile)

    if verbose_PV:
        plot_daily_average(resampled_profile_PV)
        plot_hourly_pattern(resampled_profile_PV)


    return resampled_profile, resampled_profile_PV.values.flatten()





def plot_first_hours_prices(prices_df, n=8760):
    plt.figure(figsize=(12, 5))
    plt.plot(prices_df.index[:n], prices_df['Price'][:n], marker='o', linestyle='-')
    plt.title(f"Electricity Prices — First {n} Hours")
    plt.xlabel("Datetime")
    plt.ylabel("Price [EUR/MWhe]")
    plt.xticks(rotation=45)
    plt.grid(True)
    plt.tight_layout()
    plt.show()

import matplotlib.pyplot as plt

def plot_price_boxplot(df, verbose=True):
    """
    Create a boxplot of electricity prices to visualize distribution and outliers.

    Parameters
    ----------
    df : pd.DataFrame
        Must contain a 'Price' column.
    """

    prices = df['Price'].values

    plt.figure()
    plt.boxplot(prices, vert=True, patch_artist=False)

    plt.title("Electricity Price Distribution (Boxplot)")
    plt.ylabel("Price (EUR/MWh)")
    plt.xticks([1], ['Year'])

    # Optional: print stats for deeper debugging
    if verbose:
        print("\n=== PRICE STATISTICS ===")
        print(f"Min     : {prices.min():.2f}")
        print(f"Q1      : {df['Price'].quantile(0.25):.2f}")
        print(f"Median  : {df['Price'].median():.2f}")
        print(f"Q3      : {df['Price'].quantile(0.75):.2f}")
        print(f"Max     : {prices.max():.2f}")
        print(f"Mean    : {prices.mean():.2f}")
        print(f"Std dev : {prices.std():.2f}")

    plt.show()

def convert_series_to_dict(series, T):
    values = series.values.flatten()
    return {t: values[t] for t in T}

def load_year_prices(filepath, year, priced_capped, datetime_col='Datetime (Local)', price_col='Price (EUR/MWhe)', verbose=False):
    """
    Load hourly electricity prices from CSV and return only data for a specified year.

    Parameters
    ----------
    filepath : str
        Path to the CSV file.
    year : int
        Year to filter (e.g., 2015).
    price_capped : Bool
        Yes: prices below 0 are set to 0.
        No: no change to original price
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

    
    if priced_capped:
        df['Price'] = df['Price'].clip(lower=0)

    if verbose:
        plot_first_hours_prices(df)
        plot_price_boxplot(df)

    return df

