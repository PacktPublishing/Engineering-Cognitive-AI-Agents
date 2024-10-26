import os

import pytest
from kms import Content, KnowledgeManagementSystem


@pytest.fixture(scope="module")
def kms():
  # Setup
  test_db_dir = "test_db"
  os.makedirs(test_db_dir, exist_ok=True)
  kms = KnowledgeManagementSystem(db_dir=test_db_dir)

  yield kms

  # Teardown
  kms.graph.conn.close()
  for root, dirs, files in os.walk(
    test_db_dir, topdown=False
  ):
    for name in files:
      os.remove(os.path.join(root, name))
    for name in dirs:
      os.rmdir(os.path.join(root, name))
  os.rmdir(test_db_dir)


def test_ingest_content(kms):
  content = Content(
    id="test1",
    type="text",
    content="This is a test content.",
    metadata={"author": "John Doe"},
  )
  kms.ingest_content(content)

  # Check if content is stored in file system
  assert os.path.exists(
    os.path.join(kms.file_storage_path, "test1.txt")
  )

  # Check if node is added to knowledge graph
  node = kms.graph.get_node("test1")
  assert node is not None
  assert node.type == "text"
  assert node.metadata["author"] == "John Doe"

  # Check if QA pairs are added to QA index
  results = kms.qa_index.query(
    "What is the content described in the text?"
  )
  assert len(results) > 0
  assert any(
    "test content" in result["answer"].lower()
    for result in results
  )


def test_retrieve_content(kms):
  results = kms.retrieve_content("test content")
  assert len(results) > 0
  assert results[0]["id"] == "test1"
  assert results[0]["type"] == "text"
  assert (
    "This is a test content." in results[0]["content"]
  )


def test_update_content(kms):
  updated_content = Content(
    id="test1",
    type="text",
    content="This is updated test content.",
    metadata={"author": "Jane Doe"},
  )
  kms.update_content(updated_content)

  # Check if file content is updated
  with open(
    os.path.join(kms.file_storage_path, "test1.txt"),
    "r",
    encoding="utf-8",
  ) as f:
    assert f.read() == "This is updated test content."

  # Check if node in knowledge graph is updated
  node = kms.graph.get_node("test1")
  assert node.metadata["author"] == "Jane Doe"

  # Check if QA pairs are updated
  results = kms.qa_index.query(
    "Is the test content old or current?"
  )
  assert len(results) > 0
  assert any(
    "updated" in result["answer"].lower()
    for result in results
  )


def test_delete_content(kms):
  kms.delete_content("test1")

  # Check if file is deleted
  assert not os.path.exists(
    os.path.join(kms.file_storage_path, "test1.txt")
  )

  # Check if node is deleted from knowledge graph
  assert kms.graph.get_node("test1") is None

  # Check if QA pairs are deleted from QA index
  results = kms.qa_index.query(
    "What is the content described in the text?"
  )
  assert all(
    result["metadata"].get("content_id") != "test1"
    for result in results
  )


def test_create_relationship(kms):
  content1 = Content(
    id="rel1",
    type="text",
    content="Related content 1",
    metadata={},
  )
  content2 = Content(
    id="rel2",
    type="text",
    content="Related content 2",
    metadata={},
  )
  kms.ingest_content(content1)
  kms.ingest_content(content2)

  kms.create_relationship(
    "rel1", "rel2", "related_to", {"strength": 0.8}
  )

  # Check if relationship is created in knowledge graph
  neighbors = kms.graph.get_neighbors("rel1")
  assert any(
    neighbor.id == "rel2" for neighbor in neighbors
  )


def test_get_related_content(kms):
  related_content = kms.get_related_content("rel1")
  assert len(related_content) > 0
  assert any(
    content.id == "rel2" for content in related_content
  )


def test_ingest_multiple_content_types(kms):
  text_content = Content(
    id="multi1",
    type="text",
    content="Text content",
    metadata={},
  )
  markdown_content = Content(
    id="multi2",
    type="markdown",
    content="# Markdown content",
    metadata={},
  )

  kms.ingest_content(text_content)
  kms.ingest_content(markdown_content)

  assert os.path.exists(
    os.path.join(kms.file_storage_path, "multi1.txt")
  )
  assert os.path.exists(
    os.path.join(kms.file_storage_path, "multi2.txt")
  )

  assert kms.graph.get_node("multi1") is not None
  assert kms.graph.get_node("multi2") is not None


def test_retrieve_content_with_metadata_filter(kms):
  content = Content(
    id="filter_test",
    type="text",
    content="Content for metadata filtering",
    metadata={
      "category": "test",
      "priority": "high",
    },
  )
  kms.ingest_content(content)

  results = kms.retrieve_content(
    "metadata filtering",
    metadata_filter={"category": "test"},
  )
  assert len(results) > 0
  assert results[0]["id"] == "filter_test"
  assert results[0]["metadata"]["priority"] == "high"


def test_update_relationship(kms):
  kms.create_relationship(
    "rel1", "rel2", "related_to", {"strength": 0.5}
  )
  edge = kms.graph.get_edge(
    "rel1", "rel2", "related_to"
  )

  assert edge is not None
  assert edge.metadata["strength"] == 0.5

  kms.create_relationship(
    "rel1", "rel2", "related_to", {"strength": 0.9}
  )
  edge = kms.graph.get_edge(
    "rel1", "rel2", "related_to"
  )

  assert edge is not None
  assert edge.metadata["strength"] == 0.9


def test_delete_relationship(kms):
  kms.graph.delete_edge("rel1", "rel2", "related_to")
  neighbors = kms.graph.get_neighbors("rel1")
  assert all(
    neighbor.id != "rel2" for neighbor in neighbors
  )


def test_content_versioning(kms):
  content = Content(
    id="version_test",
    type="text",
    content="Version 1",
    metadata={"version": 1},
  )
  kms.ingest_content(content)

  updated_content = Content(
    id="version_test",
    type="text",
    content="Version 2",
    metadata={"version": 2},
  )
  kms.update_content(updated_content)

  node = kms.graph.get_node("version_test")
  assert node.metadata["version"] == 2

  with open(
    os.path.join(
      kms.file_storage_path, "version_test.txt"
    ),
    "r",
    encoding="utf-8",
  ) as f:
    assert f.read() == "Version 2"


def test_error_handling(kms):
  with pytest.raises(ValueError):
    kms.retrieve_content("")

  with pytest.raises(ValueError):
    kms.delete_content("non_existent_id")

  with pytest.raises(ValueError):
    kms.create_relationship(
      "non_existent_id1",
      "non_existent_id2",
      "invalid_relation",
    )
