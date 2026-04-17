import numpy as np
import pandapower.plotting as plot
import pandapower.networks as pn


def extract_network_data(net, verbose=False):
    """
    Extract only structural network data from a pandapower network that is given as input.

    Returns:
        dict with:
            - B
            - B_prime
            - L
            - Pmax_line
            - Pmax_sub
    """

    slack_bus = int(net.ext_grid.bus.iloc[0])
    B_prime = [slack_bus]

    B = [int(b) for b in net.bus.index if int(b) != slack_bus]
    L = [(int(row.from_bus), int(row.to_bus)) for _, row in net.line.iterrows()]
    L = [(i, j) for (i, j) in L if i != 0 and j != 0] #remove lines from and to substation


    # Pmax_line = {(i, j): 9200 for (i, j) in L}

    # Pmax_line = {}

    # for _, row in net.line.iterrows():
    #     i = int(row.from_bus)
    #     j = int(row.to_bus)

    #     # skip lines connected to slack if you want
    #     if i == slack_bus or j == slack_bus:
    #         continue

    #     I_max = row.max_i_ka                      # kA
    #     V_kv = net.bus.loc[i, 'vn_kv']            # kV

    #     S_max_mva = np.sqrt(3) * V_kv * I_max     # MVA
    #     P_max_kw = S_max_mva * 1000               # convert to kW

    #     Pmax_line[(i, j)] = P_max_kw

    # for _, row in net.line.iterrows():
    #     std_type = row['std_type']   # THIS is the key

    #     if std_type in net.std_types['line']:
    #         print(net.std_types['line'][std_type]['max_i_ka']) 
    
    # {
    #     (int(row.from_bus), int(row.to_bus)): 9200
    #     for _, row in net.line.iterrows()
    #     # (1,2):9200,
    #     # (2,3):9200,
    #     # (1,3):9200
    # }

    # Pmax_sub = 10
    # print({slack_bus: float(net.sn_mva)})

    data = {
        'B': B,
        'B_prime': B_prime,
        'L': L,
        # 'Pmax_line': Pmax_line,
        # 'Pmax_sub': Pmax_sub
    }

    if verbose:
        print("\n================ NETWORK DATA ================\n")

        print("GENERAL INFO:")
        print(f"  Total buses          : {len(net.bus)}")
        print(f"  Total lines          : {len(net.line)}")
        print(f"  Slack (substation)   : {slack_bus}")
        print(f"  Distribution buses   : {B}")
        print(f"  Substation set B'    : {B_prime}")
        print()

        print("LINES (Directed edges i -> j):")
        for (i, j) in L:
            print(f"  {i} -> {j} ") #  | Pmax = {Pmax_line[(i,j)]}")
        print()

        print("===================================================\n")

        # Optional plot
        try:
            import pandapower.plotting as plot
            plot.simple_plot(net, plot_line_switches=False)
        except:
            print("Plotting failed (non-critical).")

        import networkx as nx
        import matplotlib.pyplot as plt
            # Build graph
        G = nx.DiGraph()
        G.add_nodes_from(B + B_prime)
        G.add_edges_from(L)

        # Layout
        pos = nx.spring_layout(
            G,
            k=5,          # ↑ increases distance between nodes
            iterations=100, # ↑ better convergence
            seed=42
        )

        # Plot
        plt.figure(figsize=(15, 12))
        nx.draw(G, pos,
                with_labels=True,
                node_size=300,
                font_size=8,
                arrows=True)

        # Highlight substation
        nx.draw_networkx_nodes(G, pos, nodelist=B_prime, node_color='red')

        plt.title("Network Graph")
        plt.show()

    return data