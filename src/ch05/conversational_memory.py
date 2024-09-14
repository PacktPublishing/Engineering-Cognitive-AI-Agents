"""
Conversational Memory Module

This module implements a sophisticated conversational memory system for AI agents,
providing mechanisms to store, retrieve, and manage conversation history. It offers
both short-term and long-term memory capabilities, enabling context-aware interactions.

Main components:
1. ConversationMessage: Represents individual messages in a conversation.
2. Conversation: Represents a complete conversation, including its messages and summary.
3. ConversationalMemory: The core class managing conversation storage and retrieval.

Key functionalities:
- Creating and managing conversations
- Adding messages to conversations
- Generating and updating conversation summaries
- Retrieving recent messages from a conversation
- Finding relevant messages based on context
- Persisting conversations in SQLite database
- Integrating with a Knowledge Management System (KMS) for advanced retrieval

The module uses SQLite for persistent storage and integrates with an external
Knowledge Management System for enhanced information retrieval and context understanding.

Usage:
Initialize ConversationalMemory with a KMS instance and database path, then use its
methods to manage conversations and messages throughout an AI agent's interactions.

Example:
    cm = ConversationalMemory(kms_instance, "path/to/database.db")
    conversation_id = cm.create_conversation()
    await cm.add_message(conversation_id, ConversationMessage(...))
    relevant_messages = await cm.find_relevant_messages("context", conversation_id)

Note: This module is designed for asynchronous operation, particularly in its
interaction with the KMS and for long-running operations like summarization.
"""

import json
import sqlite3
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, cast
from uuid import UUID, uuid4

from dotenv import load_dotenv
from loguru import logger

from ch03.llm import Message
from ch03.prompt import load_prompt
from ch04.kms import (
  Content,
  IngestionReport,
  KnowledgeManagementSystem,
)

#

load_dotenv()

MAX_MESSAGE_HISTORY = int(
  os.getenv("MAX_MESSAGE_HISTORY", "10")
)

SUMMARIZE_CONVERSATION_PROMPT = load_prompt(
  "ch05/conversation/summarize"
)


class ConversationMessage(Message):
  id: UUID
  conversation_id: UUID
  timestamp: datetime
  metadata: dict[str, Any] | None


@dataclass
class Conversation:
  id: UUID
  summary: str = ""
  messages: list[ConversationMessage] = field(
    default_factory=list
  )


