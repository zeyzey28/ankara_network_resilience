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


def undirected_segment_key(u, v):
    """Treat opposite directions as the same road segment."""
    return tuple(sorted((u, v)))


center_point = ox.geocode(center_place)
graph = ox.graph_from_point(center_point, dist=12000, network_type="drive")

# Keep only the largest strongly connected component.
largest_component = max(nx.strongly_connected_components(graph), key=len)
graph = graph.subgraph(largest_component).copy()

# Reuse the same fixed geographic route anchors from multi_route_core_analysis.py.
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

selected_segments = []

for route_info in routes:
    route = route_info["route"]
    route_segments = list(zip(route[:-1], route[1:]))

    top_segments = sorted(
        route_segments,
        key=lambda edge: edge_centrality_value(edge_centrality, edge[0], edge[1]),
        reverse=True,
    )[:3]

    # Keep every selected occurrence before aggregating by segment.
    for segment_u, segment_v in top_segments:
        selected_segments.append(
            {
                "route_id": route_info["route_id"],
                "route_distance_km": route_info["route_distance_km"],
                "segment_u": segment_u,
                "segment_v": segment_v,
                "centrality": edge_centrality_value(edge_centrality, segment_u, segment_v),
            }
        )

segment_summary = {}

for segment in selected_segments:
    key = undirected_segment_key(segment["segment_u"], segment["segment_v"])

    if key not in segment_summary:
        segment_summary[key] = {
            "segment_u": key[0],
            "segment_v": key[1],
            "centrality": segment["centrality"],
            "route_ids": [],
            "route_distances": [],
        }

    segment_summary[key]["route_ids"].append(segment["route_id"])
    segment_summary[key]["route_distances"].append(segment["route_distance_km"])

results = []

for summary in segment_summary.values():
    route_ids = sorted(summary["route_ids"])
    route_distances = summary["route_distances"]

    results.append(
        {
            "segment_u": summary["segment_u"],
            "segment_v": summary["segment_v"],
            "centrality": summary["centrality"],
            "route_frequency": len(route_ids),
            "route_ids": ",".join(str(route_id) for route_id in route_ids),
            "average_route_distance_km": sum(route_distances) / len(route_distances),
        }
    )

results.sort(
    key=lambda row: (row["route_frequency"], row["centrality"]),
    reverse=True,
)

csv_path = output_dir / "core_segment_frequency.csv"
fieldnames = [
    "segment_u",
    "segment_v",
    "centrality",
    "route_frequency",
    "route_ids",
    "average_route_distance_km",
]

with csv_path.open("w", newline="") as csv_file:
    writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(results)

route_frequencies = [result["route_frequency"] for result in results]

print(f"Total selected segment occurrences: {len(selected_segments)}")
print(f"Number of unique critical segments: {len(results)}")
print(f"Maximum route frequency: {max(route_frequencies)}")
print(
    "Number of segments appearing in more than one route: "
    f"{sum(frequency > 1 for frequency in route_frequencies)}"
)
