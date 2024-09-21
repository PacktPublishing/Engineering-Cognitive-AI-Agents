# src/ch05/whiteboard.py
"""
Short-term memory Whiteboard
"""

import os
import sqlite3
from collections.abc import Iterable
from typing import Any, cast
from uuid import UUID

from dotenv import load_dotenv

from ch03.llm import Message, call_llm
from ch03.prompt import load_prompt

#

_ = load_dotenv()

PROMPT_DIR = os.getenv("PROMPT_DIR", "prompts")

UPDATE_WHITEBOARD_PROMPT = load_prompt(
  "ch05/memory/update_whiteboard"
)

with open(
  os.path.join(
    PROMPT_DIR,
    "ch05/memory/whiteboard_template.md",
  ),
  "r",
  encoding="utf-8",
) as f:
  WHITEBOARD_TEMPLATE = f.read()


class Whiteboard:
  def __init__(
    self,
    db_path: str,
  ):
    self.db_path = db_path
    self.conn = sqlite3.connect(db_path)
    self.conn.row_factory = sqlite3.Row
    self._create_table()

  def _create_table(self):
    with self.conn:
      self.conn.execute("""
                CREATE TABLE IF NOT EXISTS whiteboard (
                    conversation_id TEXT PRIMARY KEY,
                    state TEXT NOT NULL
                )
            """)

  def get_state(
    self,
    conversation_id: UUID,
  ) -> str:
    with self.conn:
      result = self.conn.execute(
        "SELECT state FROM whiteboard WHERE conversation_id = ?",
        (str(conversation_id),),
      ).fetchone()

    if result:
      return result["state"]
    else:
      # Initialize with template if not exists
      self.set_state(
        conversation_id, WHITEBOARD_TEMPLATE
      )
      return WHITEBOARD_TEMPLATE

  def set_state(
    self,
    conversation_id: UUID,
    state: str,
  ):
    with self.conn:
      self.conn.execute(
        "INSERT OR REPLACE INTO whiteboard (conversation_id, state) VALUES (?, ?)",
        (str(conversation_id), state),
      )

  async def update_whiteboard(
    self,
    conversation_id: UUID,
    messages: Iterable[Message],
    context: dict[str, Any],
  ) -> str:
    current_state = self.get_state(conversation_id)
    message_history = "\n".join(
      f"{m['role']}: {m['content']}"
      for m in messages
      if m["role"] != "system"
    )
    context_str = "\n".join(
      f"{k}: {v}" for k, v in context.items()
    )
    update_prompt = UPDATE_WHITEBOARD_PROMPT.render(
      previous_state=current_state,
      message_history=message_history,
      context=context_str,
    )

    new_state = str(
      await call_llm(
        messages=[
          cast(
            Message,
            {
              "role": "system",
              "content": update_prompt,
            },
          )
        ],
        params=UPDATE_WHITEBOARD_PROMPT.params,
      )
    )

    self.set_state(conversation_id, new_state)
    return new_state