class ConversationalMemory:
  def __init__(
    self,
    kms: KnowledgeManagementSystem,
    db_path: str,
    max_message_history: int = MAX_MESSAGE_HISTORY,
  ):
    self.kms = kms
    self.db_path = db_path
    self.conn = sqlite3.connect(db_path)
    self.conn.row_factory = sqlite3.Row
    self._create_tables()
    self.active_conversations: dict[
      UUID, Conversation
    ] = {}
    self.max_message_history = max_message_history

  def _create_tables(self) -> None:
    with self.conn:
      self.conn.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    summary TEXT
                )
            """)
      self.conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    conversation_id TEXT,
                    role TEXT,
                    content TEXT,
                    metadata TEXT,
                    timestamp TEXT,
                    FOREIGN KEY(conversation_id) REFERENCES conversations(id)
                )
            """)

  def create_conversation(self) -> UUID:
    conversation_id = uuid4()
    with self.conn:
      self.conn.execute(
        "INSERT INTO conversations (id, summary) VALUES (?, ?)",
        (str(conversation_id), ""),
      )
    self.active_conversations[conversation_id] = (
      Conversation(
        id=conversation_id,
        summary="",
        messages=[],
      )
    )
    return conversation_id

  async def add_message(
    self,
    conversation_id: UUID,
    message: ConversationMessage,
    bypass_ingestion: bool = False,
  ) -> IngestionReport | None:
    logger.error(
      f"Message.content: {message["content"]}"
    )
    if (
      conversation_id not in self.active_conversations
    ):
      raise ValueError(
        f"Conversation {conversation_id} not found"
      )

    conversation = self.active_conversations[
      conversation_id
    ]
    conversation.messages.append(message)

    # Update summary if necessary
    #
    # We have to account for the system message and any
    # previous summary that may have been added.
    has_previous_summary = bool(conversation.summary)
    message_offset = 1 + (
      1 if has_previous_summary else 0
    )
    num_messages = len(conversation.messages)
    # Don't include the system message and any previous
    # summary in the message count
    num_messages -= message_offset
    if num_messages % self.max_message_history == 0:
      logger.info(
        f"Updating summary for conversation {conversation_id}"
      )
      conversation.summary = await self.summarize_messages(
        conversation_id=conversation_id,
        messages=conversation.messages[
          message_offset:
        ],  # skip the system message and any previous summary, if any
        previous_summary=conversation.summary,
      )

    # Store the message in SQLite
    timestamp = (
      message["timestamp"].isoformat()
      if "timestamp" in message
      else datetime.now().isoformat()
    )
    metadata_json = (
      json.dumps(message["metadata"])
      if "metadata" in message
      else None
    )
    with self.conn:
      self.conn.execute(
        "INSERT INTO messages (id, conversation_id, role, content, metadata, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
        (
          str(message["id"]),
          str(conversation_id),
          message["role"],
          message["content"],
          metadata_json,
          timestamp,
        ),
      )
    if bypass_ingestion:
      return None

    # Index the message in KMS
    metadata_dict = cast(
      dict[str, Any],
      message["metadata"]
      if "metadata" in message
      else {},
    )
    content = Content(
      id=str(message["id"]),
      type="message",
      content=message["content"],
      metadata={
        "conversation_id": str(
          message["conversation_id"]
        ),
        "role": message["role"],
        "timestamp": timestamp,
        **metadata_dict,
      },
    )
    return await self.kms.ingest_content(content)

  def get_last_n_messages(
    self,
    conversation_id: UUID,
    n: int | None = None,
  ) -> list[ConversationMessage]:
    messages: list[ConversationMessage] = []

    if n is None:
      n = self.max_message_history

    # Get the system message
    with self.conn:
      system_message = self.conn.execute(
        "SELECT * FROM messages WHERE conversation_id = ? AND role = 'system' ORDER BY timestamp ASC LIMIT 1",
        (str(conversation_id),),
      ).fetchone()

    if system_message:
      messages.append(
        self._row_to_message(system_message)
      )

    # Get the last n messages
    with self.conn:
      results = self.conn.execute(
        "SELECT * FROM messages WHERE conversation_id = ? AND role != 'system' ORDER BY timestamp DESC LIMIT ?",
        (str(conversation_id), n),
      ).fetchall()

    # Inject a summary if we have more than n messages
    if len(results) == n:
      summary = self.get_conversation_summary(
        conversation_id
      )
      summary_message = cast(
        ConversationMessage,
        {
          "id": uuid4(),
          "conversation_id": conversation_id,
          "role": "assistant",
          "content": f"Summary of conversation so far:\n\n{summary}",
          "timestamp": datetime.now(),
          "metadata": None,
        },
      )
      messages.append(summary_message)

    # Add the last n messages in reverse order (oldest first)
    for row in reversed(results):
      messages.append(self._row_to_message(row))

    return messages

  def _row_to_message(
    self, row: sqlite3.Row
  ) -> ConversationMessage:
    return cast(
      ConversationMessage,
      {
        "id": UUID(row["id"]),
        "conversation_id": UUID(
          row["conversation_id"]
        ),
        "role": row["role"],
        "content": row["content"],
        "metadata": json.loads(row["metadata"])
        if row["metadata"]
        else None,
        "timestamp": datetime.fromisoformat(
          row["timestamp"]
        ),
      },
    )

  async def summarize_messages(
    self,
    conversation_id: UUID,
    messages: Iterable[ConversationMessage],
    previous_summary: str | None = None,
  ) -> str:
    summary = str(
      await SUMMARIZE_CONVERSATION_PROMPT.call_llm(
        previous_summary=previous_summary,
        messages=messages,
      )
    )
    # Update the conversation summary in SQLite
    with self.conn:
      self.conn.execute(
        "UPDATE conversations SET summary = ? WHERE id = ?",
        (summary, str(conversation_id)),
      )
    return summary

  async def find_relevant_messages(
    self,
    context: str,
    conversation_id: UUID | None = None,
  ) -> Iterable[ConversationMessage]:
    metadata_filter = (
      {"conversation_id": str(conversation_id)}
      if conversation_id
      else None
    )
    results = await self.kms.retrieve_content(
      query=context,
      metadata_filter=metadata_filter,
      num_rewordings=1,
    )
    print(
      f"Results: {json.dumps(results, indent=2, default=str)}"
    )

    relevant_messages: list[ConversationMessage] = []
    for result in results:
      message = cast(
        ConversationMessage,
        {
          "id": UUID(result.id),
          "conversation_id": UUID(
            result.metadata["conversation_id"]
          ),
          "role": result.metadata["role"],
          "content": result.content,
          "timestamp": datetime.fromisoformat(
            result.metadata["timestamp"]
          ),
          "metadata": {
            k: v
            for k, v in result.metadata.items()
            if k
            not in {
              "conversation_id",
              "role",
              "timestamp",
            }
          },
        },
      )
      relevant_messages.append(message)

    return relevant_messages

  def get_conversation_summary(
    self,
    conversation_id: UUID,
  ) -> str:
    if (
      conversation_id not in self.active_conversations
    ):
      raise ValueError(
        f"Conversation {conversation_id} not found"
      )

    return self.active_conversations[
      conversation_id
    ].summary

  async def close_conversation(
    self,
    conversation_id: UUID,
  ) -> None:
    if (
      conversation_id not in self.active_conversations
    ):
      raise ValueError(
        f"Conversation {conversation_id} not found"
      )

    # Perform any necessary cleanup or final processing
    conversation = self.active_conversations[
      conversation_id
    ]
    await self.summarize_messages(
      conversation_id=conversation_id,
      messages=conversation.messages,
      previous_summary=conversation.summary,
    )

    # Remove the conversation from active conversations
    del self.active_conversations[conversation_id]
