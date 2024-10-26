import json
import os
from typing import Any, Optional, Set, TypedDict

import chromadb
from chromadb.utils import embedding_functions
from dotenv import load_dotenv
from loguru import logger

from ch03.prompt import load_prompt

#

_ = load_dotenv()

DB_DIR = os.getenv("DB_DIR", "db")
DEFAULT_COLLECTION_NAME = os.getenv(
  "DEFAULT_COLLECTION_NAME", "qa_index"
)
EMBEDDING_MODEL_NAME = os.getenv(
  "EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2"
)

REWORDING_PROMPT = load_prompt(
  "ch04/knowledge/reword_question"
)
QA_PAIRS_PROMPT = load_prompt(
  "ch04/knowledge/qa_pairs"
)

#


class QAPair(TypedDict):
  q: str
  a: str


#


class QAIndex:
  def __init__(
    self,
    db_dir: str = DB_DIR,
    collection_name: str = DEFAULT_COLLECTION_NAME,
  ) -> None:
    self.client = chromadb.PersistentClient(
      path=db_dir
    )
    self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
      model_name=EMBEDDING_MODEL_NAME
    )
    self.collection_name = collection_name
    self.collection = (
      self.client.get_or_create_collection(
        name=collection_name,
        embedding_function=self.embedding_function,
      )
    )

    logger.info(
      f"QuestionAnswerKB initialized for collection '{collection_name}'."
    )

  async def generate_qa_pairs(
    self, input_text: str
  ) -> list[QAPair]:
    try:
      qa_pairs_json = str(
        await QA_PAIRS_PROMPT.call_llm(
          input_text=input_text
        )
      )
      qa_pairs: list[QAPair] = json.loads(
        qa_pairs_json
      )["qa_pairs"]
      return qa_pairs

    except Exception as e:
      logger.error(
        f"Error generating QA pairs: {str(e)}"
      )
      return []

  async def generate_rewordings(
    self, question: str, num_rewordings: int
  ) -> list[str]:
    if num_rewordings == 0:
      return [question]

    rewordings_json = str(
      await REWORDING_PROMPT.call_llm(
        question=question,
        num_rewordings=num_rewordings,
      )
    )
    assert isinstance(rewordings_json, str)
    rewordings = json.loads(rewordings_json)[
      "reworded_questions"
    ]
    questions = [question] + rewordings
    questions = [q.strip() for q in questions]
    for i, q in enumerate(questions):
      logger.trace(f"Reworded question {i+1}: {q}")
    return questions

  async def add_qa(
    self,
    question: str | list[str],
    answer: Any = None,
    metadata: dict[str, Any] | None = None,
    num_rewordings: int = 0,
  ) -> Set[str]:
    """
    Add a question-answer pair to the KB, including
    rewordings if specified.

    Parameters
    ----------
    question : str or list of str
        The question string or list of question
        strings.
    answer : Any
        The answer (converted to string).
    metadata : dict of {str: Any} or None, optional
        Optional metadata about the QA pair.
        Default is None.
    num_rewordings : int, optional
        Number of question rewordings to generate
        and index. Default is 0.

    Returns
    -------
    set of str
        A set of all questions (original and rewordings) that were indexed.

    """
    metadata = metadata or {}
    metadata["answer"] = answer if answer else ""

    if (
      isinstance(question, str) and num_rewordings > 0
    ):
      questions = await self.generate_rewordings(
        question, num_rewordings
      )
    elif (
      isinstance(question, list) and num_rewordings > 0
    ):
      questions = question
    else:
      questions = [question]

    documents = []
    metadatas = []
    ids = []

    for i, q in enumerate(questions):
      logger.trace(f"Adding question: {q}")
      documents.append(q)
      metadatas.append(metadata.copy())
      ids.append(f"qa_{self.collection.count()}_{i}")

    self.collection.add(
      documents=documents,
      metadatas=metadatas,
      ids=ids,
    )

    return set(questions)

  async def query(
    self,
    question: str | list[str],
    n_results: int = 5,
    metadata_filter: Optional[dict[str, Any]] = None,
    num_rewordings: int = 0,
  ) -> list[dict[str, Any]]:
    """
    Query the KB for answers to a given question, with optional metadata
    filtering and question rewordings.

    Parameters
    ----------
    question : str or list of str
        The question string or list of question strings.
    n_results : int, optional
        Number of results to return (default is 5).
    metadata_filter : dict, optional
        Optional metadata filter (default is None).
    num_rewordings : int, optional
        Number of question rewordings to generate and query (default is 0).

    Returns
    -------
    list of dict
        A list of dictionaries containing the question, answer, metadata,
        and similarity score for each result.
    """
    if (
      isinstance(question, str) and num_rewordings > 0
    ):
      questions = await self.generate_rewordings(
        question, num_rewordings
      )
    elif (
      isinstance(question, list) and num_rewordings > 0
    ):
      questions = question
    else:
      questions = [question]

    all_results = []
    for q in questions:
      logger.trace(f"Querying question: {q}")
      query_params = {
        "query_texts": [q],
        "n_results": n_results,
        "include": [
          "documents",
          "metadatas",
          "distances",
        ],
      }

      if metadata_filter:
        query_params["where"] = metadata_filter

      results = self.collection.query(**query_params)

      for doc, metadata, distance in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
      ):
        all_results.append(
          {
            "question": doc,
            "answer": metadata["answer"],
            "metadata": {
              k: v
              for k, v in metadata.items()
              if k != "answer"
            },
            "similarity": 1 - distance,
          }
        )

    # Deduplicate results based on the answer
    seen_answers = set()
    unique_results = []
    for result in all_results:
      if result["answer"] not in seen_answers:
        seen_answers.add(result["answer"])
        unique_results.append(result)

    # Sort by similarity and return top n_results
    final_results = sorted(
      unique_results,
      key=lambda x: x["similarity"],
      reverse=True,
    )[:n_results]
    for i, result in enumerate(final_results):
      logger.trace(f"Query result {i+1}: {result}")
    return final_results

  def update_answer(
    self,
    question: str,
    new_answer: Any,
  ) -> None:
    """
    Update the answer to a question in the KB.

    Parameters
    ----------
    question : str
        The question string.
    new_answer : Any
        The new answer (converted to string).

    Raises
    ------
    ValueError
        If the question is not found in the KB.
    """

    results = self.collection.query(
      query_texts=[question],
      n_results=1,
      include=["metadatas"],
    )

    if results["ids"][0]:
      id = results["ids"][0][0]
      metadata = results["metadatas"][0][0]
      metadata["answer"] = str(new_answer)
      self.collection.update(
        ids=[id],
        documents=[question],
        metadatas=[metadata],
      )
    else:
      raise ValueError("Question not found in KB")
    logger.info(
      f"Answer to question '{question}' has been updated."
    )

  def get_all_questions(self) -> list[str]:
    """
    Get all questions in the KB.

    Returns:
        list[str]: A list of all questions in the KB.
    """
    documents = self.collection.get()["documents"]
    if documents:
      return [str(doc) for doc in documents]
    return []

  def clear(self):
    if self.collection.count() > 0:
      self.collection.delete(where={})

  def delete_where(
    self, where_filter: dict[str, Any]
  ) -> int:
    results = self.collection.get(
      where=where_filter, include=["metadatas"]
    )
    if not results["ids"]:
      return 0
    self.collection.delete(ids=results["ids"])
    return len(results["ids"])

  def reset_database(self) -> None:
    """
    Drop the entire collection and recreate it, effectively resetting the
    database.
    """
    try:
      # Delete the existing collection
      self.client.delete_collection(
        self.collection_name
      )
      logger.trace(
        f"Collection '{self.collection_name}' has been deleted."
      )
    except ValueError:
      # If the collection doesn't exist, a ValueError is raised
      logger.trace(
        f"Collection '{self.collection_name}' did not exist."
      )

    # Recreate the collection
    self.collection = self.client.create_collection(
      name=self.collection_name,
      embedding_function=self.embedding_function,
    )
    logger.trace(
      f"Collection '{self.collection_name}' has been recreated."
    )

  async def add_tree_question(
    self,
    question: str,
    tree_id: int,
    answer: Optional[str] = None,
  ):
    metadata = {
      "tree_id": tree_id,
      "from_tree": True,
    }
    await self.add_qa(
      question, answer, metadata=metadata
    )

  async def get_tree_questions(
    self,
  ) -> list[dict[str, Any]]:
    return await self.query(
      "",
      metadata_filter={"from_tree": True},
      n_results=self.collection.count(),
    )

  async def update_tree_question(
    self, tree_id: int, answer: str
  ):
    results = await self.query(
      "",
      metadata_filter={"tree_id": tree_id},
      n_results=1,
    )
    if results:
      question = results[0]["question"]
      self.update_answer(question, answer)
