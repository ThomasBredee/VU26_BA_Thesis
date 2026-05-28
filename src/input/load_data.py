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
        plot_daily_average(resampled_profile, 'Demand')
        plot_hourly_pattern(resampled_profile, 'Demand')

    if verbose_PV:
        plot_daily_average(resampled_profile_PV, 'PV')
        plot_hourly_pattern(resampled_profile_PV, 'PV')


    return resampled_profile, resampled_profile_PV.values.flatten()



def plot_first_hours_prices(prices_df, n=4385):
    plt.figure(figsize=(12, 5))
    plt.plot(prices_df.index[:n], prices_df['Price'][:n], linestyle='-')
    plt.title(f"Electricity Prices — First {n} Hours")
    plt.xlabel("Datetime")
    plt.ylabel("Price [EUR/MWhe]")
    plt.xticks(rotation=45)
    plt.grid(True)
    plt.tight_layout()
    plt.show()

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

import pandas as pd
import matplotlib.pyplot as plt

def aggregate_to_typical_week(prices_df, start_month, end_month):
    """
    Aggregate multiple months into a single 'typical week'
    by averaging all values for each hour-of-week pattern.

    Parameters
    ----------
    prices_df : pd.DataFrame
        DatetimeIndex + 'Price'
    start_month : int
        Start month (e.g. 1 for January)
    end_month : int
        End month (e.g. 3 for March)

    Returns
    -------
    pd.Series
        Typical week (168 values)
    """

    df = prices_df.copy()

    # Filter months
    df = df[(df.index.month >= start_month) & (df.index.month <= end_month)]

    # Build week structure
    df["day_of_week"] = df.index.dayofweek
    df["hour"] = df.index.hour

    # Aggregate into typical week
    weekly = (
        df.groupby(["day_of_week", "hour"])["Price"]
        .mean()
        .unstack()
        .sort_index()
    )

    # Flatten into 168-hour vector (7 * 24)
    typical_week = weekly.values.flatten()

    return pd.Series(typical_week)



def plot_typical_summer_winter(prices_df):
    """
    Compare seasonal representative weeks:
    winter (Jan–Mar) vs summer (Jul–Sep)
    """

    winter_week = aggregate_to_typical_week(prices_df, 1, 3)
    summer_week = aggregate_to_typical_week(prices_df, 7, 9)

    x = range(168)

    plt.figure(figsize=(14, 5))

    plt.plot(x, winter_week, label="Winter (Jan–Mar)", linewidth=2)
    plt.plot(x, summer_week, label="Summer (Jul–Sep)", linewidth=2)

    plt.title("Typical Weekly Electricity Prices (Seasonal Aggregation)")
    plt.xlabel("Hour of Week (Monday–Sunday)")
    plt.ylabel("Price [EUR/kWh]")
    plt.grid(True, alpha=0.3)
    plt.legend()

    plt.tight_layout()
    plt.show()


def load_year_prices(filepath, year, datetime_col='Datetime (Local)', price_col='Price (EUR/MWhe)', verbose=False):
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

    # Convert the electricity prices from MWh to kWh 
    df['Price'] = df['Price'] / 1000
    
    if verbose:
        plot_first_hours_prices(df)
        # plot_price_boxplot(df)
        plot_typical_summer_winter(df)

    return df

