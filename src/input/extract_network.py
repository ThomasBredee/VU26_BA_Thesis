import networkx as nx
import pandas as pd
import pandapower.plotting as plot
import numpy as np


def extract_network_data(net, verbose=False):
    """
    Extract structural network data from a pandapower network.

    Returns:
        dict:
            - B: non-slack buses
            - B_prime: slack bus
            - L: lines (edges)
            - Pmax_line: {(i,j): kW}
            - Pmax_sub: kW
        dict:
            - E_year_kWh_dict: yearly energy per bus
    """

    # ---------------------------
    # Slack bus
    # ---------------------------
    slack_bus = int(net.ext_grid.bus.iloc[0])
    B_prime = [slack_bus]

    # ---------------------------
    # Bus set (excluding slack)
    # ---------------------------
    B = [int(b) for b in net.bus.index if int(b) != slack_bus]
    
    # ---------------------------
    # Lines (edges)
    # ---------------------------
    L = [
        (int(row.from_bus), int(row.to_bus))
        for _, row in net.line.iterrows()
        if row.from_bus != slack_bus and row.to_bus != slack_bus
    ]
    
    # ---------------------------
    # Check if edges create a Radial graph
    # ---------------------------
    
    mg = nx.Graph()
    for _, row in net.line.iterrows():
        if row.in_service:
            mg.add_edge(int(row.from_bus), int(row.to_bus))
    assert nx.is_tree(mg), "Network is not radial"
    

    # ---------------------------
    # Line capacities (kW)
    # ---------------------------

    Pmax_line = {}

    for _, row in net.line.iterrows():
        i = int(row.from_bus)
        j = int(row.to_bus)

        if i == slack_bus or j == slack_bus:
            continue

        I_max = row.max_i_ka
        V_kv = net.bus.vn_kv.at[i]

        S_max_MVA = np.sqrt(3) * V_kv * I_max
        Pmax_line[(i, j)] = S_max_MVA * 1000  # kW


    # ---------------------------
    # Substation capacity (kW)
    # ---------------------------
    trafo = net.trafo.iloc[0]
    S_max_MVA = trafo.sn_mva
    Pmax_sub = S_max_MVA * 1000  # MW → kW


    # ---------------------------
    # Load per bus + yearly energy
    # ---------------------------
    P_base_kw = (
        net.load[net.load.bus.isin(B)]
        .groupby("bus")["p_mw"]
        .sum()
        .reindex(B, fill_value=0)
        * 1000
    )

    load_factor = 0.4
    E_year_kWh = P_base_kw * load_factor * 8760
    E_year_kWh_dict = E_year_kWh.to_dict()


    # ---------------------------
    # Reactive power (snapshot)
    # ---------------------------
    Q_base_kvar = (
        net.load[net.load.bus.isin(B)]
        .groupby("bus")["q_mvar"]
        .sum()
        .reindex(B, fill_value=0)
        * 1000  # MVar → kVar
    )
    Q_base_kvar_dict = Q_base_kvar.to_dict()


    # ---------------------------
    # Power factor ratio (q/p)
    # ---------------------------
    qp_ratio = {}

    for b in B:
        p = P_base_kw.get(b, 0)
        q = Q_base_kvar.get(b, 0)

        if p > 0:
            qp_ratio[b] = q / p
        else:
            qp_ratio[b] = 0.0


    # ---------------------------
    # Per-unit base values
    # ---------------------------
    S_base_MVA = 1.0  # standard choice
    V_base_kV = net.bus.vn_kv.iloc[0]
    Z_base_ohm = (V_base_kV ** 2) / S_base_MVA  # Ω


    # ---------------------------
    # Line impedances (per-unit)
    # ---------------------------
    r_pu = {}
    x_pu = {}

    for _, row in net.line.iterrows():
        i = int(row.from_bus)
        j = int(row.to_bus)

        if i == slack_bus or j == slack_bus:
            continue

        # Physical impedance (IMPORTANT: include length!)
        r_ohm = row.r_ohm_per_km * row.length_km
        x_ohm = row.x_ohm_per_km * row.length_km

        # Convert to per-unit
        r_pu[(i, j)] = r_ohm / Z_base_ohm
        x_pu[(i, j)] = x_ohm / Z_base_ohm





    # ---------------------------
    # Verbose output
    # ---------------------------
    if verbose:
        print("\n" + "="*60)
        print("NETWORK SUMMARY")
        print("="*60)

        # ---------------------------
        # General
        # ---------------------------
        print("\n[General]")
        print(f"Slack bus           : {slack_bus}")
        print(f"Total buses         : {len(net.bus)}")
        print(f"Distribution buses  : {len(B)}")
        print(f"Total lines         : {len(net.line)}")

        # ---------------------------
        # Substation
        # ---------------------------
        print("\n[Substation]")
        print(f"Transformer capacity: {Pmax_sub:.1f} kW")

        # ---------------------------
        # Per-unit base
        # ---------------------------
        print("\n[Per-Unit Base]")
        print(f"S_base              : {S_base_MVA:.2f} MVA")
        print(f"V_base              : {V_base_kV:.3f} kV")
        print(f"Z_base              : {Z_base_ohm:.4f} ohm")

        # ---------------------------
        # Line capacities (compact table)
        # ---------------------------
        print("\n[Lines]")
        if Pmax_line:
            df_lines = pd.DataFrame([
                {
                    "from": i,
                    "to": j,
                    "Pmax_kW": round(Pmax_line[(i, j)], 1),
                    "r_pu": round(r_pu[(i, j)], 4),
                    "x_pu": round(x_pu[(i, j)], 4)
                }
                for (i, j) in L if (i, j) in Pmax_line
            ])
            print(df_lines.head(10).to_string(index=False))

            if len(df_lines) > 10:
                print(f"... ({len(df_lines)} lines total)")
        else:
            print("No active lines found.")

        # ---------------------------
        # Impedance sanity check
        # ---------------------------
        print("\n[Impedance Check]")
        r_vals = np.array(list(r_pu.values()))
        x_vals = np.array(list(x_pu.values()))

        print(f"r_pu range          : {r_vals.min():.4f} – {r_vals.max():.4f}")
        print(f"x_pu range          : {x_vals.min():.4f} – {x_vals.max():.4f}")

        rx_ratio = r_vals / np.maximum(x_vals, 1e-6)
        print(f"R/X ratio (avg)     : {rx_ratio.mean():.2f}")

        # ---------------------------
        # Load summary
        # ---------------------------
        print("\n[Loads]")
        total_P = np.sum(P_base_kw)
        total_Q = np.sum(Q_base_kvar)

        print(f"Total P (snapshot)  : {total_P:.1f} kW")
        print(f"Total Q (snapshot)  : {total_Q:.1f} kvar")

        total_energy = sum(E_year_kWh_dict.values())
        print(f"Total annual energy : {total_energy:.1f} kWh")

        # ---------------------------
        # Power factor check
        # ---------------------------
        print("\n[Power Factor]")
        pf = []
        for b in B:
            p = P_base_kw.get(b, 0)
            q = Q_base_kvar.get(b, 0)
            if p > 0:
                pf.append(p / np.sqrt(p**2 + q**2))

        if pf:
            print(f"PF range            : {min(pf):.3f} – {max(pf):.3f}")
            print(f"PF average          : {np.mean(pf):.3f}")

        # ---------------------------
        # Top loads
        # ---------------------------
        print("\n[Top Load Buses]")
        top_buses = sorted(P_base_kw.items(), key=lambda x: -x[1])[:5]
        for b, p in top_buses:
            print(f"  Bus {b:>3}: {p:>8.1f} kW")

        print("\n" + "="*60 + "\n")

        # ---------------------------
        # Plot
        # ---------------------------
        try:
            plot.simple_plot(net)
        except Exception as e:
            print(f"Plot failed: {e}")

    return {
        "B": B,
        "B_prime": B_prime,
        "L": L,
        "Pmax_line": Pmax_line,
        "Pmax_sub": Pmax_sub,
        "S_base_MVA": S_base_MVA,
        "V_base_kV": V_base_kV,
        "Z_base_ohm": Z_base_ohm,
        "r_pu": r_pu,
        "x_pu": x_pu
    }, E_year_kWh_dict, Q_base_kvar_dict, qp_ratio