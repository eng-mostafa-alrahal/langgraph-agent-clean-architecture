"""Base state schema shared by all LangGraph sub-graphs."""

from __future__ import annotations

from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class BaseAgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    session_id: str
    user_id: str
    error: str | None
