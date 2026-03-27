from config import DATA_PATH, NOISE_LEVEL, RESAMPLE_FREQ

from src.data.load_data import load_profile
from src.data.preprocess_data import resample, add_noise
# from src.network.create_network import create_network

from src.utils.plotting import (
    plot_noise_comparison,
    plot_daily_average,
    plot_hourly_pattern
)




def main():
    print('Starting pipeline................. \n')

    # Load data
    profile = load_profile(DATA_PATH)

    # Preprocess
    profile = resample(profile, RESAMPLE_FREQ)

    # Add noise
    profile_noisy = add_noise(profile, NOISE_LEVEL)

    # Create network
    # net = create_network()

    # Plot
    plot_noise_comparison(profile, profile_noisy)
    plot_daily_average(profile)
    plot_hourly_pattern(profile)

    print("Pipeline executed successfully.")


if __name__ == "__main__":
    main()