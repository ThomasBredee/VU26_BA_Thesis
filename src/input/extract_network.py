import numpy as np
import pandapower.plotting as plot
import pandapower.networks as pn


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
    # Define lines to remove --> these are the tie_lines
    remove_pairs = {
        (7, 20),
        (8, 14),
        (11, 21),
        (17, 32),
        (24, 28)
    }

    # Build raw lines
    raw_lines = [
        (int(row.from_bus), int(row.to_bus))
        for _, row in net.line.iterrows()
    ]

    # Filter L: remove slack connections + specified lines (both directions)
    L = [
        (i, j)
        for (i, j) in raw_lines
        if i != slack_bus
        and j != slack_bus
        and (i, j) not in remove_pairs
        and (j, i) not in remove_pairs
    ]

    # ---------------------------
    # Line capacities (kW)
    # ---------------------------
    net.line["max_i_ka"] = 0.5

    Pmax_line = {}

    for (i, j) in L:
        if i == slack_bus or j == slack_bus:
            continue

        # find matching line
        line = net.line[(net.line.from_bus == i) & (net.line.to_bus == j)]

        if line.empty:
            continue

        row = line.iloc[0]

        if row.max_i_ka is not None:
            I_max = row.max_i_ka  # kA
            V_kv = net.bus.vn_kv.at[i]

            S_max_MVA = (3 ** 0.5) * V_kv * I_max #standard approxiamation --> check the constant
            Pmax_line[(i, j)] = S_max_MVA * 1000  # kW

    # ---------------------------
    # Substation capacity (kW)
    # ---------------------------
    Pmax_sub = net.ext_grid.max_p_mw.iloc[0] * 1000  # MW → kW

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

    E_year_kWh = P_base_kw * 8760
    E_year_kWh_dict = E_year_kWh.to_dict()


    # print(net.line["max_i_ka"].describe())
    # print(net.line["max_i_ka"].head(10))


    # ---------------------------
    # Verbose output
    # ---------------------------
    if verbose:
        print("\n================ NETWORK SUMMARY ================\n")

        print("GENERAL INFO")
        print(f"Slack bus              : {slack_bus}")
        print(f"Total buses           : {len(net.bus)}")
        print(f"Distribution buses    : {len(B)}")
        print(f"Total lines           : {len(net.line)}")
        print()

        print("BUS SETS")
        print(f"B          : {B}")
        print(f"B'         : {B_prime}")
        print()

        print("SUBSTATION")
        print(f"Estimated capacity    : {Pmax_sub:.2f} kW")
        print()

        print("LINES (i → j)")
        for (i, j) in L:
            pmax = Pmax_line.get((i, j), None)
            print(f"  {i} → {j}")
            print(f"      Pmax_line: {pmax}")
        print()

        print("BUS ENERGY (yearly)")
        for b in B:
            e = E_year_kWh_dict.get(b, 0)
            print(f"  Bus {b}: {e:.2f} kWh/year")
        print()

        print("=================================================\n")

    





        # pLotting the network.......................
        import pandas as pd

        coords = {}

        # -------------------------
        # MAIN CHAIN: 1 → 17 (horizontal line)
        # -------------------------
        for i in range(1, 18):
            coords[i] = (i, 0)

        # -------------------------
        # BRANCH: 1 → 18 → 21 (upper branch)
        # -------------------------
        coords[18] = (1, 1)
        coords[19] = (2, 1)
        coords[20] = (3, 1)
        coords[21] = (4, 1)

        # -------------------------
        # BRANCH: 2 → 22 → 24 (upper-mid branch)
        # -------------------------
        coords[22] = (2, -2)
        coords[23] = (3, -2)
        coords[24] = (4, -2)

        # -------------------------
        # LONG BRANCH: 5 → 25 → 32 (lower branch)
        # -------------------------
        for idx, bus in enumerate(range(25, 33)):
            coords[bus] = (5 + idx, -1)

        # -------------------------
        # FIX CROSS CONNECTION TARGETS (ensure alignment looks good)
        # -------------------------
        coords[7]  = (7, 0)
        coords[8]  = (8, 0)
        coords[11] = (11, 0)
        coords[14] = (14, 0)
        coords[17] = (17, 0)

        coords[28] = (8, -1)

        # -------------------------
        # SUBSTATION NODE (0)
        # -------------------------
        coords[0] = (0, 0)


        bus_geodata = pd.DataFrame.from_dict(coords, orient='index', columns=["x", "y"])

        import matplotlib.pyplot as plt

        plt.figure(figsize=(10, 5))

        # draw nodes
        for bus, (x, y) in coords.items():
            plt.scatter(x, y, s=120)
            plt.text(x, y, str(bus),
                    ha='center', va='center',
                    fontsize=9,
                    bbox=dict(facecolor='white', alpha=0.7, edgecolor='none'))

        # draw edges
        edges = [
            (1,2),(2,3),(3,4),(4,5),(5,6),(6,7),(7,8),(8,9),
            (9,10),(10,11),(11,12),(12,13),(13,14),(14,15),
            (15,16),(16,17),
            (1,18),(18,19),(19,20),(20,21),
            (2,22),(22,23),(23,24),
            (5,25),(25,26),(26,27),(27,28),(28,29),(29,30),(30,31),(31,32),
        ]

        for i, j in edges:
            x1, y1 = coords[i]
            x2, y2 = coords[j]
            plt.plot([x1, x2], [y1, y2], 'k-', linewidth=1)

        plt.axis('equal')
        plt.grid(True)
        plt.title("Custom Grid Layout for MILP Network")
        plt.show()















    return {
        "B": B,
        "B_prime": B_prime,
        "L": L,
        "Pmax_line": Pmax_line,
        "Pmax_sub": Pmax_sub
    }, E_year_kWh_dict