import networkx as nx
import pandas as pd
import pandapower.plotting as plot
import numpy as np
import networkx as nx
import matplotlib.pyplot as plt
from collections import deque


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
    # Per-unit base values
    # ---------------------------
    S_base_MVA = 1.0  # standard choice
    S_base_kVA = S_base_MVA * 1000 # for later conversion!
    V_base_kV = float(net.bus.vn_kv.loc[net.trafo.lv_bus.iloc[0]]) #net.bus.vn_kv.iloc[0] #replaced by a more robust version...
    Z_base_ohm = (V_base_kV ** 2) / S_base_MVA  # Ω


    # ---------------------------
    # Slack bus
    # ---------------------------
    slack_bus = int(net.ext_grid.bus.iloc[0])

    slack_bus = int(net.ext_grid.bus.iloc[0]) # 129, MV side
    lv_root  = int(net.trafo.lv_bus.iloc[0])  # 14,  LV side
    B_sub = [slack_bus]

    # ---------------------------
    # Bus set (excluding slack)
    # ---------------------------
    B = [int(b) for b in net.bus.index if int(b) != slack_bus]

    B_0 = [slack_bus] + B
    
    # ---------------------------
    # Lines (edges), and Parent,Children maps.
    # ---------------------------
    L = [
        (int(row.from_bus), int(row.to_bus))
        for _, row in net.line.iterrows()
    ]

    # Build undirected adjacency first
    adj = {}
    for (i, j) in L:
        adj.setdefault(i, []).append(j)
        adj.setdefault(j, []).append(i)
    # BFS from slack bus
    parent_map = {}
    children_map = {}
    visited = set()
    queue = deque([lv_root]) #SET 14 here as starting point (slack_bus does not work...)

    visited.add(lv_root)

    while queue:
        parent = queue.popleft()

        for neighbor in adj.get(parent, []):
            if neighbor not in visited:
                visited.add(neighbor)
                parent_map[neighbor] = parent

                if parent not in children_map:
                    children_map[parent] = []
                children_map[parent].append(neighbor)

                queue.append(neighbor)
    
    L_tree = [(parent_map[j], j) for j in parent_map]


    # ---------------------------
    # Check if edges create a Radial graph
    # ---------------------------
    mg = nx.Graph()
    for _, row in net.line.iterrows():
        if row.in_service:
            mg.add_edge(int(row.from_bus), int(row.to_bus))
    assert nx.is_tree(mg), "Network is not radial"
    

    # ---------------------------
    # Line capacities (kW) - Apparent power limit
    # ---------------------------
    Pmax_line = {}
    for (i, j) in L_tree:

        match = net.line[(net.line.from_bus == i) & (net.line.to_bus == j)] # Try direct match

        if match.empty:
            match = net.line[(net.line.from_bus == j) & (net.line.to_bus == i)]  # If not found → try reversed direction

        # Still not found
        if match.empty:
            raise ValueError(f"No physical line found for edge ({i}, {j})")
        row = match.iloc[0]

        I_max = row.max_i_ka
        V_kv = net.bus.vn_kv.at[i]
        S_max_line_MVA = np.sqrt(3) * V_kv * I_max # Apparent power limit (3-phase)

        # Store using tree orientation (i → j)
        Pmax_line[(i, j)] = S_max_line_MVA / S_base_MVA#* 1000  # kW Unit conversion to p.u.


    # ---------------------------
    # Substation capacity (kW)
    # ---------------------------
    trafo = net.trafo.iloc[0]
    S_max_MVA = trafo.sn_mva
    Pmax_sub = S_max_MVA / S_base_MVA#* 1000  # MW → kW

    # -------------------------------------------------
    # Transformer apparent power limit
    # -------------------------------------------------
    Pmax_line[(slack_bus, lv_root)] = trafo.sn_mva / S_base_MVA #* 1000   # kVA

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

    load_factor = 0.25 ################################################################TODO: this will be the basis for the model.
    E_year_pu = (P_base_kw/S_base_kVA) * load_factor * 8760
    E_year_pu_dict = E_year_pu.to_dict()


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
    Q_base_pu = Q_base_kvar / S_base_kVA
    Q_base_pu_dict = Q_base_pu.to_dict()
    #Q_base_kvar_dict = Q_base_kvar.to_dict()


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
    # Line impedances (per-unit)
    # ---------------------------
    r_pu = {}
    x_pu = {}

    for (i, j) in L_tree:

        # Try direct match
        match = net.line[(net.line.from_bus == i) & (net.line.to_bus == j)]

        # If not found → try reversed
        if match.empty:
            match = net.line[(net.line.from_bus == j) & (net.line.to_bus == i)]

        # If still not found → error (or handle switches)
        if match.empty:
            raise ValueError(f"No physical line found for edge ({i}, {j})")

        row = match.iloc[0]

        # Physical impedance (include length!)
        r_ohm = row.r_ohm_per_km * row.length_km
        x_ohm = row.x_ohm_per_km * row.length_km

        # Convert to per-unit
        r_pu[(i, j)] = r_ohm / Z_base_ohm
        x_pu[(i, j)] = x_ohm / Z_base_ohm

    # -------------------------------------------------
    # Transformer impedance in SYSTEM per-unit
    # -------------------------------------------------
    trafo = net.trafo.iloc[0]

    vk_percent = trafo.vk_percent      # 6.0
    vkr_percent = trafo.vkr_percent    # 1.2

    # S_max_MVA = trafo.sn_mva         # 0.4 MVA
    # S_base_MVA = S_base_MVA            # e.g. 1.0

    r_trafo = (vkr_percent / 100)  # Resistance in transformer p.u.
    z_trafo = (vk_percent / 100) # Total impedance in transformer p.u.
    x_trafo = (z_trafo**2 - r_trafo**2)**0.5 # Reactance in transformer p.u.
    scale = S_base_MVA / S_max_MVA # Convert to SYSTEM base

    r_trafo_sys = r_trafo * scale
    x_trafo_sys = x_trafo * scale

    r_pu[(slack_bus, lv_root)] = r_trafo_sys
    x_pu[(slack_bus, lv_root)] = x_trafo_sys

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

        total_energy = sum(E_year_pu_dict.values())
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



    # # -------------------------
    # # Build graph from L
    # # -------------------------
    # G = nx.DiGraph()

    # for (i, j) in L:
    #     G.add_edge(i, j)


    # # -------------------------
    # # Layout (tree-like)
    # # -------------------------
    # pos = nx.spring_layout(G, seed=46)  # stable layout

    # # -------------------------
    # # Draw graph
    # # -------------------------
    # plt.figure(figsize=(10, 6))

    # nx.draw(
    #     G,
    #     pos,
    #     with_labels=True,
    #     node_size=200,        # smaller blobs
    #     node_color="lightblue",
    #     arrows=True,
    #     arrowsize=15,
    #     font_size=9,
    #     width=1.2
    # )

    # # -------------------------
    # # Add explicit labels (bus numbers again, clearer)
    # # -------------------------
    # labels = {node: str(node) for node in G.nodes()}
    # nx.draw_networkx_labels(G, pos, labels, font_size=10)

    # plt.title("Distribution Network (Parent → Children)")
    # plt.axis("off")
    # plt.tight_layout()
    # plt.show()
    

    # Nodes that should have a parent but don't
    nodes_without_parent = [
        j for j in B
        if j != slack_bus and j not in parent_map
    ]
    for j in nodes_without_parent:
        # print(f"Adding missing edge: ({slack_bus} -> {j})")
        L_tree.append((slack_bus, j))


    # Add transformer branch: 129 -> 14
    parent_map[lv_root] = slack_bus

    if 129 not in children_map:
        children_map[129] = []

    children_map[129].append(14)


    return {
        "B": B,
        "B_0": B_0,
        "B_sub": B_sub,
        "L": L_tree,
        "parent_map": parent_map,
        "children_map": children_map,
        "Pmax_line": Pmax_line,
        "Pmax_sub": Pmax_sub,
        "S_base_MVA": S_base_MVA,
        "S_base_kVA": S_base_kVA,
        # "V_base_kV": V_base_kV,
        # "Z_base_ohm": Z_base_ohm,
        "r_pu": r_pu,
        "x_pu": x_pu
    }, E_year_pu_dict, Q_base_pu_dict, qp_ratio