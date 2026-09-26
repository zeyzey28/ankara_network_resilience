import networkx as nx
import osmnx as ox


place_name = "Çankaya, Ankara, Turkey"


def route_distance_km(graph, route):
    """Calculate route distance from edge lengths and return kilometers."""
    distance_meters = 0

    for u, v in zip(route[:-1], route[1:]):
        edge_data = graph.get_edge_data(u, v)
        shortest_edge = min(edge_data.values(), key=lambda data: data["length"])
        distance_meters += shortest_edge["length"]

    return distance_meters / 1000


def route_edges_with_keys(graph, route):
    """Return the shortest available edge key for each route step."""
    edges = []

    for u, v in zip(route[:-1], route[1:]):
        edge_data = graph.get_edge_data(u, v)
        key = min(edge_data, key=lambda edge_key: edge_data[edge_key]["length"])
        edges.append((u, v, key))

    return edges


graph = ox.graph_from_place(place_name, network_type="drive")

# Use the largest strongly connected component so the selected nodes have a
# valid driving route in both directions.
largest_component = max(nx.strongly_connected_components(graph), key=len)
graph = graph.subgraph(largest_component).copy()

# Pick two distant nodes from the network's west and east sides.
origin = min(graph.nodes, key=lambda node: graph.nodes[node]["x"])
destination = max(graph.nodes, key=lambda node: graph.nodes[node]["x"])

original_route = nx.shortest_path(
    graph,
    origin,
    destination,
    weight="length",
)
original_distance_km = route_distance_km(graph, original_route)

# Use edge betweenness centrality to choose the most important edge on the route.
undirected_graph = graph.to_undirected()
edge_centrality = nx.edge_betweenness_centrality(
    undirected_graph,
    k=200,
    weight="length",
    seed=42,
)

route_edges = route_edges_with_keys(graph, original_route)
important_edge = max(
    route_edges,
    key=lambda edge: edge_centrality.get(edge, edge_centrality.get((edge[1], edge[0], edge[2]), 0)),
)

modified_graph = graph.copy()
closed_u, closed_v, closed_key = important_edge
print(f"Closed segment: {closed_u} -> {closed_v}")

if modified_graph.has_edge(closed_u, closed_v):
    modified_graph.remove_edges_from(
        (closed_u, closed_v, key)
        for key in list(modified_graph[closed_u][closed_v])
    )

if modified_graph.has_edge(closed_v, closed_u):
    modified_graph.remove_edges_from(
        (closed_v, closed_u, key)
        for key in list(modified_graph[closed_v][closed_u])
    )

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

    print(f"Original route distance: {original_distance_km:.2f} km")
    print(f"Alternative route distance: {alternative_distance_km:.2f} km")
    print(f"Distance increase: {distance_increase_km:.2f} km")
    print(f"Percentage increase: {percentage_increase:.2f}%")
except nx.NetworkXNoPath:
    print("Destination is unreachable after removing the important edge.")
