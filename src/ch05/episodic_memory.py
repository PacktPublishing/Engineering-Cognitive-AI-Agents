# src/ch05/episodic_memory.py
"""
Episodic memory
"""

import json
import sqlite3
from dataclasses import dataclass
from typing import TypedDict
from uuid import uuid4

from loguru import logger

from ch03.llm import Message
from ch03.prompt import load_prompt
from ch04.kms import (
  Content,
  IngestionReport,
  KnowledgeManagementSystem,
  RetrievedContent,
)
from ch05.conversational_memory import (
  ConversationalMemory,
  ConversationMessage,
)

#

EPISODE_BOUNDARY_DETECTION_PROMPT = load_prompt(
  "ch05/memory/episode_boundary_detection"
)

EPISODE_REFLECTION_PROMPT = load_prompt(
  "ch05/memory/episode_reflection"
)

#


class EpisodeBoundaryDetection(TypedDict):
  is_new_episode: bool
  rationale: str


@dataclass
class EpisodeReport:
  boundary_detection: EpisodeBoundaryDetection
  reflection: str | None = None
  ingestion_report: IngestionReport | None = None


@dataclass
class Episode:
  id: str
  conversation_id: str
  start_message_id: str
  end_message_id: str
  reflection: str

  @classmethod
  def from_db_row(cls, row: sqlite3.Row) -> "Episode":
    return cls(
      id=row["id"],
      conversation_id=row["conversation_id"],
      start_message_id=row["start_message_id"],
      end_message_id=row["end_message_id"],
      reflection=row["reflection"],
    )


