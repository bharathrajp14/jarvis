# memory/knowledge_graph.py — Relational Knowledge Graph & World Model
"""
KnowledgeGraph provides a graph-based world model connecting workspace entities,
projects, files, apps, windows, goals, repositories, and APIs with directed relational edges.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

try:
    import networkx as nx
    _HAS_NETWORKX = True
except ImportError:
    _HAS_NETWORKX = False

logger = logging.getLogger("JARVIS.KnowledgeGraph")


class KnowledgeGraph:
    """
    Relational World Model for BR JARVIS tracking system entities and relationships.
    """

    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = Path(storage_path or os.path.join("workspace", "knowledge_graph.json"))
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        if _HAS_NETWORKX:
            self.graph = nx.DiGraph()
        else:
            self._nodes: Dict[str, Dict[str, Any]] = {}
            self._edges: Dict[str, List[Dict[str, Any]]] = {}

        self.load()

    def add_entity(self, entity_id: str, entity_type: str, properties: Optional[Dict[str, Any]] = None) -> None:
        """Add or update an entity node in the Knowledge Graph."""
        props = properties or {}
        props["entity_type"] = entity_type
        
        if _HAS_NETWORKX:
            self.graph.add_node(entity_id, **props)
        else:
            self._nodes[entity_id] = props
            if entity_id not in self._edges:
                self._edges[entity_id] = []

        logger.debug(f"🕸️ KnowledgeGraph: Added entity node [{entity_type}] {entity_id}")
        self.save()

    def add_relationship(
        self,
        source_id: str,
        target_id: str,
        relation_type: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Add a directed relational edge between two entities."""
        props = properties or {}
        props["relation_type"] = relation_type

        # Ensure nodes exist
        if not self.has_entity(source_id):
            self.add_entity(source_id, "unknown")
        if not self.has_entity(target_id):
            self.add_entity(target_id, "unknown")

        if _HAS_NETWORKX:
            self.graph.add_edge(source_id, target_id, **props)
        else:
            edge_entry = {"target": target_id, **props}
            if edge_entry not in self._edges[source_id]:
                self._edges[source_id].append(edge_entry)

        logger.debug(f"🕸️ KnowledgeGraph: Connected {source_id} -[{relation_type}]-> {target_id}")
        self.save()

    def has_entity(self, entity_id: str) -> bool:
        """Check if an entity node exists."""
        if _HAS_NETWORKX:
            return self.graph.has_node(entity_id)
        return entity_id in self._nodes

    def get_entity(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve entity properties."""
        if not self.has_entity(entity_id):
            return None
        if _HAS_NETWORKX:
            return dict(self.graph.nodes[entity_id])
        return dict(self._nodes[entity_id])

    def get_related_entities(self, entity_id: str) -> List[Dict[str, Any]]:
        """Get all entities connected to the specified entity."""
        if not self.has_entity(entity_id):
            return []

        results = []
        if _HAS_NETWORKX:
            for neighbor in self.graph.successors(entity_id):
                edge_data = self.graph.get_edge_data(entity_id, neighbor)
                node_data = self.graph.nodes[neighbor]
                results.append({"entity_id": neighbor, "relation": edge_data.get("relation_type"), "properties": node_data})
        else:
            for edge in self._edges.get(entity_id, []):
                target = edge["target"]
                node_data = self._nodes.get(target, {})
                results.append({"entity_id": target, "relation": edge.get("relation_type"), "properties": node_data})

        return results

    def save(self) -> None:
        """Persist graph structure to JSON disk storage."""
        try:
            if _HAS_NETWORKX:
                data = nx.node_link_data(self.graph)
            else:
                data = {"nodes": self._nodes, "edges": self._edges}

            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save KnowledgeGraph: {e}")

    def load(self) -> None:
        """Load graph structure from disk if available."""
        if not self.storage_path.exists():
            return
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if _HAS_NETWORKX and "nodes" in data and "links" in data:
                self.graph = nx.node_link_graph(data)
            elif not _HAS_NETWORKX and "nodes" in data:
                self._nodes = data.get("nodes", {})
                self._edges = data.get("edges", {})
        except Exception as e:
            logger.warning(f"Failed to load KnowledgeGraph: {e}")


_global_knowledge_graph: Optional[KnowledgeGraph] = None


def get_knowledge_graph() -> KnowledgeGraph:
    """Singleton getter for KnowledgeGraph."""
    global _global_knowledge_graph
    if _global_knowledge_graph is None:
        _global_knowledge_graph = KnowledgeGraph()
    return _global_knowledge_graph
