from unittest.mock import MagicMock, patch

import pytest
from qa_index import QAIndex


@pytest.fixture
def qa_index():
  return QAIndex(
    db_dir="test_db",
    collection_name="test_collection",
  )


def test_init(qa_index):
  assert qa_index.collection_name == "test_collection"
  assert qa_index.client is not None
  assert qa_index.collection is not None


def test_parse_qa_pairs_as_json(qa_index):
  json_str = (
    '[{"q": "Test question?", "a": "Test answer."}]'
  )
  result = qa_index._parse_qa_pairs_as_json(json_str)
  assert result == [
    {"q": "Test question?", "a": "Test answer."}
  ]

  # Test with invalid JSON
  invalid_json = "Not a JSON string"
  result = qa_index._parse_qa_pairs_as_json(
    invalid_json
  )
  assert result == []


def test_generate_qa_pairs(qa_index):
  mock_prompt = MagicMock()
  mock_prompt.call_llm.return_value = (
    '[{"q": "Test question?", "a": "Test answer."}]'
  )

  # Patch the instance attribute
  qa_index.qa_pairs_prompt = mock_prompt

  result = qa_index.generate_qa_pairs(
    "Test input text"
  )
  assert result == [
    {"q": "Test question?", "a": "Test answer."}
  ]
  mock_prompt.call_llm.assert_called_once_with(
    input_text="Test input text"
  )


def test_generate_rewordings(qa_index):
  mock_prompt = MagicMock()
  mock_prompt.call_llm.return_value = (
    "Reworded question 1\nReworded question 2"
  )

  # Patch the instance attribute
  qa_index.rewording_prompt = mock_prompt

  result = qa_index.generate_rewordings(
    "Original question", 2
  )
  assert result == [
    "Original question",
    "Reworded question 1",
    "Reworded question 2",
  ]
  mock_prompt.call_llm.assert_called_once_with(
    question="Original question", num_rewordings=2
  )


def test_add_qa(qa_index):
  with patch.object(
    qa_index.collection, "add"
  ) as mock_add:
    result = qa_index.add_qa(
      "Test question?", "Test answer."
    )
    mock_add.assert_called_once()
    assert result == {"Test question?"}


def test_add_qa_with_rewordings(qa_index):
  with patch.object(
    qa_index, "generate_rewordings"
  ) as mock_reword:
    mock_reword.return_value = [
      "Original",
      "Reworded 1",
      "Reworded 2",
    ]
    with patch.object(
      qa_index.collection, "add"
    ) as mock_add:
      result = qa_index.add_qa(
        "Original", "Answer", num_rewordings=2
      )
      mock_add.assert_called_once()
      assert result == {
        "Original",
        "Reworded 1",
        "Reworded 2",
      }


def test_query(qa_index):
  mock_results = {
    "documents": [["Test question?"]],
    "metadatas": [[{"answer": "Test answer."}]],
    "distances": [[0.1]],
  }
  with patch.object(
    qa_index.collection,
    "query",
    return_value=mock_results,
  ):
    result = qa_index.query("Test question?")
    assert len(result) == 1
    assert result[0]["question"] == "Test question?"
    assert result[0]["answer"] == "Test answer."
    assert result[0]["similarity"] == pytest.approx(
      0.9
    )


def test_update_answer(qa_index):
  mock_query_result = {
    "ids": [["test_id"]],
    "metadatas": [[{"answer": "Old answer"}]],
  }
  with patch.object(
    qa_index.collection,
    "query",
    return_value=mock_query_result,
  ):
    with patch.object(
      qa_index.collection, "update"
    ) as mock_update:
      qa_index.update_answer(
        "Test question?", "New answer"
      )
      mock_update.assert_called_once()


def test_get_all_questions(qa_index):
  mock_result = {"documents": ["Q1", "Q2", "Q3"]}
  with patch.object(
    qa_index.collection,
    "get",
    return_value=mock_result,
  ):
    result = qa_index.get_all_questions()
    assert result == ["Q1", "Q2", "Q3"]


