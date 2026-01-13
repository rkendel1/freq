"""
Visualization utilities for knowledge graphs.
Simplified version adapted from https://github.com/rkendel1/graph
"""

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def visualize_knowledge_graph(
    triples: list[dict[str, Any]],
    output_path: str | Path,
    title: str = "Knowledge Graph",
) -> dict[str, Any]:
    """
    Create an interactive HTML visualization of a knowledge graph.
    
    Args:
        triples: List of SPO triples (dicts with subject, predicate, object)
        output_path: Path to save the HTML visualization
        title: Title for the visualization
        
    Returns:
        dict: Statistics about the generated graph
        
    Raises:
        ImportError: If required libraries are not installed
    """
    try:
        import networkx as nx
        from pyvis.network import Network
    except ImportError:
        raise ImportError(
            "networkx and pyvis are required for knowledge graph visualization. "
            "Install with: pip install networkx pyvis python-louvain"
        )
    
    # Create NetworkX graph
    G = nx.DiGraph()
    
    # Add edges from triples
    for triple in triples:
        subject = triple.get("subject", "")
        predicate = triple.get("predicate", "")
        obj = triple.get("object", "")
        
        if subject and obj and predicate:
            G.add_edge(subject, obj, label=predicate)
    
    if len(G.nodes) == 0:
        logger.warning("No valid triples to visualize")
        return {"nodes": 0, "edges": 0, "communities": 0}
    
    # Detect communities using Louvain method
    try:
        import community as community_louvain
        
        # Convert to undirected for community detection
        G_undirected = G.to_undirected()
        communities = community_louvain.best_partition(G_undirected)
        num_communities = len(set(communities.values()))
    except ImportError:
        logger.warning("python-louvain not installed, skipping community detection")
        communities = {}
        num_communities = 1
    
    # Create PyVis network
    net = Network(
        height="750px",
        width="100%",
        bgcolor="#ffffff",
        font_color="#000000",
        directed=True,
    )
    
    # Configure physics
    net.set_options("""
    {
        "physics": {
            "enabled": true,
            "barnesHut": {
                "gravitationalConstant": -30000,
                "centralGravity": 0.3,
                "springLength": 200,
                "springConstant": 0.04,
                "damping": 0.09
            }
        },
        "nodes": {
            "font": {"size": 14}
        },
        "edges": {
            "font": {"size": 12},
            "arrows": {"to": {"enabled": true}}
        }
    }
    """)
    
    # Color palette for communities
    colors = [
        "#e74c3c", "#3498db", "#2ecc71", "#f39c12", "#9b59b6",
        "#1abc9c", "#34495e", "#e67e22", "#95a5a6", "#d35400"
    ]
    
    # Add nodes with community colors
    for node in G.nodes():
        community = communities.get(node, 0)
        color = colors[community % len(colors)]
        
        # Calculate node size based on degree
        degree = G.degree(node)
        size = 20 + (degree * 2)
        
        net.add_node(
            node,
            label=node,
            color=color,
            size=size,
            title=f"{node} (degree: {degree})",
        )
    
    # Add edges
    for edge in G.edges(data=True):
        source, target, data = edge
        label = data.get("label", "")
        net.add_edge(source, target, label=label, title=label)
    
    # Save to file
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Generate HTML
    net.save_graph(str(output_path))
    
    # Add custom title to HTML
    if title != "Knowledge Graph":
        try:
            with open(output_path, 'r') as f:
                html = f.read()
            html = html.replace("<title>", f"<title>{title} - ")
            with open(output_path, 'w') as f:
                f.write(html)
        except Exception as e:
            logger.warning(f"Could not update title in HTML: {e}")
    
    logger.info(f"Knowledge graph visualization saved to {output_path}")
    
    stats = {
        "nodes": len(G.nodes),
        "edges": len(G.edges),
        "communities": num_communities,
    }
    
    return stats


def save_triples_json(
    triples: list[dict[str, Any]],
    output_path: str | Path,
) -> None:
    """
    Save triples to JSON file.
    
    Args:
        triples: List of SPO triples
        output_path: Path to save the JSON file
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(triples, f, indent=2)
    
    logger.info(f"Triples saved to {output_path}")
