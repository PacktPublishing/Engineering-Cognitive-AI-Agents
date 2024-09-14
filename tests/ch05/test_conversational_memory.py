import asyncio
import os
import sqlite3
import uuid
from uuid import UUID

import pytest

from ch04.kms import KnowledgeManagementSystem
from ch05.conversational_memory import (
  ConversationalMemory,
  ConversationMessage,
)


@pytest.fixture(scope="module")
def cm():
  # Setup
  test_db_dir = "test_db"
  os.makedirs(test_db_dir, exist_ok=True)
  kms = KnowledgeManagementSystem(db_dir=test_db_dir)
  cm = ConversationalMemory(
    kms, os.path.join(test_db_dir, "conversations.db")
  )

  def reset_state():
    cm.active_conversations.clear()
    cm.conn.execute("DELETE FROM conversations")
    cm.conn.execute("DELETE FROM messages")
    cm.conn.commit()

  cm.reset_state = reset_state

  yield cm

  # Teardown
  cm.reset_state()
  cm.conn.close()
  for root, dirs, files in os.walk(
    test_db_dir, topdown=False
  ):
    for name in files:
      os.remove(os.path.join(root, name))
    for name in dirs:
      os.rmdir(os.path.join(root, name))
  os.rmdir(test_db_dir)


@pytest.fixture(autouse=True)
def reset_cm_state(cm):
  cm.reset_state()


@pytest.mark.asyncio
async def test_create_conversation(cm):
  conversation_id = cm.create_conversation()
  assert isinstance(conversation_id, UUID)
  assert conversation_id in cm.active_conversations


@pytest.mark.asyncio
async def test_add_message(cm):
  conversation_id = cm.create_conversation()
  message = ConversationMessage(
    id=UUID("12345678-1234-5678-1234-567812345678"),
    conversation_id=conversation_id,
    name="user",
    content="Hello, how are you?",
    metadata={"timestamp": "2023-04-01T12:00:00Z"},
  )
  report = await cm.add_message(
    conversation_id, message
  )

  print(f"Report: {report.summary()}")

  assert report.content_id == str(message.id)
  assert report.content_type == "message"
  assert (
    len(
      cm.active_conversations[conversation_id].messages
    )
    == 1
  )


@pytest.mark.asyncio
async def test_get_last_n_messages(cm):
  conversation_id = cm.create_conversation()
  for i in range(5):
    message = ConversationMessage(
      id=UUID(
        f"12345678-1234-5678-1234-56781234567{i}"
      ),
      conversation_id=conversation_id,
      name="user",
      content=f"Message {i}",
      metadata={},
    )
    await cm.add_message(conversation_id, message)

  last_messages = list(
    cm.get_last_n_messages(conversation_id, 3)
  )
  assert len(last_messages) == 3
  assert [m.content for m in last_messages] == [
    "Message 2",
    "Message 3",
    "Message 4",
  ]


@pytest.mark.asyncio
async def test_summarize_messages(cm):
  conversation_id = cm.create_conversation()
  messages = [
    ConversationMessage(
      generate_unique_id(),
      conversation_id,
      "user",
      f"Message {i}",
      {},
    )
    for i in range(3)
  ]
  for message in messages:
    await cm.add_message(conversation_id, message)

  summary = await cm.summarize_messages(messages)
  assert isinstance(summary, str)
  assert len(summary) > 0


@pytest.mark.asyncio
async def test_find_relevant_messages(cm):
  conversation_id = cm.create_conversation()
  messages = [
    ConversationMessage(
      generate_unique_id(),
      conversation_id,
      "user",
      f"Message about topic {i}",
      {},
    )
    for i in range(5)
  ]
  for message in messages:
    report = await cm.add_message(
      conversation_id, message
    )
    print(f"Report: {report.summary()}")

  relevant_messages = await cm.find_relevant_messages(
    "topic 2", conversation_id
  )

  # Debug print statements
  print(f"All messages: {messages}")
  print(
    f"Relevant messages: {list(relevant_messages)}"
  )

  assert len(list(relevant_messages)) > 0


