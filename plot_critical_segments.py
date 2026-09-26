from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx
import osmnx as ox


place_name = "Çankaya, Ankara, Turkey"
output_dir = Path(__file__).resolve().parent / "outputs"
output_dir.mkdir(exist_ok=True)


def make_simple_undirected_graph(graph):
    """Create a simple undirected graph using the shortest edge between nodes."""
    simple_graph = nx.Graph()

    for u, v, data in graph.edges(data=True):
        length = data["length"]

        if simple_graph.has_edge(u, v):
            if length < simple_graph[u][v]["length"]:
                simple_graph[u][v]["length"] = length
        else:
            simple_graph.add_edge(u, v, length=length)

    return simple_graph


def edge_centrality_value(edge_centrality, u, v):
    """Read centrality for an undirected edge regardless of node order."""
    return edge_centrality.get((u, v), edge_centrality.get((v, u), 0))


graph = ox.graph_from_place(place_name, network_type="drive")

# Keep only the largest strongly connected component.
largest_component = max(nx.strongly_connected_components(graph), key=len)
graph = graph.subgraph(largest_component).copy()

# Use the same west/east origin and destination logic as before.
origin = min(graph.nodes, key=lambda node: graph.nodes[node]["x"])
destination = max(graph.nodes, key=lambda node: graph.nodes[node]["x"])

original_route = nx.shortest_path(
    graph,
    origin,
    destination,
    weight="length",
)

undirected_graph = make_simple_undirected_graph(graph)
edge_centrality = nx.edge_betweenness_centrality(
    undirected_graph,
    k=200,
    weight="length",
    seed=42,
)

route_segments = list(zip(original_route[:-1], original_route[1:]))
top_segments = sorted(
    route_segments,
    key=lambda edge: edge_centrality_value(edge_centrality, edge[0], edge[1]),
    reverse=True,
)[:5]

fig, ax = ox.plot_graph(
    graph,
    node_size=0,
    edge_color="lightgray",
    edge_linewidth=0.5,
    bgcolor="white",
    show=False,
    close=False,
)

for u, v in top_segments:
    x_values = [graph.nodes[u]["x"], graph.nodes[v]["x"]]
    y_values = [graph.nodes[u]["y"], graph.nodes[v]["y"]]
    ax.plot(x_values, y_values, color="red", linewidth=3)

fig.savefig(output_dir / "critical_segments_map.png", dpi=300, bbox_inches="tight")
plt.close(fig)
