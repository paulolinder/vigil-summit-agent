import anthropic
from app.config import settings
from app.llm.base import LLMAdapter, Turn, ToolCall


class AnthropicAdapter(LLMAdapter):
    def __init__(self):
        self._client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        # Maps id(turn) to the raw SDK content list, so append_assistant can
        # re-inject the exact native blocks Anthropic expects.
        self._raw_by_turn: dict[int, list] = {}

    def init_messages(self, system: str, user_text: str) -> list:
        # Anthropic takes `system` as a top-level param, not a message.
        return [{"role": "user", "content": user_text}]

    async def create_turn(self, system: str, messages: list, tools: list, max_tokens: int) -> Turn:
        resp = await self._client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=max_tokens,
            system=system,
            tools=tools,
            messages=messages,
        )
        text = ""
        tool_calls: list[ToolCall] = []
        for block in resp.content:
            if block.type == "text":
                text = block.text
            elif block.type == "tool_use":
                tool_calls.append(ToolCall(id=block.id, name=block.name, input=block.input))
        if resp.stop_reason == "end_turn":
            stop = "end_turn"
        elif resp.stop_reason == "tool_use":
            stop = "tool_use"
        else:
            stop = resp.stop_reason
        turn = Turn(text=text, tool_calls=tool_calls, stop_reason=stop)
        self._raw_by_turn[id(turn)] = resp.content
        return turn

    def append_assistant(self, messages: list, turn: Turn) -> None:
        messages.append({"role": "assistant", "content": self._raw_by_turn[id(turn)]})

    def append_tool_results(self, messages: list, results: list[tuple[str, str]]) -> None:
        content = [
            {"type": "tool_result", "tool_use_id": tid, "content": result}
            for tid, result in results
        ]
        messages.append({"role": "user", "content": content})
