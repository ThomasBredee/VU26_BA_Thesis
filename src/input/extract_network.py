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

    Pmax_line = {
        (int(row.from_bus), int(row.to_bus)): 9200
        for _, row in net.line.iterrows()
    }

    Pmax_sub = 1500 #{slack_bus: float(net.sn_mva)}

    data = {
        'B': B,
        'B_prime': B_prime,
        'L': L,
        'Pmax_line': Pmax_line,
        'Pmax_sub': Pmax_sub
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
            print(f"  {i} -> {j}   | Pmax = {Pmax_line[(i,j)]}")
        print()

        print("===================================================\n")

        # Optional plot
        try:
            import pandapower.plotting as plot
            plot.simple_plot(net, plot_line_switches=False)
        except:
            print("Plotting failed (non-critical).")

    return data



# net = pn.case33bw()
# data = extract_network_data(net, verbose=True)
# # print(data)