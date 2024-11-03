import networkx
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Patch
from pathlib import Path


# Switch to Agg backend to avoid GUI dependencies (e.g. Tkinter)
plt.switch_backend('agg')


def draw_graph(graph: networkx.DiGraph, save_path: Path):
    """Draws a graph with nodes as rounded rectangles and labels inside them,
    using professional colors suitable for academic publications, and adds a legend describing the colors.

    Args:
        graph (networkx.DiGraph): The networkx graph
        save_path (Path): The path to save the visualization
    """
    pos = networkx.spring_layout(graph, k=2, iterations=20)

    # Define a professional, colorblind-friendly palette
    color_map = {}
    type_color = {}  # Map from node type to color
    for node in graph.nodes(data=True):
        node_type = node[0].graphql_type
        if node_type == 'Mutation':
            color = '#1f77b4'  # Blue
        elif node_type == 'Query':
            color = '#2ca02c'  # Green
        else:
            color = '#7f7f7f'  # Gray
            node_type = 'Object'  # To group all other types under 'Object'
        color_map[node[0]] = color
        type_color[node_type] = color  # Map node type to color

    fig, ax = plt.subplots(figsize=(12, 8))

    # Detect bidirectional edges and draw them accordingly
    drawn_edges = set()
    for edge in graph.edges():
        u, v = edge
        if (v, u) in graph.edges() and (v, u) not in drawn_edges:
            # Draw a single bidirectional edge
            x1, y1 = pos[u]
            x2, y2 = pos[v]
            ax.annotate("",
                        xy=(x2, y2), xycoords='data',
                        xytext=(x1, y1), textcoords='data',
                        arrowprops=dict(arrowstyle="<->", color="black", shrinkA=15, shrinkB=15,
                                        connectionstyle="arc3,rad=0.1", linewidth=1))
            drawn_edges.add((u, v))
            drawn_edges.add((v, u))
        elif (u, v) not in drawn_edges:
            # Draw a unidirectional edge
            x1, y1 = pos[u]
            x2, y2 = pos[v]
            ax.annotate("",
                        xy=(x2, y2), xycoords='data',
                        xytext=(x1, y1), textcoords='data',
                        arrowprops=dict(arrowstyle="->", color="black", shrinkA=15, shrinkB=15,
                                        connectionstyle="arc3,rad=0.1", linewidth=1))
            drawn_edges.add((u, v))

    # Calculate all x and y positions
    all_x = [pos[node][0] for node in graph.nodes()]
    all_y = [pos[node][1] for node in graph.nodes()]

    # Calculate margins
    x_margin = (max(all_x) - min(all_x)) * 0.1  # 10% margin
    y_margin = (max(all_y) - min(all_y)) * 0.1  # 10% margin

    # Set axis limits with margins
    ax.set_xlim(min(all_x) - x_margin, max(all_x) + x_margin)
    ax.set_ylim(min(all_y) - y_margin, max(all_y) + y_margin)

    plt.axis('off')
    plt.tight_layout()

    # Draw nodes as rounded rectangles with variable width
    # Get renderer to compute text size
    fig.canvas.draw()  # Need to draw the figure to get the renderer
    renderer = fig.canvas.renderer # type: ignore

    for node in graph.nodes():
        x, y = pos[node]
        text = node.name

        # Create a dummy text object to get text size
        text_obj = ax.text(0, 0, text, fontsize=8)
        bbox = text_obj.get_window_extent(renderer=renderer)
        # Remove the dummy text object
        text_obj.remove()

        # Convert bbox width from pixels to data units
        inv = ax.transData.inverted()
        bbox_data = inv.transform([[0, 0], [bbox.width, bbox.height]])
        width_data = bbox_data[1][0] - bbox_data[0][0]
        height_data = bbox_data[1][1] - bbox_data[0][1]

        # Add some padding
        width = width_data + 0.02 * (ax.get_xlim()[1] - ax.get_xlim()[0])
        height = height_data + 0.02 * (ax.get_ylim()[1] - ax.get_ylim()[0])

        # Center the box around (x, y)
        box = FancyBboxPatch((x - width / 2, y - height / 2),
                             width,
                             height,
                             boxstyle="round,pad=0.02",
                             fc=color_map[node],
                             ec="black",
                             linewidth=1)
        ax.add_patch(box)
        # Add label inside the box
        ax.text(x, y, text, horizontalalignment='center', verticalalignment='center', fontsize=8)

    # Create custom legend handles
    legend_handles = []
    for node_type, color in type_color.items():
        patch = Patch(facecolor=color, edgecolor='black', label=node_type)
        legend_handles.append(patch)

    # Add the legend to the plot
    ax.legend(handles=legend_handles, loc='upper right', title='Node Types', fontsize=8, title_fontsize=9)

    # Save the figure
    plt.savefig(save_path, format="png", dpi=1000, bbox_inches='tight')
    plt.savefig(save_path.with_suffix('.pdf'), format='pdf', bbox_inches='tight')
    plt.close()
