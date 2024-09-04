import json
import sqlite3
import time
import uuid
from dataclasses import dataclass
from typing import Any, Literal, Optional

#


@dataclass
class Node:
  id: str
  type: str
  content: str
  metadata: dict[str, Any]
  created_at: float
  last_accessed: float
  importance: float


@dataclass
class Edge:
  id: str
  source: str
  target: str
  type: str
  metadata: dict[str, Any]


class KnowledgeGraph:
  def __init__(self, db_file: str) -> None:
    self.db_file = db_file
    self.conn = sqlite3.connect(db_file)
    self.conn.row_factory = sqlite3.Row
    self._create_tables()

  def __str__(self) -> str:
    return f"Database(db_file='{self.db_file}')"

  def __repr__(self) -> str:
    return self.__str__()

  def _create_tables(self) -> None:
    with self.conn:
      # Nodes table
      self.conn.execute("""
                CREATE TABLE IF NOT EXISTS nodes (
                    id TEXT PRIMARY KEY,
                    type TEXT,
                    content TEXT,
                    metadata TEXT,
                    created_at REAL,
                    last_accessed REAL,
                    importance REAL DEFAULT 0.5
                )
            """)

      # Edges table
      self.conn.execute("""
                CREATE TABLE IF NOT EXISTS edges (
                    id TEXT PRIMARY KEY,
                    source TEXT,
                    target TEXT,
                    type TEXT,
                    metadata TEXT,
                    FOREIGN KEY(source) REFERENCES nodes(id),
                    FOREIGN KEY(target) REFERENCES nodes(id),
                    UNIQUE(source, target, type)
                )
            """)

  def add_or_update_node(
    self,
    id: str,
    type: str,
    content: str,
    metadata: Optional[dict[str, Any]] = None,
    importance: float = 0.5,
  ) -> None:
    current_time = time.time()
    with self.conn:
      self.conn.execute(
        """
                INSERT INTO nodes (id, type, content, metadata, created_at, last_accessed, importance)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    type = excluded.type,
                    content = excluded.content,
                    metadata = excluded.metadata,
                    last_accessed = excluded.last_accessed,
                    importance = excluded.importance
            """,
        (
          id,
          type,
          content,
          json.dumps(metadata or {}),
          current_time,
          current_time,
          importance,
        ),
      )

  def add_or_update_edge(
    self,
    source: str,
    target: str,
    type: str,
    metadata: dict[str, Any] = None,
  ) -> None:
    edge_id = str(
      uuid.uuid4()
    )  # Generate a unique text ID
    with self.conn:
      self.conn.execute(
        """
                INSERT INTO edges (id, source, target, type, metadata)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(source, target, type) DO UPDATE SET
                    metadata = excluded.metadata
                """,
        (
          edge_id,
          source,
          target,
          type,
          json.dumps(metadata or {}),
        ),
      )

  def update_node_importance(
    self, id: str, importance: float
  ) -> None:
    with self.conn:
      self.conn.execute(
        """
                UPDATE nodes
                SET importance = ?, last_accessed = ?
                WHERE id = ?
                """,
        (importance, time.time(), id),
      )

  def get_all_nodes(self) -> list[Node]:
    with self.conn:
      results = self.conn.execute(
        "SELECT * FROM nodes"
      ).fetchall()
    return [
      Node(
        **{
          k: json.loads(v) if k == "metadata" else v
          for k, v in dict(row).items()
        }
      )
      for row in results
    ]

  def get_node(self, id: str) -> Optional[Node]:
    with self.conn:
      result = self.conn.execute(
        "SELECT * FROM nodes WHERE id = ?",
        (id,),
      ).fetchone()
    return (
      Node(
        **{
          k: json.loads(v) if k == "metadata" else v
          for k, v in dict(result).items()
        }
      )
      if result
      else None
    )

  def get_nodes_by_type(self, type: str) -> list[Node]:
    with self.conn:
      results = self.conn.execute(
        "SELECT * FROM nodes WHERE type = ?",
        (type,),
      ).fetchall()
    return [
      Node(
        **{
          k: json.loads(v) if k == "metadata" else v
          for k, v in dict(row).items()
        }
      )
      for row in results
    ]

  def get_node_degree(
    self, node_id: str
  ) -> dict[str, int]:
    with self.conn:
      in_degree = self.conn.execute(
        "SELECT COUNT(*) FROM edges WHERE target = ?",
        (node_id,),
      ).fetchone()[0]
      out_degree = self.conn.execute(
        "SELECT COUNT(*) FROM edges WHERE source = ?",
        (node_id,),
      ).fetchone()[0]
    return {
      "in_degree": in_degree,
      "out_degree": out_degree,
    }

  def get_edge(
    self,
    source: str,
    target: str,
    edge_type: Optional[str] = None,
  ) -> Optional[Edge]:
    with self.conn:
      if edge_type is None:
        query = "SELECT * FROM edges WHERE source = ? AND target = ?"
        params = (source, target)
      else:
        query = "SELECT * FROM edges WHERE source = ? AND target = ? AND type = ?"
        params = (source, target, edge_type)

      result = self.conn.execute(
        query, params
      ).fetchone()

    if result:
      return Edge(
        **{
          k: json.loads(v) if k == "metadata" else v
          for k, v in dict(result).items()
        }
      )
    return None

  def get_edges(
    self,
    node_id: str,
    direction: Literal[
      "outgoing", "incoming"
    ] = "outgoing",
  ) -> list[Edge]:
    with self.conn:
      if direction == "outgoing":
        query = "SELECT * FROM edges WHERE source = ?"
      else:  # incoming
        query = "SELECT * FROM edges WHERE target = ?"
      results = self.conn.execute(
        query, (node_id,)
      ).fetchall()
    return [
      Edge(
        **{
          k: json.loads(v) if k == "metadata" else v
          for k, v in dict(row).items()
        }
      )
      for row in results
    ]

  def get_edges_by_type(self, type: str) -> list[Edge]:
    with self.conn:
      results = self.conn.execute(
        "SELECT * FROM edges WHERE type = ?",
        (type,),
      ).fetchall()
    return [
      Edge(
        **{
          k: json.loads(v) if k == "metadata" else v
          for k, v in dict(row).items()
        }
      )
      for row in results
    ]

  def search_nodes(self, query: str) -> list[Node]:
    with self.conn:
      results = self.conn.execute(
        """
                SELECT DISTINCT *
                FROM nodes
                WHERE content LIKE ? OR metadata LIKE ?
                """,
        (f"%{query}%", f"%{query}%"),
      ).fetchall()
    return [
      Node(
        **{
          k: json.loads(v) if k == "metadata" else v
          for k, v in dict(row).items()
        }
      )
      for row in results
    ]

  def delete_node(self, id: str) -> None:
    with self.conn:
      self.conn.execute(
        "DELETE FROM nodes WHERE id = ?", (id,)
      )
      self.conn.execute(
        "DELETE FROM edges WHERE source = ? OR target = ?",
        (id, id),
      )

  def delete_edge(
    self, source: str, target: str, edge_type: str
  ) -> None:
    with self.conn:
      self.conn.execute(
        "DELETE FROM edges WHERE source = ? AND target = ? AND type = ?",
        (source, target, edge_type),
      )

  def get_neighbors(
    self,
    node_id: str,
    edge_type: Optional[str] = None,
  ) -> list[Node]:
    query = """
            SELECT DISTINCT n.*
            FROM nodes n
            JOIN edges e ON (n.id = e.target OR n.id = e.source)
            WHERE (e.source = ? OR e.target = ?) AND n.id != ?
        """
    params = [node_id, node_id, node_id]
    if edge_type:
      query += " AND e.type = ?"
      params.append(edge_type)

    with self.conn:
      results = self.conn.execute(
        query, params
      ).fetchall()
    return [
      Node(
        **{
          k: json.loads(v) if k == "metadata" else v
          for k, v in dict(row).items()
        }
      )
      for row in results
    ]

  def get_subgraph(
    self, node_id: str, depth: int = 1
  ) -> dict[str, list[Any]]:
    nodes = set()
    edges = set()

    def traverse(current_id, current_depth):
      if current_depth > depth:
        return
      nodes.add(current_id)
      if (
        current_depth < depth
      ):  # Only add edges if we're not at the maximum depth
        neighbors = self.get_neighbors(current_id)
        for neighbor in neighbors:
          edge = self.get_edge(
            current_id, neighbor.id
          ) or self.get_edge(neighbor.id, current_id)
          if edge:
            edges.add(
              (
                edge.source,
                edge.target,
                edge.type,
              )
            )
          if neighbor.id not in nodes:
            traverse(
              neighbor.id,
              current_depth + 1,
            )

    traverse(node_id, 0)

    return {
      "nodes": [
        self.get_node(node_id) for node_id in nodes
      ],
      "edges": [
        self.get_edge(source, target)
        for source, target, _ in edges
      ],
    }
