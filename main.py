from config import DATA_PATH_DEMAND, DATA_PATH_ELECTRICITY_PRICE, NOISE_LEVEL, RESAMPLE_FREQ

from src.data.load_data import load_profile, load_year_prices
from src.data.preprocess_data import resample, add_noise, add_ARIMA_noise
# from src.network.create_network import create_network

from src.utils.plotting import (
    plot_noise_comparison,
    plot_daily_average,
    plot_hourly_pattern,
    plot_first_hours_prices
)




def main():
    print('Starting pipeline................. \n')

    # Load data
    profile = load_profile(DATA_PATH_DEMAND)

    # Preprocess
    profile = resample(profile, RESAMPLE_FREQ)

    # Add noise
    profile_noisy = add_ARIMA_noise(profile)

    electricity_prices = load_year_prices(DATA_PATH_ELECTRICITY_PRICE, year=2025)
    plot_first_hours_prices(electricity_prices)



    # Create network
    # net = create_network()

    # Plot
    plot_noise_comparison(profile, profile_noisy)
    # plot_daily_average(profile)
    # plot_hourly_pattern(profile)

    print("Pipeline executed successfully.")


if __name__ == "__main__":
    main()