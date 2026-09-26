from pathlib import Path

import networkx as nx
import osmnx as ox


place_name = "Çankaya, Ankara, Turkey"
output_dir = Path("outputs")
output_dir.mkdir(exist_ok=True)

graph = ox.graph_from_place(place_name, network_type="drive")
undirected_graph = graph.to_undirected()

centrality = nx.betweenness_centrality(
    undirected_graph,
    k=200,
    seed=42,
)

top_nodes = sorted(
    centrality,
    key=centrality.get,
    reverse=True,
)[:10]

node_colors = [
    "red" if node in top_nodes else "black"
    for node in graph.nodes
]
node_sizes = [
    35 if node in top_nodes else 0
    for node in graph.nodes
]

fig, ax = ox.plot_graph(
    graph,
    node_color=node_colors,
    node_size=node_sizes,
    edge_color="gray",
    edge_linewidth=0.5,
    bgcolor="white",
    show=False,
    close=False,
)

fig.savefig(output_dir / "critical_nodes.png", dpi=300, bbox_inches="tight")
