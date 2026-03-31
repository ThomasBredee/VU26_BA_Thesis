
import pandas as pd
import pandapower.networks as pn
import pandapower.plotting as plot

# -----------------------------
# 1. Load MATPOWER case
# -----------------------------
mpc_file = "data/case33bw.m"  # make sure this file is in your folder

net = pn.case33bw()

# -----------------------------
# 2. Extract BUS data
# -----------------------------
buses = net.bus.copy()

# Add load info (Pd, Qd)
loads = net.load.copy()

# Merge load onto buses
buses["p_mw"] = 0.0
buses["q_mvar"] = 0.0

for _, row in loads.iterrows():
    bus_id = row["bus"]
    buses.loc[bus_id, "p_mw"] += row["p_mw"]
    buses.loc[bus_id, "q_mvar"] += row["q_mvar"]

# Clean bus dataframe
buses_df = buses.reset_index().rename(columns={
    "index": "bus_id",
    "vn_kv": "voltage_kv"
})

# -----------------------------
# 3. Extract LINE data
# -----------------------------
lines = net.line.copy()

lines_df = lines.reset_index().rename(columns={
    "index": "line_id",
    "from_bus": "from_bus",
    "to_bus": "to_bus",
    "length_km": "length_km",
    "r_ohm_per_km": "r_ohm_per_km",
    "x_ohm_per_km": "x_ohm_per_km",
    "max_i_ka": "max_current_ka"
})

# -----------------------------
# 4. Compute LINE CAPACITY (MW)
# -----------------------------
# S = sqrt(3) * V * I
import numpy as np

lines_df["capacity_mva"] = (
    np.sqrt(3)
    * lines_df["max_current_ka"]
    * buses_df.loc[lines_df["from_bus"], "voltage_kv"].values
)

# -----------------------------
# 5. Substation (slack bus)
# -----------------------------
slack_bus = net.ext_grid.bus.iloc[0]

substation = {
    "bus_id": slack_bus,
    "voltage_kv": buses_df.loc[slack_bus, "voltage_kv"],
    "approx_capacity_mva": net.sn_mva  # system base power
}

# -----------------------------
# 6. Print results
# -----------------------------
print("\n=== BUSES ===")
print(buses_df.head())
print(buses_df.columns)

print("\n=== LINES ===")
print(lines_df.head())
print(lines_df.columns)

print("\n=== SUBSTATION ===")
print(substation)


## A random setup of the network
# import pandapower.networks as pn
# import pandapower.plotting as plot
# import pandapower.topology as top
# import networkx as nx
# import matplotlib.pyplot as plt

# # Load network
# net = pn.case33bw()

# # Convert to NetworkX graph
# G = top.create_nxgraph(net)

# # Generate layout (tree-like)
# pos = nx.spring_layout(G, seed=62)

# # Draw
# slack_bus = net.ext_grid.bus.iloc[0]

# node_colors = [
#     "red" if node == slack_bus else "lightblue"
#     for node in G.nodes()
# ]

# plt.figure(figsize=(10, 8))

# nx.draw(
#     G,
#     pos,
#     with_labels=True,
#     node_color=node_colors,
#     node_size=300,
#     font_size=8
# )

# plt.title("IEEE 33-Bus Network (Red = Substation)")
# plt.show()


# ## A tree like setup of the network
# import pandapower.networks as pn
# import pandapower.topology as top
# import networkx as nx
# import matplotlib.pyplot as plt

# # Load network
# net = pn.case33bw()

# # Create graph
# G = top.create_nxgraph(net)

# # Get slack (root node)
# root = net.ext_grid.bus.iloc[0]

# # Build BFS tree from root
# tree = nx.bfs_tree(G, source=root)

# # Custom hierarchy layout
# def hierarchy_pos(G, root, width=1.0, vert_gap=0.2, vert_loc=0, xcenter=0.5):
#     pos = {root: (xcenter, vert_loc)}
#     neighbors = list(G.neighbors(root))
    
#     if len(neighbors) != 0:
#         dx = width / len(neighbors)
#         nextx = xcenter - width/2 - dx/2
        
#         for neighbor in neighbors:
#             nextx += dx
#             pos.update(hierarchy_pos(
#                 G, neighbor,
#                 width=dx,
#                 vert_gap=vert_gap,
#                 vert_loc=vert_loc - vert_gap,
#                 xcenter=nextx
#             ))
#     return pos

# # Generate positions
# pos = hierarchy_pos(tree, root)

# # Plot
# plt.figure(figsize=(12, 8))

# nx.draw(
#     G,
#     pos,
#     with_labels=True,
#     node_size=300,
#     font_size=8
# )

# plt.title("IEEE 33-Bus Radial Network (Tree Layout)")
# plt.show()

import pandapower.plotting as plot

plot.simple_plot(net, plot_line_switches=False)