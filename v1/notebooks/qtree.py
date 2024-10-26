import json
import sqlite3
from typing import Dict, Optional

import graphviz


class QuestionNode:
  def __init__(
    self,
    id: int,
    question: str,
    answer: Optional[str] = None,
    metadata: Dict = None,
    parent_id: Optional[int] = None,
  ):
    self.id = id
    self.question = question
    self.answer = answer
    self.metadata = metadata or {}
    self.parent_id = parent_id
    self.children: list[QuestionNode] = []
    self.priority = 0


class QuestionTree:
  def __init__(self, db_path: str):
    self.conn = sqlite3.connect(db_path)
    self.cursor = self.conn.cursor()
    self.create_tables()
    self.root: Optional[QuestionNode] = None

  def create_tables(self):
    self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY,
                question TEXT NOT NULL,
                answer TEXT,
                metadata TEXT,
                parent_id INTEGER,
                FOREIGN KEY (parent_id) REFERENCES questions (id)
            )
        """)
    self.conn.commit()

  def add_question(
    self,
    question: str,
    parent_id: Optional[int] = None,
    answer: Optional[str] = None,
    metadata: Dict = None,
  ) -> int:
    metadata_json = (
      json.dumps(metadata) if metadata else None
    )
    self.cursor.execute(
      """
            INSERT INTO questions (question, answer, metadata, parent_id)
            VALUES (?, ?, ?, ?)
        """,
      (
        question,
        answer,
        metadata_json,
        parent_id,
      ),
    )
    self.conn.commit()
    return self.cursor.lastrowid

  def update_answer(
    self, question_id: int, answer: str
  ):
    self.cursor.execute(
      """
            UPDATE questions SET answer = ? WHERE id = ?
        """,
      (answer, question_id),
    )
    self.conn.commit()

  def get_question(
    self, question_id: int
  ) -> Optional[QuestionNode]:
    self.cursor.execute(
      """
            SELECT id, question, answer, metadata, parent_id
            FROM questions WHERE id = ?
        """,
      (question_id,),
    )
    row = self.cursor.fetchone()
    if row:
      (
        id,
        question,
        answer,
        metadata_json,
        parent_id,
      ) = row
      metadata = (
        json.loads(metadata_json)
        if metadata_json
        else None
      )
      return QuestionNode(
        id,
        question,
        answer,
        metadata,
        parent_id,
      )
    return None

  def get_children(
    self, parent_id: int
  ) -> list[QuestionNode]:
    self.cursor.execute(
      """
            SELECT id, question, answer, metadata, parent_id
            FROM questions WHERE parent_id = ?
        """,
      (parent_id,),
    )
    children = []
    for row in self.cursor.fetchall():
      (
        id,
        question,
        answer,
        metadata_json,
        parent_id,
      ) = row
      metadata = (
        json.loads(metadata_json)
        if metadata_json
        else None
      )
      children.append(
        QuestionNode(
          id,
          question,
          answer,
          metadata,
          parent_id,
        )
      )
    return children

  def build_tree(self):
    self.cursor.execute(
      "SELECT id FROM questions WHERE parent_id IS NULL"
    )
    root_id = self.cursor.fetchone()
    if root_id:
      self.root = self._build_subtree(root_id[0])

  def _build_subtree(
    self, node_id: int
  ) -> QuestionNode:
    node = self.get_question(node_id)
    if node:
      node.children = [
        self._build_subtree(child.id)
        for child in self.get_children(node_id)
      ]
    return node

  def calculate_priorities(self):
    if self.root:
      self._calculate_subtree_priority(self.root)

  def _calculate_subtree_priority(
    self, node: QuestionNode
  ) -> int:
    if not node.children:
      node.priority = 1
      return 1

    child_priorities = [
      self._calculate_subtree_priority(child)
      for child in node.children
    ]
    node.priority = sum(child_priorities)
    return node.priority

  def find_duplicate_questions(
    self,
  ) -> dict[str, list[int]]:
    self.cursor.execute("""
            SELECT question, GROUP_CONCAT(id) as ids
            FROM questions
            GROUP BY question
            HAVING COUNT(*) > 1
        """)
    duplicates = {}
    for row in self.cursor.fetchall():
      question, id_list = row
      duplicates[question] = [
        int(id) for id in id_list.split(",")
      ]
    return duplicates

  def get_high_priority_questions(
    self, limit: int = 10
  ) -> list[QuestionNode]:
    if not self.root:
      self.build_tree()
    self.calculate_priorities()

    all_nodes = self._flatten_tree(self.root)
    return sorted(
      all_nodes,
      key=lambda x: x.priority,
      reverse=True,
    )[:limit]

  def _flatten_tree(
    self, node: QuestionNode
  ) -> list[QuestionNode]:
    flat_list = [node]
    for child in node.children:
      flat_list.extend(self._flatten_tree(child))
    return flat_list

  def cascade_delete(self, node_id: int):
    """
    Delete a node and all its descendants from the database.

    :param node_id: ID of the node to delete
    """
    # First, get all descendant IDs
    descendant_ids = self._get_all_descendants(node_id)

    # Add the node itself to the list of IDs to delete
    ids_to_delete = [node_id] + descendant_ids

    # Delete all nodes in a single transaction
    try:
      self.cursor.execute("BEGIN")
      self.cursor.executemany(
        "DELETE FROM questions WHERE id = ?",
        [(id,) for id in ids_to_delete],
      )
      self.conn.commit()
      print(
        f"Successfully deleted node {node_id} and {len(descendant_ids)} descendants."
      )
    except sqlite3.Error as e:
      self.conn.rollback()
      print(f"An error occurred: {e}")

    # Rebuild the tree after deletion
    self.build_tree()

  def _get_all_descendants(
    self, node_id: int
  ) -> list[int]:
    """
    Recursively get all descendant IDs of a given node.

    :param node_id: ID of the node
    :return: List of descendant IDs
    """
    descendants = []
    self.cursor.execute(
      "SELECT id FROM questions WHERE parent_id = ?",
      (node_id,),
    )
    children = self.cursor.fetchall()

    for child in children:
      child_id = child[0]
      descendants.append(child_id)
      descendants.extend(
        self._get_all_descendants(child_id)
      )

    return descendants

  # ... (rest of the class remains the same)

  def close(self):
    self.conn.close()

  def visualize(self, output_file: str = None):
    """
    Visualize the question tree using Graphviz.

    :param output_file: Optional name of the output file (without extension)
    :return: Bytes object containing the PNG image data
    """
    dot = graphviz.Digraph(comment="Question Tree")
    dot.attr(
      rankdir="TB", size="8,8"
    )  # Top to bottom layout, 8x8 inch size

    def add_node_to_graph(node: QuestionNode):
      # Truncate long questions for better visualization
      short_question = (
        (node.question[:30] + "...")
        if len(node.question) > 30
        else node.question
      )

      # Create label with question, answer (if exists), and priority
      label = f"{short_question}\nID: {node.id}\nPriority: {node.priority}"
      if node.answer:
        short_answer = (
          (node.answer[:20] + "...")
          if len(node.answer) > 20
          else node.answer
        )
        label += f"\nAnswer: {short_answer}"

      # Add node to graph
      dot.node(str(node.id), label, shape="box")

      # Add edges to children
      for child in node.children:
        dot.edge(str(node.id), str(child.id))
        add_node_to_graph(child)

    # Build the tree if it hasn't been built yet
    if not self.root:
      self.build_tree()

    # Calculate priorities
    self.calculate_priorities()

    # Add nodes to the graph
    if self.root:
      add_node_to_graph(self.root)

    # Render the graph to a PNG image
    png_data = dot.pipe(format="png")

    # If output_file is provided, save the image
    if output_file:
      with open(f"{output_file}.png", "wb") as f:
        f.write(png_data)
      print(
        f"Tree visualization saved as {output_file}.png"
      )

    # Return the image data
    return png_data


# Usage example
if __name__ == "__main__":
  tree = QuestionTree("qtree_test.db")

  # Add some questions
  root_id = tree.add_question("What is the main goal?")
  child1_id = tree.add_question(
    "What are the objectives?", parent_id=root_id
  )
  child2_id = tree.add_question(
    "What is the timeline?", parent_id=root_id
  )
  grandchild1_id = tree.add_question(
    "What is objective 1?", parent_id=child1_id
  )
  grandchild2_id = tree.add_question(
    "What is objective 2?", parent_id=child1_id
  )

  # Add a duplicate question
  tree.add_question(
    "What is the timeline?", parent_id=child1_id
  )

  # Build the tree
  tree.build_tree()

  # Calculate priorities
  tree.calculate_priorities()

  # Find duplicate questions
  duplicates = tree.find_duplicate_questions()
  print("Duplicate questions:", duplicates)

  # Get high priority questions
  high_priority = tree.get_high_priority_questions(5)
  print("High priority questions:")
  for node in high_priority:
    print(
      f"ID: {node.id}, Question: {node.question}, Priority: {node.priority}"
    )

  tree.visualize("qtree_before_deletion")

  # Delete a node and its descendants
  tree.cascade_delete(node_id=child1_id)

  tree.visualize("qtree_after_deletion")

  tree.close()
