from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx
import osmnx as ox
import pandas as pd


center_place = "Kızılay, Çankaya, Ankara, Turkey"
project_dir = Path(__file__).resolve().parent
output_dir = project_dir / "outputs"

csv_path = output_dir / "core_segment_frequency.csv"
map_path = output_dir / "core_critical_segments_map.png"


def linewidth_for_frequency(route_frequency):
    """Choose overlay line width from route frequency."""
    if route_frequency == 1:
        return 0.8
    if route_frequency == 2:
        return 1.5
    if route_frequency == 3:
        return 2.3
    return 3.2


center_point = ox.geocode(center_place)
graph = ox.graph_from_point(center_point, dist=12000, network_type="drive")

# Keep only the largest strongly connected component.
largest_component = max(nx.strongly_connected_components(graph), key=len)
graph = graph.subgraph(largest_component).copy()

segments = pd.read_csv(csv_path)

fig, ax = ox.plot_graph(
    graph,
    node_size=0,
    edge_color="lightgray",
    edge_linewidth=0.4,
    bgcolor="white",
    show=False,
    close=False,
)

for _, segment in segments.iterrows():
    segment_u = int(segment["segment_u"])
    segment_v = int(segment["segment_v"])
    route_frequency = segment["route_frequency"]

    if segment_u not in graph.nodes or segment_v not in graph.nodes:
        continue

    edge_data = graph.get_edge_data(segment_u, segment_v)

    if edge_data is None:
        edge_data = graph.get_edge_data(segment_v, segment_u)

    if edge_data is None:
        continue

    shortest_edge = min(edge_data.values(), key=lambda data: data["length"])
    linewidth = linewidth_for_frequency(route_frequency)

    if "geometry" in shortest_edge:
        x_values, y_values = shortest_edge["geometry"].xy
    else:
        x_values = [graph.nodes[segment_u]["x"], graph.nodes[segment_v]["x"]]
        y_values = [graph.nodes[segment_u]["y"], graph.nodes[segment_v]["y"]]

    ax.plot(
        x_values,
        y_values,
        color="red",
        linewidth=linewidth,
        solid_capstyle="round",
    )

fig.savefig(map_path, dpi=300, bbox_inches="tight")
plt.close(fig)
