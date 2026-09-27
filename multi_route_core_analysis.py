import csv
from pathlib import Path

import networkx as nx
import osmnx as ox


center_place = "Kızılay, Çankaya, Ankara, Turkey"
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


def nearest_node_to_fraction(graph, x_fraction, y_fraction):
    """Find the graph node closest to a relative position in the study area."""
    x_values = [data["x"] for _, data in graph.nodes(data=True)]
    y_values = [data["y"] for _, data in graph.nodes(data=True)]

    min_x, max_x = min(x_values), max(x_values)
    min_y, max_y = min(y_values), max(y_values)

    target_x = min_x + (max_x - min_x) * x_fraction
    target_y = min_y + (max_y - min_y) * y_fraction

    return min(
        graph.nodes,
        key=lambda node: (
            (graph.nodes[node]["x"] - target_x) ** 2
            + (graph.nodes[node]["y"] - target_y) ** 2
        ),
    )


center_point = ox.geocode(center_place)
graph = ox.graph_from_point(center_point, dist=12000, network_type="drive")

# Keep only the largest strongly connected component.
largest_component = max(nx.strongly_connected_components(graph), key=len)
graph = graph.subgraph(largest_component).copy()

# Candidate routes use fixed geographic anchor points across the study area.
candidate_anchor_pairs = [
    ((0.05, 0.50), (0.95, 0.50)),
    ((0.10, 0.85), (0.90, 0.15)),
    ((0.10, 0.15), (0.90, 0.85)),
    ((0.50, 0.95), (0.50, 0.05)),
    ((0.20, 0.75), (0.85, 0.40)),
    ((0.20, 0.25), (0.85, 0.60)),
    ((0.35, 0.90), (0.70, 0.10)),
    ((0.35, 0.10), (0.70, 0.90)),
    ((0.05, 0.70), (0.75, 0.20)),
    ((0.05, 0.30), (0.75, 0.80)),
    ((0.25, 0.50), (0.95, 0.75)),
    ((0.25, 0.50), (0.95, 0.25)),
]

routes = []
minimum_route_distance_km = 5

for origin_anchor, destination_anchor in candidate_anchor_pairs:
    origin = nearest_node_to_fraction(graph, *origin_anchor)
    destination = nearest_node_to_fraction(graph, *destination_anchor)

    if origin == destination:
        continue

    route = nx.shortest_path(graph, origin, destination, weight="length")
    distance_km = route_distance_km(graph, route)

    if distance_km < minimum_route_distance_km:
        continue

    routes.append(
        {
            "route_id": len(routes) + 1,
            "origin": origin,
            "destination": destination,
            "route": route,
            "route_distance_km": distance_km,
        }
    )

    if len(routes) == 10:
        break

undirected_graph = make_simple_undirected_graph(graph)
edge_centrality = nx.edge_betweenness_centrality(
    undirected_graph,
    k=200,
    weight="length",
    seed=42,
)

results = []
seen_segments = set()

for route_info in routes:
    route = route_info["route"]
    route_segments = list(zip(route[:-1], route[1:]))

    top_segments = sorted(
        route_segments,
        key=lambda edge: edge_centrality_value(edge_centrality, edge[0], edge[1]),
        reverse=True,
    )[:3]

    for segment_u, segment_v in top_segments:
        segment_key = frozenset((segment_u, segment_v))

        if segment_key in seen_segments:
            continue

        seen_segments.add(segment_key)

        results.append(
            {
                "route_id": route_info["route_id"],
                "origin": route_info["origin"],
                "destination": route_info["destination"],
                "route_distance_km": route_info["route_distance_km"],
                "segment_u": segment_u,
                "segment_v": segment_v,
                "centrality": edge_centrality_value(edge_centrality, segment_u, segment_v),
            }
        )

csv_path = output_dir / "core_multi_route_segments.csv"
fieldnames = [
    "route_id",
    "origin",
    "destination",
    "route_distance_km",
    "segment_u",
    "segment_v",
    "centrality",
]

with csv_path.open("w", newline="") as csv_file:
    writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(results)

route_distances = [route_info["route_distance_km"] for route_info in routes]

print(f"Number of tested routes: {len(routes)}")
print(f"Number of unique critical segments identified: {len(results)}")
print(f"Average route distance: {sum(route_distances) / len(route_distances):.2f} km")
print(f"Shortest route distance: {min(route_distances):.2f} km")
print(f"Longest route distance: {max(route_distances):.2f} km")
