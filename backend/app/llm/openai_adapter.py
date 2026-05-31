import json
from openai import AsyncOpenAI
from app.config import settings
from app.llm.base import LLMAdapter, Turn, ToolCall


class OpenAIAdapter(LLMAdapter):
    def __init__(self):
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)
        self._model = settings.openai_agent_model
        self._raw_by_turn: dict[int, dict] = {}

    @staticmethod
    def _to_openai_tools(tools: list) -> list:
        return [
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t.get("description", ""),
                    "parameters": t["input_schema"],
                },
            }
            for t in tools
        ]

    def init_messages(self, system: str, user_text: str) -> list:
        # OpenAI puts the system prompt as the first message.
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user_text},
        ]

    async def create_turn(self, system: str, messages: list, tools: list, max_tokens: int) -> Turn:
        resp = await self._client.chat.completions.create(
            model=self._model,
            max_tokens=max_tokens,
            messages=messages,
            tools=self._to_openai_tools(tools),
        )
        choice = resp.choices[0]
        msg = choice.message
        text = msg.content or ""
        tool_calls: list[ToolCall] = []
        raw_tool_calls = []
        for tc in (msg.tool_calls or []):
            try:
                parsed = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                parsed = {}
            tool_calls.append(ToolCall(id=tc.id, name=tc.function.name, input=parsed))
            raw_tool_calls.append({
                "id": tc.id,
                "type": "function",
                "function": {"name": tc.function.name, "arguments": tc.function.arguments or "{}"},
            })
        if choice.finish_reason == "stop":
            stop = "end_turn"
        elif choice.finish_reason == "tool_calls":
            stop = "tool_use"
        else:
            stop = choice.finish_reason
        turn = Turn(text=text, tool_calls=tool_calls, stop_reason=stop)
        assistant_msg: dict = {"role": "assistant", "content": msg.content}
        if raw_tool_calls:
            assistant_msg["tool_calls"] = raw_tool_calls
        self._raw_by_turn[id(turn)] = assistant_msg
        return turn

    def append_assistant(self, messages: list, turn: Turn) -> None:
        messages.append(self._raw_by_turn[id(turn)])

    def append_tool_results(self, messages: list, results: list[tuple[str, str]]) -> None:
        for tid, result in results:
            messages.append({"role": "tool", "tool_call_id": tid, "content": result})
