import networkx
import matplotlib.pyplot as plt
from pathlib import Path


def draw_graph(graph: networkx.DiGraph, save_path: Path):
    """Draws a graph

    Args:
        graph (networkx.DiGraph): The networkx graph
        save_path (Path): The path to save the visualization
    """
    pos = networkx.random_layout(graph)
    networkx.draw(graph, pos, with_labels=False, node_size=100, node_color="skyblue", font_size=8, font_color="black", font_weight="bold", edge_color="gray", width=2)
    custom_labels = get_custom_labels(graph)
    networkx.draw_networkx_labels(graph, pos, labels=custom_labels, font_size=8, verticalalignment="bottom", horizontalalignment="right")
    plt.savefig(save_path, format="png", dpi=1200)


def get_custom_labels(graph):
    labels = {}
    for node in graph.nodes():
        labels[node] = f"{node.name}\n({node.graphql_type})"
    return labels
