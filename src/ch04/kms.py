# src/ch04/kms.py
"""
Knowledge Management System
"""

import json
import os
from dataclasses import dataclass, field
from typing import Any

from dotenv import load_dotenv
from loguru import logger

from ch03.prompt import load_prompt
from ch04.graph_db import KnowledgeGraph, Node
from ch04.qa_index import QAIndex

#

_ = load_dotenv()

EXTRACT_ENTITIES_PROMPT = load_prompt(
  "ch04/knowledge/extract_entities"
)
EXTRACT_RELATIONSHIPS_PROMPT = load_prompt(
  "ch04/knowledge/extract_relationships"
)
EXTRACT_ATTRIBUTES_PROMPT = load_prompt(
  "ch04/knowledge/extract_attributes"
)

#


@dataclass
class Content:
  id: str
  type: str
  content: str
  metadata: dict[str, Any]


@dataclass
class IngestionReport:
  """
  Represents a report of the artifacts produced during content ingestion.

  Attributes:
      content_id (str): The ID of the ingested content.
      content_type (str): The type of the ingested content.
      file_path (str): The path where the content file is stored.
      entities (list[dict[str, str]]): List of extracted entities.
      relationships (list[dict[str, str]]): List of extracted relationships.
      attributes (dict[str, dict[str, Any]]): Dictionary of extracted attributes for each entity.
      qa_pairs (list[dict[str, str]]): List of generated question-answer pairs.
      metadata (dict[str, Any]): Additional metadata about the ingestion process.
      errors (list[str]): List of any errors encountered during ingestion.
  """

  content_id: str
  content_type: str
  file_path: str
  entities: list[dict[str, str]] = field(
    default_factory=list
  )
  relationships: list[dict[str, str]] = field(
    default_factory=list
  )
  attributes: dict[str, dict[str, Any]] = field(
    default_factory=dict
  )
  qa_pairs: list[dict[str, str]] = field(
    default_factory=list
  )
  metadata: dict[str, Any] = field(
    default_factory=dict
  )
  errors: list[str] = field(default_factory=list)

  def summary(self) -> str:
    """Generate a summary of the ingestion report."""
    return f"""
        Ingestion Report for Content ID: {self.content_id}
        Content Type: {self.content_type}
        File Path: {self.file_path}
        Entities Extracted: {len(self.entities)}
        Relationships Extracted: {len(self.relationships)}
        Attributes Extracted: {len(self.attributes)}
        QA Pairs Generated: {len(self.qa_pairs)}
        Errors Encountered: {len(self.errors)}
        """


@dataclass
class RetrievedContent:
  id: str
  type: str
  content: str
  metadata: dict[str, Any]
  question: str
  answer: str
  similarity: float
  related_content: list[str]

  def __str__(self) -> str:
    return f"""
        ID: {self.id}
        Type: {self.type}
        Content: {self.content}
        Metadata: {self.metadata}
        Question: {self.question}
        Answer: {self.answer}
        Similarity: {self.similarity}
        Related Content: {self.related_content}
        """


#


