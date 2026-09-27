from pathlib import Path

import networkx as nx
import osmnx as ox


center_place = "Kızılay, Çankaya, Ankara, Turkey"
output_dir = Path(__file__).resolve().parent / "outputs"
output_dir.mkdir(exist_ok=True)

# Use Kızılay as the approximate center of Ankara's compact urban core.
center_point = ox.geocode(center_place)
graph = ox.graph_from_point(center_point, dist=12000, network_type="drive")

# Keep only the largest strongly connected component.
largest_component = max(nx.strongly_connected_components(graph), key=len)
graph = graph.subgraph(largest_component).copy()

print(f"Number of nodes: {len(graph.nodes)}")
print(f"Number of edges: {len(graph.edges)}")

fig, ax = ox.plot_graph(
    graph,
    node_size=0,
    edge_color="lightgray",
    edge_linewidth=0.5,
    bgcolor="white",
    show=False,
    close=False,
)

fig.savefig(output_dir / "ankara_core_network.png", dpi=300, bbox_inches="tight")