def test_delete_where_simple(qa_index):
  mock_get_result = {"ids": ["id1", "id2"]}
  with patch.object(
    qa_index.collection,
    "get",
    return_value=mock_get_result,
  ) as mock_get:
    with patch.object(
      qa_index.collection, "delete"
    ) as mock_delete:
      num_deleted = qa_index.delete_where(
        {"category": "proverb"}
      )

      mock_get.assert_called_once_with(
        where={"category": "proverb"},
        include=["ids"],
      )
      mock_delete.assert_called_once_with(
        ids=["id1", "id2"]
      )
      assert num_deleted == 2


def test_delete_where_complex(qa_index):
  mock_get_result = {"ids": ["id1", "id2", "id3"]}
  complex_filter = {
    "$and": [
      {"category": "proverb"},
      {"year": {"$gte": 2019}},
      {
        "$or": [
          {"author": "John"},
          {"author": "Sarah"},
        ]
      },
    ]
  }
  with patch.object(
    qa_index.collection,
    "get",
    return_value=mock_get_result,
  ) as mock_get:
    with patch.object(
      qa_index.collection, "delete"
    ) as mock_delete:
      num_deleted = qa_index.delete_where(
        complex_filter
      )

      mock_get.assert_called_once_with(
        where=complex_filter, include=["ids"]
      )
      mock_delete.assert_called_once_with(
        ids=["id1", "id2", "id3"]
      )
      assert num_deleted == 3


def test_delete_where_no_matches(qa_index):
  mock_get_result = {"ids": []}
  with patch.object(
    qa_index.collection,
    "get",
    return_value=mock_get_result,
  ) as mock_get:
    with patch.object(
      qa_index.collection, "delete"
    ) as mock_delete:
      num_deleted = qa_index.delete_where(
        {"category": "nonexistent"}
      )

      mock_get.assert_called_once_with(
        where={"category": "nonexistent"},
        include=["ids"],
      )
      mock_delete.assert_not_called()
      assert num_deleted == 0


def test_delete_where_empty_filter(qa_index):
  with pytest.raises(
    ValueError,
    match="Where filter cannot be empty",
  ):
    qa_index.delete_where({})


def test_clear(qa_index):
  with patch.object(
    qa_index.collection, "delete"
  ) as mock_delete:
    with patch.object(
      qa_index.collection,
      "get",
      return_value={"ids": ["id1", "id2"]},
    ):
      qa_index.clear()
      mock_delete.assert_called_once_with(
        ids=["id1", "id2"]
      )


def test_reset_database(qa_index):
  with patch.object(
    qa_index.client, "delete_collection"
  ) as mock_delete:
    with patch.object(
      qa_index.client, "create_collection"
    ) as mock_create:
      qa_index.reset_database()
      mock_delete.assert_called_once_with(
        "test_collection"
      )
      mock_create.assert_called_once()


def test_add_tree_question(qa_index):
  with patch.object(qa_index, "add_qa") as mock_add_qa:
    qa_index.add_tree_question(
      "Tree question?", 1, "Tree answer"
    )
    mock_add_qa.assert_called_once_with(
      "Tree question?",
      "Tree answer",
      metadata={"tree_id": 1, "from_tree": True},
    )


def test_get_tree_questions(qa_index):
  mock_results = [
    {"question": "Tree Q?", "answer": "Tree A"}
  ]
  with patch.object(
    qa_index, "query", return_value=mock_results
  ) as mock_query:
    result = qa_index.get_tree_questions()
    mock_query.assert_called_once_with(
      "",
      metadata_filter={"from_tree": True},
      n_results=qa_index.collection.count(),
    )
    assert result == mock_results


def test_update_tree_question(qa_index):
  mock_query_result = [{"question": "Tree Q?"}]
  with patch.object(
    qa_index,
    "query",
    return_value=mock_query_result,
  ) as mock_query:
    with patch.object(
      qa_index, "update_answer"
    ) as mock_update:
      qa_index.update_tree_question(
        1, "Updated answer"
      )
      mock_query.assert_called_once_with(
        "",
        metadata_filter={"tree_id": 1},
        n_results=1,
      )
      mock_update.assert_called_once_with(
        "Tree Q?", "Updated answer"
      )


if __name__ == "__main__":
  pytest.main()
