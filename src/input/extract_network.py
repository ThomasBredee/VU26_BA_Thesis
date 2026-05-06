import networkx as nx
import pandas as pd
import pandapower.plotting as plot
import numpy as np
import networkx as nx
import matplotlib.pyplot as plt
from collections import deque


def extract_network_data(net, verbose=False):
    # buses of interest
    bus_a = 18
    bus_b = 8

    print("\n=== Searching in net.line ===")

    matches = net.line[
        ((net.line.from_bus == bus_a) & (net.line.to_bus == bus_b)) |
        ((net.line.from_bus == bus_b) & (net.line.to_bus == bus_a))
    ]

    if not matches.empty:
        print(matches[[
            "from_bus", "to_bus",
            "length_km",
            "r_ohm_per_km", "x_ohm_per_km"
        ]])
    else:
        print("❌ No line found between buses 18 and 8 in net.line")


    # -------------------------
    # Also check switches (VERY important in SimBench)
    # -------------------------
    print("\n=== Searching in net.switch ===")

    switch_matches = net.switch[
        ((net.switch.bus == bus_a) & (net.switch.element == bus_b)) |
        ((net.switch.bus == bus_b) & (net.switch.element == bus_a))
    ]

    if not switch_matches.empty:
        print(switch_matches)
    else:
        print("❌ No switch found between buses 18 and 8")    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
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


    # Check transformer connections
    print(net.trafo[['hv_bus', 'lv_bus', 'sn_mva']])
    for _, row in net.trafo.iterrows():
        print(row)

    # ---------------------------
    # Bus set (excluding slack)
    # ---------------------------
    B = [int(b) for b in net.bus.index if int(b) != slack_bus]
    
    # ---------------------------
    # Lines (edges), and Parent,Children maps.
    # ---------------------------
    L = [
        (int(row.from_bus), int(row.to_bus))
        for _, row in net.line.iterrows()
    ]

    #### THIS CODE DOES NOT WORK?! ####
    # for line in L:
    #     print(line)

    # parent_map = {j: i for (i,j) in L}
    # children_map = {}

    # for (i, j) in L:
    #     if i not in children_map:
    #         children_map[i] = []
    #     children_map[i].append(j)


    # Build undirected adjacency first
    adj = {}
    for (i, j) in L:
        adj.setdefault(i, []).append(j)
        adj.setdefault(j, []).append(i)
    # BFS from slack bus
    parent_map = {}
    children_map = {}
    visited = set()
    queue = deque([14]) #SET 14 here as starting point (slack_bus does not work...)

    visited.add(14)

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

    print(L_tree)

    # # -------------------------
    # # Pretty printing
    # # -------------------------
    # print("\n==============================")
    # print("PARENT MAP (child -> parent)")
    # print("==============================")
    # for child in sorted(parent_map.keys()):
    #     print(f"{child:>5}  →  {parent_map[child]}")

    # print("\n==============================")
    # print("CHILDREN MAP (parent -> children)")
    # print("==============================")
    # for parent in sorted(children_map.keys()):
    #     print(f"{parent:>5}  →  {children_map[parent]}")


    # # -------------------------
    # # Optional: sanity checks
    # # -------------------------
    # all_children = set(parent_map.keys())
    # all_parents = set(children_map.keys())

    # roots = all_parents - all_children
    # leaves = all_children - all_parents

    # print("\n==============================")
    # print("STRUCTURE CHECK")
    # print("==============================")
    # print(f"Root nodes (no parent in map): {sorted(roots)}")
    # print(f"Leaf nodes (no children): {sorted(leaves)}")
    # print(f"Total edges: {len(L)}")
    # print(f"Unique parents: {len(all_parents)}")
    # print(f"Unique children: {len(all_children)}")







































    
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
        S_max_MVA = np.sqrt(3) * V_kv * I_max # Apparent power limit (3-phase)

        # Store using tree orientation (i → j)
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

    B0 = [slack_bus] + B

    return {
        "B": B,
        "B_prime": B0,
        "L": L_tree,
        "parent_map": parent_map,
        "children_map": children_map,
        "Pmax_line": Pmax_line,
        "Pmax_sub": Pmax_sub,
        "S_base_MVA": S_base_MVA,
        "V_base_kV": V_base_kV,
        "Z_base_ohm": Z_base_ohm,
        "r_pu": r_pu,
        "x_pu": x_pu
    }, E_year_kWh_dict, Q_base_kvar_dict, qp_ratio