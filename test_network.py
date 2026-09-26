from pathlib import Path

import osmnx as ox


place_name = "Çankaya, Ankara, Turkey"
output_dir = Path("outputs")
output_dir.mkdir(exist_ok=True)

graph = ox.graph_from_place(place_name, network_type="drive")

print(f"Number of nodes: {len(graph.nodes)}")
print(f"Number of edges: {len(graph.edges)}")

fig, ax = ox.plot_graph(graph, show=False, close=False)
fig.savefig(output_dir / "cankaya_network.png", dpi=300, bbox_inches="tight")