class KnowledgeManagementSystem:
  def __init__(
    self,
    db_dir: str = "db",
    qa_collection_name: str = "qa_index",
  ):
    os.makedirs(db_dir, exist_ok=True)
    self.graph = KnowledgeGraph(
      os.path.join(db_dir, "knowledge_graph.db")
    )
    self.qa_index = QAIndex(
      db_dir=db_dir,
      collection_name=qa_collection_name,
    )
    self.file_storage_path = os.path.join(
      db_dir, "files"
    )
    os.makedirs(self.file_storage_path, exist_ok=True)

  async def ingest_content(
    self, content: Content
  ) -> IngestionReport:
    """
    Ingest new content into the KMS and produce an ingestion report.

    Parameters
    ----------
    content : Content
        The content to ingest.

    Returns
    -------
    IngestionReport
        A report detailing the ingestion process and its results.
    """

    # Store content in file system
    file_path = self._store_file(content)

    # Add node to knowledge graph
    self.graph.add_or_update_node(
      id=content.id,
      type=content.type,
      content=file_path,
      metadata=content.metadata,
    )
    logger.info(
      f"Ingested content with ID {content.id} and type {content.type}: {content.content[:100]}"
    )

    report = IngestionReport(
      content_id=content.id,
      content_type=content.type,
      file_path=file_path,
      metadata=content.metadata,
    )

    # Extract entities
    entities_json = str(
      await EXTRACT_ENTITIES_PROMPT.call_llm(
        text=content.content
      )
    )
    assert isinstance(entities_json, str)
    entities = json.loads(entities_json)["entities"]
    report.entities = entities
    logger.info(
      f"Extracted {len(entities)} entities from content with ID {content.id}"
    )

    # Extract relationships
    relationships_json = str(
      await EXTRACT_RELATIONSHIPS_PROMPT.call_llm(
        text=content.content,
        entities=json.dumps(entities),
      )
    )
    assert isinstance(relationships_json, str)
    relationships = json.loads(relationships_json)[
      "relationships"
    ]
    report.relationships = relationships
    logger.info(
      f"Extracted {len(relationships)} relationships from content with ID {content.id}"
    )

    # Extract attributes
    attributes_json = str(
      await EXTRACT_ATTRIBUTES_PROMPT.call_llm(
        text=content.content,
        entities=json.dumps(entities),
      )
    )
    assert isinstance(attributes_json, str)
    attributes = json.loads(attributes_json)[
      "attributes"
    ]
    report.attributes = attributes
    logger.info(
      f"Extracted attributes for {len(attributes)} entities from content with ID {content.id}"
    )
    entity_attributes: dict[str, dict[str, str]] = {
      entity["entity"]: {
        prop["key"]: prop["value"]
        for prop in entity["properties"]
      }
      for entity in attributes
    }

    # Add entities to knowledge graph
    for entity in entities:
      self.graph.add_or_update_node(
        id=entity["name"],
        type=entity["type"],
        content=f"Entity of type {entity['type']}",
        metadata=entity_attributes.get(
          entity["name"], {}
        ),
      )
      logger.info(
        f"Added entity {entity['name']} to content with ID {content.id}"
      )

    # Add relationships to knowledge graph
    for rel in relationships:
      self.graph.add_or_update_edge(
        source=rel["source"],
        target=rel["target"],
        type=rel["relationship"],
      )
      logger.info(
        f"Added relationship {rel['source']} -> {rel['target']} of type {rel['relationship']} to content with ID {content.id}"
      )

    # Generate QA pairs and add to QA index
    qa_pairs = await self._generate_qa_pairs(
      content.content
    )
    report.qa_pairs = qa_pairs
    for qa_pair in qa_pairs:
      await self.qa_index.add_qa(
        question=qa_pair["q"],
        answer=qa_pair["a"],
        metadata={
          "content_id": content.id,
          **content.metadata,
        },
      )
      logger.info(
        f"Added question-answer pair to content with ID {content.id}: {qa_pair}"
      )

    return report

  async def retrieve_content(
    self,
    query: str,
    n_results: int = 5,
    metadata_filter: dict[str, Any] | None = None,
    num_rewordings: int = 3,
  ) -> list[RetrievedContent]:
    """
    Retrieve content based on a query.

    Parameters
    ----------
    query : str
        The query string.
    n_results : int, optional
        Number of results to return.
    metadata_filter : dict[str, Any] | None, optional
        Filter for metadata.
    num_rewordings : int, optional
        Number of query rewordings to generate.

    Returns
    -------
    list[RetrievedContent]
        List of retrieved content items.
    """
    print(f"Query: {query}")
    if not query:
      raise ValueError("Query cannot be empty")

    # Perform QA retrieval
    qa_results = await self.qa_index.query(
      query,
      n_results=n_results,
      metadata_filter=metadata_filter,
      num_rewordings=num_rewordings,
    )

    # Fetch corresponding nodes from knowledge graph
    # and create RetrievedContent objects
    retrieved_content: list[RetrievedContent] = []
    for qa_result in qa_results:
      source_id = qa_result["metadata"].get(
        "content_id"
      )
      if source_id:
        node = self.graph.get_node(source_id)
        if node:
          related_nodes = self.graph.get_subgraph(
            node_id=node.id,
            depth=5,
          )["nodes"]
          result = self._format_result(
            node, qa_result, related_nodes
          )
          retrieved_content.append(
            RetrievedContent(**result)
          )

    return retrieved_content

  async def update_content(
    self, content: Content
  ) -> None:
    """
    Update existing content in the KMS.

    Parameters
    ----------
    content : Content
        The updated content.
    """
    # Update file in file system
    file_path = self._store_file(content)

    # Update node in knowledge graph
    self.graph.add_or_update_node(
      id=content.id,
      type=content.type,
      content=file_path,
      metadata=content.metadata,
    )

    # Update QA pairs
    self.qa_index.delete_where(
      {"content_id": content.id}
    )
    qa_pairs = await self._generate_qa_pairs(
      content.content
    )
    for qa_pair in qa_pairs:
      await self.qa_index.add_qa(
        question=qa_pair["q"],
        answer=qa_pair["a"],
        metadata={
          "content_id": content.id,
          **content.metadata,
        },
      )

  async def delete_content(
    self, content_id: str
  ) -> None:
    """
    Delete content from the KMS.

    Parameters
    ----------
    content_id : str
        The ID of the content to delete.
    """
    # Remove node from knowledge graph
    node = self.graph.get_node(content_id)
    if not node:
      raise ValueError(
        f"Content with ID {content_id} not found."
      )

    self._delete_file(node.content)
    self.graph.delete_node(content_id)

    # Remove QA pairs from QA index
    deleted_count = self.qa_index.delete_where(
      {"content_id": content_id}
    )

    logger.info(
      f"Deleted content with ID {content_id}. Removed {deleted_count} QA pairs from the index."
    )

  def create_relationship(
    self,
    source_id: str,
    target_id: str,
    relationship_type: str,
    metadata: dict[str, Any] | None = None,
  ) -> None:
    """
    Create a relationship between two content items.

    Parameters
    ----------
    source_id : str
        The ID of the source content.
    target_id : str
        The ID of the target content.
    relationship_type : str
        The type of relationship.
    metadata : dict[str, Any] | None, optional
        Additional metadata for the relationship.

    Raises
    ------
    ValueError
        If either the source or target content is not found in the graph.
    """
    if not self.graph.get_node(source_id):
      raise ValueError(
        f"Source content with ID {source_id} not found."
      )
    if not self.graph.get_node(target_id):
      raise ValueError(
        f"Target content with ID {target_id} not found."
      )
    self.graph.add_or_update_edge(
      source=source_id,
      target=target_id,
      type=relationship_type,
      metadata=metadata or {},
    )

  def get_related_content(
    self,
    content_id: str,
    relationship_type: str | None = None,
  ) -> list[Node]:
    """
    Get content related to a given content item.

    Parameters
    ----------
    content_id : str
        The ID of the content item.
    relationship_type : str or None, optional
        Filter by relationship type.

    Returns
    -------
    list of Node
        List of related content nodes.
    """
    return self.graph.get_neighbors(
      content_id, relationship_type
    )

  def _store_file(self, content: Content) -> str:
    file_path = os.path.join(
      self.file_storage_path, f"{content.id}.txt"
    )
    with open(file_path, "w", encoding="utf-8") as f:
      f.write(content.content)
    return file_path

  def _read_file(self, file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8") as f:
      return f.read()

  def _delete_file(self, file_path: str) -> None:
    if os.path.exists(file_path):
      os.remove(file_path)

  async def _generate_qa_pairs(
    self, content: str
  ) -> list[dict[str, str]]:
    # TODO: chunking
    print(
      f"Generating QA pairs for content: {content}"
    )
    qa_pairs = await self.qa_index.generate_qa_pairs(
      content
    )
    print(f"Generated {len(qa_pairs)} QA pairs")
    return qa_pairs

  def _format_result(
    self,
    node: Node,
    qa_result: dict[str, Any],
    related_nodes: list[Node],
  ) -> dict[str, Any]:
    return {
      "id": node.id,
      "type": node.type,
      "content": self._read_file(node.content),
      "metadata": node.metadata,
      "question": qa_result["question"],
      "answer": qa_result["answer"],
      "similarity": qa_result["similarity"],
      "related_content": [
        self._read_file(rn.content)
        for rn in related_nodes
      ],
    }

  def read_content(self, content_or_path: str) -> str:
    """
    Read content from a file if it's a path, or return the content directly if it's not.
    """
    if os.path.exists(content_or_path):
      return self._read_file(content_or_path)
    return content_or_path
