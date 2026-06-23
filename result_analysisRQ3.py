def compare_price_years_s1_b0_b2(
    results_root=".",
    price_file="data/Netherlands hourly electricity price.csv",
    folder_b0="results_*_RQ1.2_Batt=0.00_elec=1.00_P=1.00",
    folder_b2="results_*_RQ1.2_Batt=2.00_elec=1.00_P=1.00",
    years=range(2015, 2026),
    cP=360,
    cE=210,
    alpha=0.1295,
    c_deg=0.021,
    plot_metric="Total_Cost_EUR"
):
    import os
    import glob
    import pandas as pd
    import matplotlib.pyplot as plt

    # -------------------------
    # Resolve wildcard folders
    # -------------------------

    def resolve_folder(pattern):

        matches = glob.glob(
            os.path.join(results_root, pattern)
        )

        if len(matches) == 0:
            raise FileNotFoundError(
                f"No folder found for pattern: {pattern}"
            )

        if len(matches) > 1:
            matches = sorted(matches)
            print(
                f"[WARNING] Multiple folders found for {pattern}. "
                f"Using: {matches[-1]}"
            )
            return matches[-1]

        return matches[0]

    folder_b0_path = resolve_folder(folder_b0)
    folder_b2_path = resolve_folder(folder_b2)

    scenarios = {
        "S3.E100.B0": folder_b0_path,
        "S3.E100.B2": folder_b2_path,
    }

    # -------------------------
    # Load all electricity prices
    # -------------------------

    prices = pd.read_csv(price_file)
    prices["Datetime (Local)"] = pd.to_datetime(prices["Datetime (Local)"])
    prices["Year"] = prices["Datetime (Local)"].dt.year

    price_col = "Price (EUR/MWhe)"

    rows = []

    # -------------------------
    # Helper functions
    # -------------------------

    def read_investment_cost(folder):
        battery_file = os.path.join(folder, "batteries.csv")

        if not os.path.exists(battery_file):
            return 0.0

        df_bat = pd.read_csv(battery_file)

        if "battery_installed" in df_bat.columns:
            df_bat = df_bat[df_bat["battery_installed"] > 0]

        if df_bat.empty:
            return 0.0

        investment_cost = alpha * (
            cP * df_bat["Pmax_kW"].sum()
            + cE * df_bat["Emax_kWh"].sum()
        )

        return investment_cost

    def read_degradation_cost(folder):
        soc_file = os.path.join(folder, "soc.csv")

        if not os.path.exists(soc_file):
            return 0.0

        df_soc = pd.read_csv(soc_file)

        if not {"Charge_kW", "Discharge_kW"}.issubset(df_soc.columns):
            return 0.0

        throughput_kwh = (
            df_soc["Charge_kW"].sum()
            + df_soc["Discharge_kW"].sum()
        )

        return c_deg * throughput_kwh

    # -------------------------
    # Evaluate scenarios
    # -------------------------

    for scenario_id, folder in scenarios.items():

        substation_file = os.path.join(folder, "substation.csv")
        pv_file = os.path.join(folder, "pv_summary.csv")

        if not os.path.exists(substation_file):
            raise FileNotFoundError(f"Missing substation.csv in {folder}")

        df_sub = pd.read_csv(substation_file)
        n_hours = len(df_sub)

        investment_cost = read_investment_cost(folder)
        degradation_cost = read_degradation_cost(folder)

        if os.path.exists(pv_file):
            df_pv = pd.read_csv(pv_file)
            curtailed_by_hour = (
                df_pv.groupby("time")["PV_curtailed_kW"]
                .sum()
                .reindex(range(n_hours), fill_value=0)
                .values
            )
        else:
            curtailed_by_hour = [0] * n_hours

        for year in years:

            df_price_year = (
                prices[prices["Year"] == year]
                .sort_values("Datetime (Local)")
                .reset_index(drop=True)
            )

            if len(df_price_year) < n_hours:
                print(
                    f"[WARNING] Skipping {year}: "
                    f"{len(df_price_year)} price rows available, "
                    f"{n_hours} required."
                )
                continue

            price_eur_per_kwh = (
                df_price_year[price_col]
                .iloc[:n_hours]
                .values
                / 1000
            )

            p_import_kwh = (
                df_sub["P_sub_kW"]
                .clip(lower=0)
                .values
            )

            energy_cost = (
                p_import_kwh
                * price_eur_per_kwh
            ).sum()

            curtailment_cost = (
                curtailed_by_hour
                * pd.Series(price_eur_per_kwh).clip(lower=0).values
            ).sum()

            total_cost = (
                energy_cost
                + investment_cost
                + degradation_cost
                + curtailment_cost
            )

            rows.append({
                "Scenario_ID": scenario_id,
                "Resolved_Folder": os.path.basename(folder),
                "Price_Year": year,
                "Energy_Cost_EUR": energy_cost,
                "Investment_Cost_EUR": investment_cost,
                "Degradation_Cost_EUR": degradation_cost,
                "Curtailment_Cost_EUR": curtailment_cost,
                "Total_Cost_EUR": total_cost
            })

    summary = pd.DataFrame(rows)

    # -------------------------
    # Print dataframe
    # -------------------------

    print("\n======================================")
    print("ELECTRICITY MARKET SENSITIVITY SUMMARY")
    print("======================================\n")

    print(
        summary.to_string(
            index=False,
            float_format=lambda x: f"{x:,.2f}"
        )
    )

    # -------------------------
    # Plot two lines
    # -------------------------

    plt.figure(figsize=(9, 5))

    for scenario_id in summary["Scenario_ID"].unique():

        df_plot = (
            summary[summary["Scenario_ID"] == scenario_id]
            .sort_values("Price_Year")
        )

        plt.plot(
            df_plot["Price_Year"],
            df_plot[plot_metric],
            marker="o",
            linewidth=2,
            label=scenario_id
        )

    plt.xlabel("Electricity price year")
    plt.ylabel(plot_metric.replace("_", " "))
    plt.title("Electricity Market Sensitivity Analysis")
    plt.grid(alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.show()

    return summary

def summarize_price_statistics_by_year(
    price_file="data/Netherlands hourly electricity price.csv",
    years=range(2015, 2026)
):
    """
    Print yearly electricity price statistics.

    Returns a dataframe with:
        - Minimum price
        - 1st percentile
        - Mean price
        - 99th percentile
        - Maximum price

    Prices remain in EUR/MWh.
    """

    import pandas as pd

    df = pd.read_csv(price_file)

    df["Datetime (Local)"] = pd.to_datetime(
        df["Datetime (Local)"]
    )

    df["Year"] = df["Datetime (Local)"].dt.year

    price_col = "Price (EUR/MWhe)"

    rows = []

    for year in years:

        df_year = df[df["Year"] == year]

        if len(df_year) == 0:
            continue

        prices = df_year[price_col]

        rows.append({
            "Year": year,
            "Min": prices.min(),
            "P1": prices.quantile(0.01),
            "Mean": prices.mean(),
            "P99": prices.quantile(0.99),
            "Max": prices.max(),
            "Spread_P99_P1": prices.quantile(0.99) - prices.quantile(0.01)
        })

    summary = pd.DataFrame(rows)

    print("\n======================================")
    print("YEARLY ELECTRICITY PRICE STATISTICS")
    print("======================================\n")

    print(
        summary.to_string(
            index=False,
            float_format=lambda x: f"{x:.2f}"
        )
    )
        # ======================================
    # VISUALIZATION
    # ======================================

    import matplotlib.pyplot as plt

    fig, ax1 = plt.subplots(figsize=(10, 5))

    # -----------------------
    # Mean price
    # -----------------------

    ax1.plot(
        summary["Year"],
        summary["Mean"],
        marker="o",
        linewidth=2,
        label="Mean price"
    )

    ax1.set_xlabel("Year")
    ax1.set_ylabel("Mean electricity price [EUR/MWh]")
    ax1.grid(alpha=0.3)

    # -----------------------
    # Volatility
    # -----------------------

    ax2 = ax1.twinx()

    ax2.bar(
        summary["Year"],
        summary["Spread_P99_P1"],
        alpha=0.35,
        width=0.7,
        label="P99-P1 spread"
    )

    ax2.set_ylabel("Price spread [EUR/MWh]")

    # -----------------------
    # Legend
    # -----------------------

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()

    ax1.legend(
        lines1 + lines2,
        labels1 + labels2,
        loc="upper left"
    )

    plt.title(
        "Historical Dutch Electricity Price Levels and Volatility"
    )

    plt.tight_layout()
    plt.show()

    return summary






# market_summary = compare_price_years_s1_b0_b2(
#     results_root=".",
#     folder_b0="results_*_RQ1.2_Batt=0.00_elec=1.00_P=1.00",
#     folder_b2="results_*_RQ1.2_Batt=2.00_elec=1.00_P=1.00",
#     plot_metric="Total_Cost_EUR"
# )

price_stats = summarize_price_statistics_by_year()

