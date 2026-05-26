import os
import glob
import re
import pandas as pd


def summarize_all_results(results_root="."):
    rows = []

    # --------------------------------------------------
    # Find all result folders
    # --------------------------------------------------
    folders = glob.glob(
        os.path.join(results_root, "results_*_EX*_PV*")
    )

    for folder in folders:
        try:
            folder_name = os.path.basename(folder)

            # ------------------------------------------
            # Extract experiment + PV from folder name
            # ------------------------------------------
            exp_match = re.search(r"(EX\d+)", folder_name)
            pv_match = re.search(r"PV([\d\.]+)", folder_name)

            experiment = (
                exp_match.group(1)
                if exp_match else "UNKNOWN"
            )

            pv_share = (
                float(pv_match.group(1))
                if pv_match else None
            )

            # ==========================================
            # CONFIG
            # ==========================================
            config = pd.read_csv(
                os.path.join(folder, "config_settings.csv")
            )

            config_dict = dict(
                zip(
                    config["parameter"],
                    config["value"]
                )
            )

            pv_scenario = config_dict.get(
                "PV_SCENARIO",
                "unknown"
            )

            reactive_mode = config_dict.get(
                "PV_REACTIVE_MODE",
                "unknown"
            )

            # ==========================================
            # PV SUMMARY
            # ==========================================
            df_pv = pd.read_csv(
                os.path.join(folder, "pv_summary.csv")
            )

            total_used = df_pv["PV_used_kW"].sum()
            total_curt = df_pv["PV_curtailed_kW"].sum()

            if total_used + total_curt > 0:
                curt_pct = (
                    total_curt /
                    (total_used + total_curt)
                    * 100
                )
            else:
                curt_pct = 0.0

            # ==========================================
            # LINE FLOWS
            # ==========================================
            df_line = pd.read_csv(
                os.path.join(folder, "line_flows.csv")
            )

            idx_max = df_line[
                "loading_percent"
            ].idxmax()

            max_line = df_line.loc[idx_max]

            max_loading = max_line[
                "loading_percent"
            ]

            critical_line = (
                f"{int(max_line['from_bus'])}"
                f"->{int(max_line['to_bus'])}"
            )

            # ==========================================
            # SUBSTATION
            # ==========================================
            df_sub = pd.read_csv(
                os.path.join(folder, "substation.csv")
            )

            max_import = (
                df_sub["P_sub_kW"]
                .max()
                / 1000
            )

            max_export = (
                df_sub["P_sub_kW"]
                .min()
                / 1000
            )

            annual_import = (
                df_sub["P_sub_kW"]
                .clip(lower=0)
                .sum()
                / 1000
            )

            # ==========================================
            # Save row
            # ==========================================
            rows.append({
                "experiment": experiment,
                "PV_share": pv_share,
                "PV_scenario": pv_scenario,
                "reactive_mode": reactive_mode,

                "PV_used_MWh":
                    total_used / 1000,

                "PV_curtailed_MWh":
                    total_curt / 1000,

                "Curtailment_%":
                    curt_pct,

                "Max_line_loading_%":
                    max_loading,

                "Critical_line":
                    critical_line,

                "Max_import_MW":
                    max_import,

                "Max_export_MW":
                    max_export,

                "Annual_import_MWh":
                    annual_import
            })

        except Exception as e:
            print(
                f"Skipping {folder}: {e}"
            )

    # --------------------------------------------------
    # Final dataframe
    # --------------------------------------------------
    summary = pd.DataFrame(rows)

    summary = summary.sort_values(
        ["experiment", "PV_share"]
    )

    # Save csv
    summary.to_csv(
        "all_results_summary.csv",
        index=False,
        float_format="%.2f"
    )

    # --------------------------------------------------
    # Pretty print
    # --------------------------------------------------
    print("\n=== RESULTS SUMMARY ===\n")

    print(
        summary.to_string(
            index=False,
            float_format=lambda x:
                f"{x:,.2f}"
        )
    )

    return summary


summary = summarize_all_results()