class EpisodicMemory:
  first_episode_message: ConversationMessage | None

  def __init__(
    self,
    kms: KnowledgeManagementSystem,
    cm: ConversationalMemory,
    db_path: str,
  ):
    self.kms = kms
    self.cm = cm
    self.db_path = db_path
    self.conn = sqlite3.connect(db_path)
    self.conn.row_factory = sqlite3.Row
    self._create_tables()
    self.first_episode_message = None

  def _create_tables(self) -> None:
    with self.conn:
      self.conn.execute("""
                CREATE TABLE IF NOT EXISTS episodes (
                    id TEXT PRIMARY KEY,
                    conversation_id TEXT,
                    start_message_id TEXT,
                    end_message_id TEXT,
                    reflection TEXT,
                    FOREIGN KEY(conversation_id) REFERENCES conversations(id),
                    FOREIGN KEY(start_message_id) REFERENCES messages(id),
                    FOREIGN KEY(end_message_id) REFERENCES messages(id)
                )
            """)

  async def process_episode(
    self,
    user_message: ConversationMessage,
    history: list[Message],
    whiteboard: str,
  ) -> EpisodeReport:
    """
    Process a new user message to determine if it starts a new episode and generate a report.

    Parameters
    ----------
    user_message : ConversationMessage
        The latest message from the user.
    history : list[Message]
        The conversation history.
    whiteboard : str
        The current state of the whiteboard.

    Returns
    -------
    EpisodeReport
        A report containing boundary detection results and, if applicable, episode reflection.

    Notes
    -----
    This method performs the following steps:
    1. Handles the first message of a conversation if applicable.
    2. Detects if the new message starts a new episode.
    3. If a new episode is detected:
       - Retrieves messages from the current episode.
       - Generates a reflection on the episode.
       - Stores the episode in the database.
       - Updates the first message of the new episode.
    4. Returns a report with boundary detection and reflection (if applicable).
    """
    if self.first_episode_message is None:
      return self._handle_first_message(user_message)

    boundary_detection = (
      await self._detect_episode_boundary(
        history, whiteboard
      )
    )

    if not boundary_detection["is_new_episode"]:
      return EpisodeReport(
        boundary_detection=boundary_detection
      )

    episode_messages = self._get_episode_messages()
    reflection = await self._create_reflection(
      episode_messages, whiteboard
    )
    logger.error(f"reflection:\n\n{reflection}")
    ingestion_report = (
      await self._store_and_index_episode(
        user_message, reflection
      )
    )

    self.first_episode_message = user_message

    return EpisodeReport(
      boundary_detection=boundary_detection,
      reflection=reflection,
      ingestion_report=ingestion_report,
    )

  def get_episodes(
    self,
    conversation_id: str,
  ) -> list[Episode]:
    with self.conn:
      cursor = self.conn.execute(
        """
        SELECT * FROM episodes
        WHERE conversation_id = ?
        ORDER BY start_message_id
      """,
        (conversation_id,),
      )
      return [
        Episode.from_db_row(row)
        for row in cursor.fetchall()
      ]

  def get_episode(
    self,
    episode_id: str,
  ) -> Episode | None:
    with self.conn:
      cursor = self.conn.execute(
        """
        SELECT * FROM episodes
        WHERE id = ?
      """,
        (episode_id,),
      )
      row = cursor.fetchone()
      return Episode.from_db_row(row) if row else None

  async def query_episodes(
    self,
    query: str,
    n_results: int = 5,
  ) -> list[RetrievedContent]:
    return await self.kms.retrieve_content(
      query=query,
      n_results=n_results,
      metadata_filter={"type": "episode"},
    )

  async def get_related_episodes(
    self,
    episode_id: str,
    n_results: int = 5,
  ) -> list[Episode]:
    # First, get the episode
    episode = self.get_episode(episode_id)
    if not episode:
      return []

    # Use the episode's reflection to find related content
    related_content = await self.kms.retrieve_content(
      query=episode.reflection,
      n_results=n_results
      + 1,  # We add 1 because the episode itself might be returned
      metadata_filter={"type": "episode"},
    )

    # Convert related content to episodes, excluding the original episode
    related_episodes: list[Episode] = []
    for content in related_content:
      if content.id != episode_id:
        related_episode = self.get_episode(content.id)
        if related_episode:
          related_episodes.append(related_episode)

    return related_episodes

  def _handle_first_message(
    self,
    user_message: ConversationMessage,
  ) -> EpisodeReport:
    self.first_episode_message = user_message
    return EpisodeReport(
      boundary_detection=EpisodeBoundaryDetection(
        is_new_episode=True,
        rationale="This is the first message in the conversation",
      ),
    )

  async def _detect_episode_boundary(
    self,
    history: list[Message],
    whiteboard: str,
  ) -> EpisodeBoundaryDetection:
    episode_boundary_detection_json = str(
      await EPISODE_BOUNDARY_DETECTION_PROMPT.call_llm(
        message_history=history,
        whiteboard=whiteboard,
      )
    )
    logger.error(
      f"episode_boundary_detection_json:\n\n{episode_boundary_detection_json}"
    )
    return json.loads(episode_boundary_detection_json)

  def _get_episode_messages(
    self,
  ) -> list[ConversationMessage]:
    assert self.first_episode_message is not None
    return self.cm.get_messages_since(
      conversation_id=self.first_episode_message[
        "conversation_id"
      ],
      since_message_id=self.first_episode_message[
        "id"
      ],
    )

  async def _create_reflection(
    self,
    episode_messages: list[ConversationMessage],
    whiteboard: str,
  ) -> str:
    messages_for_reflection = [
      {
        (
          "user" if msg["role"] == "user" else "me"
        ): str(msg["content"])
      }
      for msg in episode_messages
    ]
    return str(
      await EPISODE_REFLECTION_PROMPT.call_llm(
        episode_messages=messages_for_reflection,
        whiteboard=whiteboard,
      )
    )

  async def _store_and_index_episode(
    self,
    user_message: ConversationMessage,
    reflection: str,
  ) -> IngestionReport:
    assert self.first_episode_message is not None
    episode_id = str(uuid4())
    with self.conn:
      self.conn.execute(
        """
        INSERT INTO episodes (
          id, conversation_id, start_message_id, end_message_id, reflection
        ) VALUES (?, ?, ?, ?, ?)
        """,
        (
          episode_id,
          str(
            self.first_episode_message[
              "conversation_id"
            ]
          ),
          str(self.first_episode_message["id"]),
          str(user_message["id"]),
          reflection,
        ),
      )

    return await self.kms.ingest_content(
      content=Content(
        id=episode_id,
        type="episode",
        content=reflection,
        metadata={
          "conversation_id": str(
            self.first_episode_message[
              "conversation_id"
            ]
          ),
        },
      )
    )
