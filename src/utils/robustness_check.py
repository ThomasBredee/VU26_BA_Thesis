import pandas as pd    
import pandapower as pp
import numpy as np


def robustness_checker(
    RESULTS_DIR="results_0519_1443_1bat_0.25PV_weakbus",
    V_MIN=0.95,
    V_MAX=1.05,
    TRAFO_RATING_KVA=400,   # adjust if needed
):
    print("\n" + "="*60)
    print("ROBUSTNESS CHECKER")
    print("="*60)

    
    # ============================================================
    # LINE LOADING
    # ============================================================

    df_line = pd.read_csv(
        f"{RESULTS_DIR}/line_flows.csv"
    )

    df_line["loading_pu"] = (
        df_line["loading_percent"] / 100
    )

    # ------------------------------------------------------------
    # Maximum loading
    # ------------------------------------------------------------
    idx_max = df_line["loading_percent"].idxmax()
    row_max = df_line.loc[idx_max]

    # ------------------------------------------------------------
    # Minimum loading
    # ------------------------------------------------------------
    idx_min = df_line["loading_percent"].idxmin()
    row_min = df_line.loc[idx_min]

    # ------------------------------------------------------------
    # Reverse power flow check
    # ------------------------------------------------------------
    min_P = df_line["P_kW"].min()
    max_P = df_line["P_kW"].max()

    print("\n[Line Loading]")

    print(
        f"Max loading        : "
        f"{row_max['loading_percent']:.2f} % "
        f"({row_max['loading_pu']:.4f} p.u.) "
        f"(Line {int(row_max['from_bus'])} "
        f"-> {int(row_max['to_bus'])}, "
        f"t={int(row_max['time'])})"
    )

    print(
        f"  P flow           : "
        f"{row_max['P_kW']:.2f} kW"
    )

    print(
        f"  Q flow           : "
        f"{row_max['Q_kVar']:.2f} kVAr"
    )

    print(
        f"  S flow           : "
        f"{row_max['S_kVA']:.2f} kVA"
    )

    print()

    print(
        f"Min loading        : "
        f"{row_min['loading_percent']:.2f} % "
        f"(Line {int(row_min['from_bus'])} "
        f"-> {int(row_min['to_bus'])}, "
        f"t={int(row_min['time'])})"
    )

    print(
        f"Distance to limit  : "
        f"{100 - row_max['loading_percent']:.2f} %"
    )

    print()

    print(
        f"Max forward flow   : "
        f"{max_P:.2f} kW"
    )

    print(
        f"Max reverse flow   : "
        f"{min_P:.2f} kW"
    )

    # ------------------------------------------------------------
    # Constraint check
    # ------------------------------------------------------------
    if row_max["loading_percent"] > 100:
        print("⚠️  LINE OVERLOAD DETECTED")
    elif row_max["loading_percent"] > 95:
        print("⚠️  Line close to overload")
    else:
        print("✓ No line overload")


    # ============================================================
    # SUBSTATION FLOW
    # ============================================================
    df_sub = pd.read_csv(f"{RESULTS_DIR}/substation.csv")

    # -------------------
    # Active power
    # -------------------
    idx_pmax = df_sub["P_sub_kW"].idxmax()
    idx_pmin = df_sub["P_sub_kW"].idxmin()

    row_pmax = df_sub.loc[idx_pmax]
    row_pmin = df_sub.loc[idx_pmin]

    # -------------------
    # Reactive power
    # -------------------
    idx_qmax = df_sub["Q_sub_kVar"].idxmax()
    idx_qmin = df_sub["Q_sub_kVar"].idxmin()

    row_qmax = df_sub.loc[idx_qmax]
    row_qmin = df_sub.loc[idx_qmin]

    # -------------------
    # Apparent transformer loading
    # -------------------
    df_sub["S_kVA"] = np.sqrt(
        df_sub["P_sub_kW"]**2 +
        df_sub["Q_sub_kVar"]**2
    )

    df_sub["trafo_loading_percent"] = (
        df_sub["S_kVA"] / TRAFO_RATING_KVA
    ) * 100

    idx_smax = df_sub["trafo_loading_percent"].idxmax()
    row_smax = df_sub.loc[idx_smax]

    # -------------------
    # Annual import
    # -------------------
    annual_import_mwh = (
        df_sub["P_sub_kW"]
        .clip(lower=0)
        .sum() / 1000
    )

    print("\n[Substation Flow]")

    print(
        f"Max P import       : "
        f"{row_pmax['P_sub_kW']/1000:.4f} MW "
        f"at t={int(row_pmax['time'])}"
    )

    print(
        f"Min P (export)     : "
        f"{row_pmin['P_sub_kW']/1000:.4f} MW "
        f"at t={int(row_pmin['time'])}"
    )

    print(
        f"Max Q              : "
        f"{row_qmax['Q_sub_kVar']/1000:.4f} MVAr "
        f"at t={int(row_qmax['time'])}"
    )

    print(
        f"Min Q              : "
        f"{row_qmin['Q_sub_kVar']/1000:.4f} MVAr "
        f"at t={int(row_qmin['time'])}"
    )

    print(
        f"Annual import      : "
        f"{annual_import_mwh:.2f} MWh"
    )

    print(
        f"Max trafo loading  : "
        f"{row_smax['trafo_loading_percent']:.2f} % "
        f"at t={int(row_smax['time'])}"
    )

    print(
        f"Distance to limit  : "
        f"{100 - row_smax['trafo_loading_percent']:.2f} %"
    )

    if row_smax["trafo_loading_percent"] > 100:
        print("⚠️  TRANSFORMER OVERLOAD")
    else:
        print("✓ No transformer overload")


    # ============================================================
    # VOLTAGE PROFILE
    # ============================================================
    df_v = pd.read_csv(f"{RESULTS_DIR}/voltage_profiles.csv")

    idx_vmin = df_v["v_pu"].idxmin()
    idx_vmax = df_v["v_pu"].idxmax()

    row_vmin = df_v.loc[idx_vmin]
    row_vmax = df_v.loc[idx_vmax]

    print("\n[Voltage Profile]")

    print(
        f"Min voltage        : "
        f"{row_vmin['v_pu']:.4f} p.u. "
        f"(Bus {int(row_vmin['bus'])}, "
        f"t={int(row_vmin['time'])})"
    )

    print(
        f"Max voltage        : "
        f"{row_vmax['v_pu']:.4f} p.u. "
        f"(Bus {int(row_vmax['bus'])}, "
        f"t={int(row_vmax['time'])})"
    )

    print(
        f"Distance to V_min  : "
        f"{row_vmin['v_pu'] - V_MIN:.4f} p.u."
    )

    print(
        f"Distance to V_max  : "
        f"{V_MAX - row_vmax['v_pu']:.4f} p.u."
    )

    if row_vmin["v_pu"] < V_MIN:
        print("⚠️  UNDERVOLTAGE VIOLATION")

    if row_vmax["v_pu"] > V_MAX:
        print("⚠️  OVERVOLTAGE VIOLATION")

    if (
        row_vmin["v_pu"] >= V_MIN
        and row_vmax["v_pu"] <= V_MAX
    ):
        print("✓ Voltage limits satisfied")


    # ============================================================
    # PV SUMMARY
    # ============================================================

    try:
        df_pv = pd.read_csv(
            f"{RESULTS_DIR}/pv_summary.csv"
        )

        # -----------------------------------
        # Aggregate totals
        # -----------------------------------
        total_used = (
            df_pv["PV_used_kW"].sum()
        )

        total_curtailed = (
            df_pv["PV_curtailed_kW"].sum()
        )

        total_generated = (
            total_used + total_curtailed
        )

        curtailment_share = (
            100 * total_curtailed
            / total_generated
            if total_generated > 0
            else 0
        )

        utilization_share = (
            100 * total_used
            / total_generated
            if total_generated > 0
            else 0
        )

        print("\n[PV Summary]")

        print(
            f"PV generated       : "
            f"{total_generated/1000:.2f} MWh"
        )

        print(
            f"PV utilized        : "
            f"{total_used/1000:.2f} MWh"
        )

        print(
            f"PV curtailed       : "
            f"{total_curtailed/1000:.2f} MWh"
        )

        print(
            f"Utilization share  : "
            f"{utilization_share:.2f} %"
        )

        print(
            f"Curtailment share  : "
            f"{curtailment_share:.2f} %"
        )

    except FileNotFoundError:
        print("\n[PV Summary]")
        print("pv_summary.csv not found.")

    # print("\n==============================")
    # print("NLSI (Optimization model)")
    # print("==============================")

    # df_flow = pd.read_csv(f"{RESULTS_DIR}/line_flows.csv")
    # df_v = pd.read_csv(f"{RESULTS_DIR}/voltage_profiles.csv")

    # max_nlsi = -1
    # worst_line = None
    # worst_time = None

    # for _, row in df_flow.iterrows():

    #     i = int(row["from_bus"])
    #     j = int(row["to_bus"])
    #     t = int(row["time"])

    #     # --------------------------
    #     # Power in p.u.
    #     # --------------------------
    #     P_pu = abs(row["P_kW"]) / data["S_base_kVA"]

    #     # Need Q too
    #     if "Q_kVar" in df_flow.columns:
    #         Q_pu = abs(row["Q_kVar"]) / data["S_base_kVA"]
    #     else:
    #         Q_pu = 0

    #     # --------------------------
    #     # Sending voltage
    #     # --------------------------
    #     Vi = df_v[
    #         (df_v["bus"] == i) &
    #         (df_v["time"] == t)
    #     ]["v_pu"].values[0]

    #     # --------------------------
    #     # Line impedance
    #     # --------------------------
    #     R = data["r_pu"][(i, j)]
    #     X = data["x_pu"][(i, j)]

    #     # --------------------------
    #     # Compute NLSI
    #     # --------------------------
    #     nlsi = (R * P_pu + X * Q_pu) / (0.25 * Vi**2)

    #     if nlsi > max_nlsi:
    #         max_nlsi = nlsi
    #         worst_line = (i, j)
    #         worst_time = t

    # print(f"Worst line         : {worst_line[0]} -> {worst_line[1]}")
    # print(f"Worst time         : t={worst_time}")
    # print(f"Maximum NLSI       : {max_nlsi:.6f}")

    # if max_nlsi < 1:
    #     print("Status             : STABLE")
    # else:
    #     print("Status             : UNSTABLE")
    
    

