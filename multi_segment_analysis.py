import csv
from pathlib import Path

import networkx as nx
import osmnx as ox


place_name = "Çankaya, Ankara, Turkey"
output_dir = Path(__file__).resolve().parent / "outputs"
output_dir.mkdir(exist_ok=True)


def route_distance_km(graph, route):
    """Calculate a route distance from edge lengths and return kilometers."""
    distance_meters = 0

    for u, v in zip(route[:-1], route[1:]):
        edge_data = graph.get_edge_data(u, v)
        shortest_edge = min(edge_data.values(), key=lambda data: data["length"])
        distance_meters += shortest_edge["length"]

    return distance_meters / 1000


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


def close_segment(graph, u, v):
    """Remove all edges in both directions between two nodes."""
    if graph.has_edge(u, v):
        graph.remove_edges_from((u, v, key) for key in list(graph[u][v]))

    if graph.has_edge(v, u):
        graph.remove_edges_from((v, u, key) for key in list(graph[v][u]))


graph = ox.graph_from_place(place_name, network_type="drive")

# Keep only the largest strongly connected component so the route is valid.
largest_component = max(nx.strongly_connected_components(graph), key=len)
graph = graph.subgraph(largest_component).copy()

# Pick distant west/east nodes from the network.
origin = min(graph.nodes, key=lambda node: graph.nodes[node]["x"])
destination = max(graph.nodes, key=lambda node: graph.nodes[node]["x"])

original_route = nx.shortest_path(
    graph,
    origin,
    destination,
    weight="length",
)
original_distance_km = route_distance_km(graph, original_route)

# Calculate approximate edge betweenness centrality on an undirected graph.
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

results = []

for rank, (closed_u, closed_v) in enumerate(top_segments, start=1):
    modified_graph = graph.copy()
    close_segment(modified_graph, closed_u, closed_v)

    centrality = edge_centrality_value(edge_centrality, closed_u, closed_v)

    try:
        alternative_route = nx.shortest_path(
            modified_graph,
            origin,
            destination,
            weight="length",
        )
        alternative_distance_km = route_distance_km(modified_graph, alternative_route)
        distance_increase_km = alternative_distance_km - original_distance_km
        percentage_increase = (distance_increase_km / original_distance_km) * 100
        status = "reachable"
    except nx.NetworkXNoPath:
        alternative_distance_km = None
        distance_increase_km = None
        percentage_increase = None
        status = "unreachable"

    results.append(
        {
            "rank": rank,
            "closed_u": closed_u,
            "closed_v": closed_v,
            "centrality": centrality,
            "original_distance_km": original_distance_km,
            "alternative_distance_km": alternative_distance_km,
            "distance_increase_km": distance_increase_km,
            "percentage_increase": percentage_increase,
            "status": status,
        }
    )

fieldnames = [
    "rank",
    "closed_u",
    "closed_v",
    "centrality",
    "original_distance_km",
    "alternative_distance_km",
    "distance_increase_km",
    "percentage_increase",
    "status",
]

print(
    f"{'Rank':<5} {'Closed segment':<35} {'Centrality':<12} "
    f"{'Original km':<12} {'Alternative km':<15} {'Increase km':<12} "
    f"{'Increase %':<12} {'Status':<12}"
)

for result in results:
    alternative = result["alternative_distance_km"]
    increase = result["distance_increase_km"]
    percentage = result["percentage_increase"]

    print(
        f"{result['rank']:<5} "
        f"{str(result['closed_u']) + ' -> ' + str(result['closed_v']):<35} "
        f"{result['centrality']:<12.6f} "
        f"{result['original_distance_km']:<12.2f} "
        f"{alternative if alternative is None else f'{alternative:.2f}':<15} "
        f"{increase if increase is None else f'{increase:.2f}':<12} "
        f"{percentage if percentage is None else f'{percentage:.2f}':<12} "
        f"{result['status']:<12}"
    )

csv_path = output_dir / "segment_resilience_results.csv"

with csv_path.open("w", newline="") as csv_file:
    writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(results)
