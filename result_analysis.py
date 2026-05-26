import os
import re
import pandas as pd


def summarize_all_pv_results(base_dir="."):
    rows = []

    # --------------------------------------------------
    # Find all result folders
    # --------------------------------------------------
    result_folders = [
        f for f in os.listdir(base_dir)
        if f.startswith("results_")
        and os.path.isdir(os.path.join(base_dir, f))
    ]

    for folder in result_folders:

        try:
            folder_path = os.path.join(base_dir, folder)

            # ==================================================
            # 1. Extract experiment + PV share from folder name
            # ==================================================
            # Example:
            # results_0524_0106_EX3_PV0.75
            match = re.search(
                r"(EX\d+)_PV([0-9.]+)",
                folder
            )

            if match is None:
                print(f"Skipping {folder}: naming issue")
                continue

            experiment = match.group(1)
            pv_share = float(match.group(2))

            # ==================================================
            # 2. Read config settings
            # ==================================================
            config = pd.read_csv(
                os.path.join(
                    folder_path,
                    "config_settings.csv"
                )
            )

            cfg = dict(
                zip(
                    config["parameter"],
                    config["value"]
                )
            )

            pv_scenario = cfg.get(
                "PV_SCENARIO",
                "unknown"
            )

            reactive_mode = cfg.get(
                "PV_REACTIVE_MODE",
                "unknown"
            )

            # ==================================================
            # 3. Read PV summary
            # ==================================================
            pv = pd.read_csv(
                os.path.join(
                    folder_path,
                    "pv_summary.csv"
                )
            )

            total_used = pv["PV_used_kW"].sum()
            total_curt = pv["PV_curtailed_kW"].sum()

            total_generated = (
                total_used + total_curt
            )

            if total_generated > 0:
                curt_pct = (
                    100
                    * total_curt
                    / total_generated
                )
            else:
                curt_pct = 0

            # ==================================================
            # 4. Store row
            # ==================================================
            rows.append({
                "experiment": experiment,
                "PV_share": pv_share,
                "PV_scenario": pv_scenario,
                "reactive_mode": reactive_mode,
                "PV_generated_MWh":
                    total_generated / 1000,
                "PV_used_MWh":
                    total_used / 1000,
                "PV_curtailed_MWh":
                    total_curt / 1000,
                "Curtailment_%":
                    curt_pct
            })

        except Exception as e:
            print(
                f"Skipping {folder}: {e}"
            )

    # ======================================================
    # Build summary dataframe
    # ======================================================
    summary = pd.DataFrame(rows)

    summary = summary.sort_values(
        ["experiment", "PV_share"]
    )

    # Save
    # summary.to_csv(
    #     "all_pv_summary.csv",
    #     index=False
    # )

    return summary

summary = summarize_all_pv_results()

print("\n=== PV EXPERIMENT SUMMARY ===\n")

print(
    summary.to_string(
        index=False,
        float_format=lambda x: f"{x:.2f}"
    )
)