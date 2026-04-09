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

    # -----------------------------
    # 1. Slack bus
    # -----------------------------
    slack_bus = int(net.ext_grid.bus.iloc[0])
    B_prime = [slack_bus]

    # -----------------------------
    # 2. Buses (exclude slack)
    # -----------------------------
    B = [int(b) for b in net.bus.index if int(b) != slack_bus]

    # -----------------------------
    # 3. Lines
    # -----------------------------
    # L = [(int(row.from_bus), int(row.to_bus)) for _, row in net.line.iterrows()]

    L = [#(0,1), 
         (1,2), (2,3)]
    Pmax_line = {#(0,1): 8000000,
                 (1,2): 8000000,
                 (2,3): 8000000
                }


    # -----------------------------
    # 4. Line capacities (MW)
    # -----------------------------
    # Pmax_line = {
    #     (int(row.from_bus), int(row.to_bus)):
    #     float(np.sqrt(3) * net.bus.loc[row.from_bus, "vn_kv"] * row.max_i_ka)*1000000 #to go from MW, to W
    #     for _, row in net.line.iterrows()
    # }

    # -----------------------------
    # 5. Substation capacity
    # -----------------------------
    Pmax_sub = 150000 #{slack_bus: float(net.sn_mva)}

    # -----------------------------
    # 6. Output
    # -----------------------------
    data = {
        'B': B,
        'B_prime': B_prime,
        'L': L,
        'Pmax_line': Pmax_line,
        'Pmax_sub': Pmax_sub
    }

    if verbose:
        print("\n=== NETWORK SUMMARY ===")
        print(f"Number of buses: {len(net.bus)}")
        print(f"Number of lines: {len(net.line)}")
        print(f"Substation bus: {net.ext_grid.bus.iloc[0]}")
        plot.simple_plot(net, plot_line_switches=False)

    return data



# net = pn.case33bw()
# data = extract_network_data(net, verbose=True)
# # print(data)