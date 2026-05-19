import pandas as pd    
import pandapower as pp

def robustness_checker():
    # ============================================================
    # MAX LINE LOADING (in p.u.) for test network
    # ============================================================

    # # Load csv
    RESULTS_DIR = "results_0519_1103_0_batteries_and_PV"

    # ============================================================
    # LINE LOADING
    # ============================================================

    df_line = pd.read_csv(f"{RESULTS_DIR}/line_flows.csv")

    # Convert % -> p.u.
    df_line["loading_pu"] = df_line["loading_percent"] / 100.0

    # Maximum loading
    idx = df_line["loading_percent"].idxmax()
    max_line = df_line.loc[idx]

    print("\n[Line Loading]")
    print(
        f"Max loading        : "
        f"{max_line['loading_percent']:.2f} % "
        f"(Line {int(max_line['from_bus'])} -> {int(max_line['to_bus'])})"
    )



    # ============================================================
    # SUBSTATION FLOW
    # ============================================================

    df_sub = pd.read_csv(f"{RESULTS_DIR}/substation.csv")

    # ------------------------------------------------------------
    # Maximum active import
    # ------------------------------------------------------------
    idx_pmax = df_sub["P_sub_kW"].idxmax()
    row_pmax = df_sub.loc[idx_pmax]

    # ------------------------------------------------------------
    # Maximum reactive import
    # ------------------------------------------------------------
    idx_qmax = df_sub["Q_sub_kVar"].abs().idxmax()
    row_qmax = df_sub.loc[idx_qmax]

    print("\n[Substation Flow]")

    print(
        f"Max P import       : "
        f"{row_pmax['P_sub_kW']/1000:.4f} MW "
        f"at t={int(row_pmax['time'])}"
    )

    print(
        f"Max Q import       : "
        f"{row_qmax['Q_sub_kVar']/1000:.4f} MVAr "
        f"at t={int(row_qmax['time'])}"
    )

    # ------------------------------------------------------------
    # Total annual imported energy
    # ------------------------------------------------------------
    energy_imported_mwh = (
        df_sub["P_sub_kW"].clip(lower=0).sum() / 1000
    )

    print(
        f"Annual import      : "
        f"{energy_imported_mwh:.2f} MWh"
    )


    # ============================================================
    # VOLTAGE PROFILE
    # ============================================================

    df_v = pd.read_csv(f"{RESULTS_DIR}/voltage_profiles.csv")

    # ------------------------------------------------------------
    # Global minimum voltage
    # ------------------------------------------------------------
    min_idx = df_v["v_pu"].idxmin()
    min_row = df_v.loc[min_idx]

    # ------------------------------------------------------------
    # Global maximum voltage
    # ------------------------------------------------------------
    max_idx = df_v["v_pu"].idxmax()
    max_row = df_v.loc[max_idx]

    print("\n[Voltage Profile]")

    print(
        f"Min voltage        : "
        f"{min_row['v_pu']:.4f} p.u. "
        f"(Bus {int(min_row['bus'])}, "
        f"t={int(min_row['time'])})"
    )

    print(
        f"Max voltage        : "
        f"{max_row['v_pu']:.4f} p.u. "
        f"(Bus {int(max_row['bus'])}, "
        f"t={int(max_row['time'])})"
    )

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
    
    

