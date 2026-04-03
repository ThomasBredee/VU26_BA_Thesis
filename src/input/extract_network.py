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
    # 1. Buses
    # -----------------------------
    B = list(net.bus.index)

    # -----------------------------
    # 2. Substation (slack bus)
    # -----------------------------
    slack_bus = net.ext_grid.bus.iloc[0]
    B_prime = [slack_bus]

    # -----------------------------
    # 3. Lines
    # -----------------------------
    L = [(row.from_bus, row.to_bus) for _, row in net.line.iterrows()]

    # -----------------------------
    # 4. Line capacities (MW)
    # -----------------------------
    Pmax_line = {}

    for _, row in net.line.iterrows():
        i = row.from_bus
        j = row.to_bus

        voltage = net.bus.loc[i, "vn_kv"]
        capacity = np.sqrt(3) * voltage * row.max_i_ka

        Pmax_line[(i, j)] = capacity

    # -----------------------------
    # 5. Substation capacity
    # -----------------------------
    Pmax_sub = {slack_bus: net.sn_mva}

    # -----------------------------
    # 6. Output dictionary
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