def test_get_conversation_summary(cm):
  conversation_id = cm.create_conversation()
  # Ensure the conversation is added to active_conversations
  assert conversation_id in cm.active_conversations
  cm.active_conversations[
    conversation_id
  ].summary = "Test summary"

  summary = cm.get_conversation_summary(
    conversation_id
  )
  assert summary == "Test summary"


@pytest.mark.asyncio
async def test_close_conversation(cm):
  conversation_id = cm.create_conversation()
  message = ConversationMessage(
    generate_unique_id(),
    conversation_id,
    "user",
    "Test message",
    {},
  )
  await cm.add_message(conversation_id, message)

  await cm.close_conversation(conversation_id)
  assert conversation_id not in cm.active_conversations

  # Check if the conversation is stored in the database
  with cm.conn:
    result = cm.conn.execute(
      "SELECT * FROM conversations WHERE id = ?",
      (str(conversation_id),),
    ).fetchone()
  assert result is not None
  assert result["summary"] != ""


def test_error_handling(cm):
  non_existent_id = UUID(
    "00000000-0000-0000-0000-000000000000"
  )

  with pytest.raises(ValueError):
    cm.get_conversation_summary(non_existent_id)

  with pytest.raises(ValueError):
    asyncio.run(cm.close_conversation(non_existent_id))

  with pytest.raises(ValueError):
    asyncio.run(
      cm.add_message(
        non_existent_id,
        ConversationMessage(
          UUID("12345678-1234-5678-1234-567812345678"),
          non_existent_id,
          "user",
          "Test",
          {},
        ),
      )
    )


@pytest.mark.asyncio
async def test_summary_interval(cm):
  conversation_id = cm.create_conversation()
  cm.summary_interval = 3

  for i in range(5):
    message = ConversationMessage(
      generate_unique_id(),
      conversation_id,
      "user",
      f"Message {i}",
      {},
    )
    await cm.add_message(conversation_id, message)

  conversation = cm.active_conversations[
    conversation_id
  ]
  assert conversation.summary != ""
  assert "Message 2" in conversation.summary


@pytest.mark.asyncio
async def test_multiple_conversations(cm):
  conv_id1 = cm.create_conversation()
  conv_id2 = cm.create_conversation()

  await cm.add_message(
    conv_id1,
    ConversationMessage(
      generate_unique_id(),
      conv_id1,
      "user",
      "Message in conv 1",
      {},
    ),
  )
  await cm.add_message(
    conv_id2,
    ConversationMessage(
      generate_unique_id(),
      conv_id2,
      "user",
      "Message in conv 2",
      {},
    ),
  )

  assert len(cm.active_conversations) == 2
  assert (
    len(cm.active_conversations[conv_id1].messages)
    == 1
  )
  assert (
    len(cm.active_conversations[conv_id2].messages)
    == 1
  )


@pytest.mark.asyncio
async def test_conversation_persistence(cm):
  conv_id = cm.create_conversation()
  await cm.add_message(
    conv_id,
    ConversationMessage(
      generate_unique_id(),
      conv_id,
      "user",
      "Test message",
      {},
    ),
  )
  await cm.close_conversation(conv_id)

  # Simulate restarting the ConversationalMemory
  cm.conn.close()
  cm.conn = sqlite3.connect(cm.db_path)
  cm.conn.row_factory = sqlite3.Row  # Add this line
  # Check if we can retrieve the closed conversation
  with cm.conn:
    result = cm.conn.execute(
      "SELECT * FROM conversations WHERE id = ?",
      (str(conv_id),),
    ).fetchone()
  assert result is not None
  assert result["summary"] != ""


def generate_unique_id():
  return uuid.uuid4()
