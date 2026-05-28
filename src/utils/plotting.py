import matplotlib.pyplot as plt


def plot_noise_comparison(original, noisy, n=200):
    """
    Plot original vs noisy profile (first n timesteps)
    """
    plt.figure(figsize=(10, 5))

    plt.plot(original.index[:n], original.iloc[:n], label="Original")
    plt.plot(noisy.index[:n], noisy.iloc[:n], label="Noisy")

    plt.legend()
    plt.title(f"Noise Injection (First {n} Hours)")
    plt.xlabel("Time")
    plt.ylabel("Value")

    plt.show()


def plot_daily_average(profile, naming):
    """
    Plot daily average over the year
    """
    daily = profile.resample('D').mean()

    plt.figure(figsize=(10, 5))
    plt.plot(daily.index, daily.iloc[:, 0])

    name = "Annual Average Dutch Electricity Profile for " + naming

    plt.title(name)
    plt.xlabel("Date")
    plt.ylabel("Value")

    plt.show()


def plot_hourly_pattern(profile, naming):
    """
    Plot average load per hour of the day
    """
    df = profile.copy()  # avoid modifying original

    df["hour"] = df.index.hour
    hourly_pattern = df.groupby("hour").mean()

    plt.figure(figsize=(10, 5))
    plt.plot(hourly_pattern.index, hourly_pattern.iloc[:, 0])

    name = "Average Daily Load Pattern for " + naming

    plt.title(name)
    plt.xlabel("Hour of Day")
    plt.ylabel("Value")

    plt.xticks(range(0, 24))

    plt.show()