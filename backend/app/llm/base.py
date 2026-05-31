from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ToolCall:
    """A normalized tool call. Field names (name/input/id) MUST match what
    app.agent.memory.save_memory reads off each item — do not rename."""
    id: str
    name: str
    input: dict


@dataclass
class Turn:
    """One assistant turn, normalized across providers."""
    text: str                  # assistant's text (may be "")
    tool_calls: list[ToolCall]
    stop_reason: str           # normalized: "end_turn" | "tool_use"


class LLMAdapter(ABC):
    """Each adapter owns the native `messages` list format for its provider.
    The orchestrator treats `messages` as opaque and only handles Turn/ToolCall."""

    @abstractmethod
    def init_messages(self, system: str, user_text: str) -> list:
        """Return the initial native messages list for one agent run."""

    @abstractmethod
    async def create_turn(self, system: str, messages: list, tools: list, max_tokens: int) -> Turn:
        """Call the provider and return a normalized Turn."""

    @abstractmethod
    def append_assistant(self, messages: list, turn: Turn) -> None:
        """Append the assistant turn to `messages` in native format."""

    @abstractmethod
    def append_tool_results(self, messages: list, results: list[tuple[str, str]]) -> None:
        """Append tool results (each a (tool_call_id, content) pair) in native format."""
