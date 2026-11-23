"""Turns conversation history and a question into the LangChain message list
AIService.invoke() expects. Retrieval happens on the model's own terms via
assistant_tools.py's tools, not by pre-loading data into this prompt.
"""
from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

# Keeps prompt size (and provider cost) bounded for long-running conversations.
MAX_HISTORY_MESSAGES = 20

SYSTEM_PROMPT = (
    "You are the greenhouse monitoring assistant. You have tools to look up "
    "current area conditions, sensor status, and recent sensor history - call "
    "them whenever you need real data, and never invent sensor readings, "
    "zones, or values. Temperature values are in degrees Celsius. If a tool "
    "reports no matching area or sensor, say so plainly instead of guessing."
)


def build_messages(history, question):
    """history: list of {"role": "user"|"assistant", "content": str}, oldest first."""
    messages = [SystemMessage(content=SYSTEM_PROMPT)]

    for turn in history[-MAX_HISTORY_MESSAGES:]:
        if turn["role"] == "user":
            messages.append(HumanMessage(content=turn["content"]))
        else:
            messages.append(AIMessage(content=turn["content"]))

    messages.append(HumanMessage(content=question))
    return messages
