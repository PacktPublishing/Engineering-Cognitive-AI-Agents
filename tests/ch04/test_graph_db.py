import os
import time

import pytest
from graph_db import KnowledgeGraph


@pytest.fixture
def temp_db():
  db_file = "test_graph.db"
  graph = KnowledgeGraph(db_file)
  yield graph
  graph.conn.close()
  os.remove(db_file)


def test_create_database(temp_db):
  """Test database creation and basic structure."""
  assert isinstance(temp_db, KnowledgeGraph)
  assert os.path.exists(temp_db.db_file)


def test_add_node(temp_db):
  """Test adding a node to the database."""
  temp_db.add_or_update_node(
    "1", "person", "John Doe", {"age": 30}
  )
  node = temp_db.get_node("1")
  assert node.id == "1"
  assert node.type == "person"
  assert node.content == "John Doe"
  assert node.metadata == {"age": 30}


def test_update_node(temp_db):
  """Test updating an existing node."""
  temp_db.add_or_update_node(
    "1", "person", "John Doe", {"age": 30}
  )
  temp_db.add_or_update_node(
    "1", "person", "John Doe", {"age": 31}
  )
  node = temp_db.get_node("1")
  assert node.metadata == {"age": 31}


def test_add_edge(temp_db):
  """Test adding an edge between nodes."""
  temp_db.add_or_update_node("1", "person", "John Doe")
  temp_db.add_or_update_node("2", "person", "Jane Doe")
  temp_db.add_or_update_edge(
    "1", "2", "knows", {"since": 2020}
  )
  edges = temp_db.get_edges("1")
  assert len(edges) == 1
  assert edges[0].source == "1"
  assert edges[0].target == "2"
  assert edges[0].type == "knows"
  assert edges[0].metadata == {"since": 2020}


def test_get_all_nodes(temp_db):
  """Test retrieving all nodes."""
  temp_db.add_or_update_node("1", "person", "John Doe")
  temp_db.add_or_update_node("2", "person", "Jane Doe")
  nodes = temp_db.get_all_nodes()
  assert len(nodes) == 2
  assert {node.id for node in nodes} == {"1", "2"}


def test_search_nodes(temp_db):
  """Test searching nodes."""
  temp_db.add_or_update_node(
    "1", "person", "John Doe", {"city": "New York"}
  )
  temp_db.add_or_update_node(
    "2", "person", "Jane Doe", {"city": "London"}
  )
  results = temp_db.search_nodes("John")
  assert len(results) == 1
  assert results[0].id == "1"


def test_delete_node(temp_db):
  """Test deleting a node and its associated edges."""
  temp_db.add_or_update_node("1", "person", "John Doe")
  temp_db.add_or_update_node("2", "person", "Jane Doe")
  temp_db.add_or_update_edge("1", "2", "knows")
  temp_db.delete_node("1")
  assert temp_db.get_node("1") is None
  assert (
    len(temp_db.get_edges("2", direction="incoming"))
    == 0
  )


def test_update_node_importance(temp_db):
  """Test updating node importance."""
  temp_db.add_or_update_node("1", "person", "John Doe")
  temp_db.update_node_importance("1", 0.8)
  node = temp_db.get_node("1")
  assert node.importance == 0.8


def test_get_nodes_by_type(temp_db):
  """Test retrieving nodes by type."""
  temp_db.add_or_update_node("1", "person", "John Doe")
  temp_db.add_or_update_node("2", "person", "Jane Doe")
  temp_db.add_or_update_node("3", "city", "New York")
  persons = temp_db.get_nodes_by_type("person")
  assert len(persons) == 2
  assert all(node.type == "person" for node in persons)


def test_get_edges_by_type(temp_db):
  """Test retrieving edges by type."""
  temp_db.add_or_update_node("1", "person", "John Doe")
  temp_db.add_or_update_node("2", "person", "Jane Doe")
  temp_db.add_or_update_node(
    "3", "person", "Bob Smith"
  )
  temp_db.add_or_update_edge("1", "2", "knows")
  temp_db.add_or_update_edge("1", "3", "works_with")
  knows_edges = temp_db.get_edges_by_type("knows")
  assert len(knows_edges) == 1
  assert knows_edges[0].type == "knows"


def test_get_node_degree(temp_db):
  """Test getting node degree."""
  temp_db.add_or_update_node("1", "person", "John Doe")
  temp_db.add_or_update_node("2", "person", "Jane Doe")
  temp_db.add_or_update_node(
    "3", "person", "Bob Smith"
  )
  temp_db.add_or_update_edge("1", "2", "knows")
  temp_db.add_or_update_edge("3", "1", "knows")
  degree = temp_db.get_node_degree("1")
  assert degree == {"in_degree": 1, "out_degree": 1}


def test_get_neighbors(temp_db):
  """Test getting node neighbors."""
  temp_db.add_or_update_node("1", "person", "John Doe")
  temp_db.add_or_update_node("2", "person", "Jane Doe")
  temp_db.add_or_update_node(
    "3", "person", "Bob Smith"
  )
  temp_db.add_or_update_edge("1", "2", "knows")
  temp_db.add_or_update_edge("1", "3", "works_with")
  neighbors = temp_db.get_neighbors("1")
  assert len(neighbors) == 2
  assert {n.id for n in neighbors} == {"2", "3"}


def test_get_neighbors_with_edge_type(temp_db):
  """Test getting node neighbors with specific edge type."""
  temp_db.add_or_update_node("1", "person", "John Doe")
  temp_db.add_or_update_node("2", "person", "Jane Doe")
  temp_db.add_or_update_node(
    "3", "person", "Bob Smith"
  )
  temp_db.add_or_update_edge("1", "2", "knows")
  temp_db.add_or_update_edge("1", "3", "works_with")
  neighbors = temp_db.get_neighbors(
    "1", edge_type="knows"
  )
  assert len(neighbors) == 1
  assert neighbors[0].id == "2"


def test_get_subgraph(temp_db):
  """Test getting subgraph."""
  temp_db.add_or_update_node("1", "person", "John Doe")
  temp_db.add_or_update_node("2", "person", "Jane Doe")
  temp_db.add_or_update_node(
    "3", "person", "Bob Smith"
  )
  temp_db.add_or_update_node(
    "4", "person", "Alice Johnson"
  )
  temp_db.add_or_update_edge("1", "2", "knows")
  temp_db.add_or_update_edge("2", "3", "knows")
  temp_db.add_or_update_edge("3", "4", "knows")
  subgraph = temp_db.get_subgraph("1", depth=2)
  assert len(subgraph["nodes"]) == 3
  assert len(subgraph["edges"]) == 2


def test_get_edge(temp_db):
  """Test getting a specific edge."""
  temp_db.add_or_update_node("1", "person", "John Doe")
  temp_db.add_or_update_node("2", "person", "Jane Doe")
  temp_db.add_or_update_edge(
    "1", "2", "knows", {"since": 2020}
  )
  edge = temp_db.get_edge("1", "2")
  assert edge.source == "1"
  assert edge.target == "2"
  assert edge.type == "knows"
  assert edge.metadata == {"since": 2020}


def test_node_timestamps(temp_db):
  """Test node creation and last accessed timestamps."""
  before = time.time()
  temp_db.add_or_update_node("1", "person", "John Doe")
  after = time.time()
  node = temp_db.get_node("1")
  assert before <= node.created_at <= after
  assert before <= node.last_accessed <= after


def test_node_default_importance(temp_db):
  """Test default node importance."""
  temp_db.add_or_update_node("1", "person", "John Doe")
  node = temp_db.get_node("1")
  assert node.importance == 0.5
