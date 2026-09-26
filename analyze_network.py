import networkx as nx
import osmnx as ox


place_name = "Çankaya, Ankara, Turkey"

graph = ox.graph_from_place(place_name, network_type="drive")
undirected_graph = graph.to_undirected()

centrality = nx.betweenness_centrality(
    undirected_graph,
    k=200,
    seed=42,
)

top_nodes = sorted(
    centrality.items(),
    key=lambda item: item[1],
    reverse=True,
)[:10]

print("Top 10 nodes by betweenness centrality:")
for node, value in top_nodes:
    print(f"{node}: {value}")
