# Agente Multi-Provedor (Anthropic / OpenAI) — Design

**Data:** 2026-05-31
**Origem:** Pedido do usuário — o backend deve detectar qual chave de LLM está no ambiente
(`ANTHROPIC_API_KEY` ou `OPENAI_API_KEY`) e ativar a LLM correspondente, em **tudo** que usa LLM.
**Verificação:** design verificado contra o código real (feature-dev:code-reviewer) antes de escrever
o spec; achados incorporados (ver "Achados da verificação").

---

## Objetivo e decisões

Tornar o uso de LLM **multi-provedor** com **auto-detecção pela chave presente**.

| Decisão | Valor |
|---|---|
| Escopo | Tudo que usa LLM: agente orquestrador (backend) + chatbot da landing (frontend) + health-check |
| Seleção | Auto-detecção: `ANTHROPIC_API_KEY` presente → Anthropic; senão `OPENAI_API_KEY` → OpenAI; nenhuma → erro claro |
| Empate (as duas presentes) | **Anthropic ganha** (provedor atual; zero surpresa no comportamento de produção) |
| Modelo do agente | Anthropic `claude-sonnet-4-6` / OpenAI `OPENAI_AGENT_MODEL` (default `gpt-4.1`) |
| Modelo do chatbot | Anthropic `claude-haiku-4-5-20251001` / OpenAI `OPENAI_CHAT_MODEL` (default `gpt-4.1-mini`) |
| Abordagem | Adapter interno feito à mão (sem LiteLLM, sem endpoint compat) |
| Model IDs OpenAI | Configuráveis por env var, com defaults acima (strings exatos não confirmáveis estaticamente) |
| Testes | Atualizar os testes existentes do agente + 1 teste novo de `detect_provider` |

---

## Inventário de pontos LLM (escopo real, confirmado no código)

| # | Arquivo | O que faz hoje |
|---|---|---|
| 1 | `backend/app/agent/orchestrator.py` | Loop do agente — Anthropic async, `messages.create`, model `claude-sonnet-4-6`, tool-use |
| 2 | `backend/app/api/admin.py` | Health-check `_ping_anthropic` + nome/detalhe de serviço hardcoded "Claude"/"claude-sonnet-4-6" |
| 3 | `frontend/app/api/chat/route.ts` | Chatbot SSE streaming — Anthropic TS SDK, model `claude-haiku-4-5-20251001`, sem tools |
| 4 | `backend/app/config.py` | `anthropic_api_key: str` — **obrigatório** (app não sobe sem ele) |
| 5 | `backend/requirements.txt` | Só `anthropic==0.40.0` |
| 6 | `frontend/package.json` | Só `@anthropic-ai/sdk` |
| 7 | `backend/tests/test_agent.py` | Mocka `orchestrator._get_client` (some no refactor) |

Não há nenhum outro uso de LLM no repositório (grep confirmou).

---

## Arquitetura

### Backend — novo pacote `backend/app/llm/`

Isola o orquestrador dos dialetos de cada provedor. Quatro arquivos:

**`provider.py`** — detecção + mapa de modelos.
- `detect_provider() -> Literal["anthropic", "openai"]`: lê `settings`; Anthropic ganha empate;
  levanta `RuntimeError` claro se nenhuma chave estiver presente.
- `MODELS = {"anthropic": {"agent": "claude-sonnet-4-6"}, "openai": {"agent": settings.openai_agent_model}}`
  (o chatbot do backend não existe; só o agente usa modelo no backend).

**`base.py`** — tipos normalizados + interface.
```python
@dataclass
class ToolCall:
    id: str
    name: str
    input: dict     # nomes batem com memory.py (t.name, t.input, t.id) — NÃO renomear

@dataclass
class Turn:
    text: str                 # texto do assistant (para save_memory)
    tool_calls: list[ToolCall]
    stop_reason: str          # normalizado: "end_turn" | "tool_use"

class LLMAdapter(ABC):
    async def create_turn(self, system: str, messages: list, tools: list, max_tokens: int) -> Turn
    def append_assistant(self, messages: list, turn: Turn, raw) -> None   # acrescenta o assistant no formato nativo
    def append_tool_results(self, messages: list, results: list[tuple[str, str]]) -> None  # (tool_call_id, conteúdo)
    def init_messages(self, user_text: str) -> list   # 1ª mensagem no formato nativo
```

**`anthropic_adapter.py`** — envolve o SDK Anthropic.
- `create_turn`: `messages.create(model, max_tokens, system=system, tools=tools, messages=messages)`;
  converte `response.content` → `Turn` (texto + `ToolCall` de cada bloco `tool_use`); mapeia
  `stop_reason`. Guarda `response.content` cru para o `append_assistant`.
- `append_assistant`: `messages.append({"role": "assistant", "content": raw})`.
- `append_tool_results`: `messages.append({"role": "user", "content": [{"type":"tool_result","tool_use_id":id,"content":c} ...]})`.
- `init_messages`: `[{"role":"user","content":user_text}]`. TOOLS usados como estão (formato nativo).

**`openai_adapter.py`** — envolve o SDK OpenAI.
- `create_turn`: `chat.completions.create(model, max_tokens, messages, tools=tools_openai)`; converte
  `choices[0].message.tool_calls` → `Turn`; mapeia `finish_reason` ("stop"→"end_turn",
  "tool_calls"→"tool_use"). `tool_calls[].function.arguments` é JSON string → `json.loads` p/ `input`.
- `append_assistant`: acrescenta a `message` do assistant no formato OpenAI (com `tool_calls`).
- `append_tool_results`: uma msg `{"role":"tool","tool_call_id":id,"content":c}` por resultado.
- `init_messages`: `[{"role":"system","content":system},{"role":"user","content":user_text}]`
  (OpenAI põe o system como 1ª mensagem; o `system` ainda é passado em `create_turn` mas o adapter
  decide onde colocá-lo — para OpenAI, ignora o param e usa a msg system de `init_messages`).
- **Tradução de TOOLS:** `{"type":"function","function":{"name","description","parameters": input_schema}}`.

### Orquestrador — `orchestrator.py` (reescrito em torno do adapter)

- `adapter = get_adapter()` (resolve via `detect_provider()`).
- `messages = adapter.init_messages(user_text)`. **Nunca mais `messages.append(...)` direto.**
- Loop (máx 10 iters): `turn = await adapter.create_turn(system, messages, TOOLS, max_tokens=4096)`.
  - `if turn.text: await save_memory(lead_id, "assistant", turn.text, turn.tool_calls or None)`
    (`ToolCall` tem `.name/.input/.id` → `memory.py` intacto).
  - `if turn.stop_reason == "end_turn": break`.
  - `if turn.stop_reason == "tool_use"`: `adapter.append_assistant(...)`; executa cada tool via
    `execute_tool(tc.name, tc.input, lead_id)`; `adapter.append_tool_results(messages, [(tc.id, result), ...])`.
- Lock/heartbeat/`build_system_prompt`/`execute_tool` ficam **inalterados** (provider-agnósticos).

### Health-check — `admin.py`

- `_ping_anthropic` → `_ping_llm()` que ramifica pelo provedor detectado (ping Anthropic
  `models.list()` ou OpenAI `models.list()`).
- A linha de serviço "Claude (Anthropic)" vira dinâmica: nome = provedor ativo, detail = model do agente.

### Chatbot (frontend) — `chat/route.ts` (código próprio, NÃO compartilha com o backend)

- Detecção própria em TS, mesma regra: `ANTHROPIC_API_KEY` → Anthropic; senão `OPENAI_API_KEY` → OpenAI.
- Anthropic: como hoje (stream `content_block_delta`/`text_delta`).
- OpenAI: `openai` SDK, `chat.completions.create({stream:true})`, itera `choices[0].delta.content`.
- **O SSE enviado ao browser fica idêntico** (`data: {"text":...}` / `data: [DONE]`) → `ChatbotWidget.tsx`
  **não muda**. System prompt vira a 1ª msg role `system` no caminho OpenAI.

### Config & deps

- `config.py`: `anthropic_api_key: str = ""`, `openai_api_key: str = ""`,
  `openai_agent_model: str = "gpt-4.1"`, `openai_chat_model: str = "gpt-4.1-mini"`.
  `@model_validator(mode="after")` levanta erro claro se ambas as chaves de LLM estiverem vazias.
- `requirements.txt`: `+ openai>=1.30.0`. `package.json`: `+ "openai": "^4.0.0"`.
- `.env.example` (backend e frontend): documentar `OPENAI_API_KEY`, `OPENAI_AGENT_MODEL`, `OPENAI_CHAT_MODEL`.

---

## Tratamento de erros

- **Nenhuma chave de LLM:** `config.py` falha no boot com mensagem clara (backend); `chat/route.ts`
  retorna o erro SSE já existente ("…não configurada", adaptado para "nenhum provedor de LLM configurado").
- **Model ID inválido (OpenAI):** erro de runtime na 1ª chamada; mitigado por ser configurável via env var.
- **Empate de chaves:** resolvido deterministicamente (Anthropic), sem erro.

---

## Testes (decisão: atualizar existentes + 1 de detecção)

- `test_agent.py`: trocar o mock de `orchestrator._get_client` por um **mock adapter** injetado
  (mocka `create_turn` retornando `Turn`/`ToolCall`), mantendo o teste do loop verde.
- **Novo** `test_provider.py`: `detect_provider` — Anthropic ganha empate; OpenAI quando só ela;
  erro quando nenhuma. Sem chamadas de rede.
- Validação multi-provedor de verdade: **teste vivo manual** (rodar o agente com cada chave).

---

## Arquivos afetados

| Arquivo | Ação |
|---|---|
| `backend/app/llm/__init__.py` | **Criar** |
| `backend/app/llm/provider.py` | **Criar** (detect_provider + MODELS + get_adapter) |
| `backend/app/llm/base.py` | **Criar** (ToolCall, Turn, LLMAdapter) |
| `backend/app/llm/anthropic_adapter.py` | **Criar** |
| `backend/app/llm/openai_adapter.py` | **Criar** |
| `backend/app/agent/orchestrator.py` | Editar (usar adapter; remover `_get_client` e appends inline) |
| `backend/app/api/admin.py` | Editar (`_ping_llm` + serviço dinâmico) |
| `backend/app/config.py` | Editar (chaves opcionais + models OpenAI + validator) |
| `backend/requirements.txt` | Editar (`openai`) |
| `backend/tests/test_agent.py` | Editar (mock adapter) |
| `backend/tests/test_provider.py` | **Criar** |
| `frontend/app/api/chat/route.ts` | Editar (detecção + ramo OpenAI; SSE idêntico) |
| `frontend/package.json` | Editar (`openai`) |
| `backend/.env.example`, `frontend/.env.example` | Editar (documentar vars OpenAI) |

`memory.py`, `tool_executor.py`, `tools.py`, `prompts.py`, `lock_manager.py`, `ChatbotWidget.tsx`
**não mudam** (provider-agnósticos).

---

## Achados da verificação (incorporados)

| Sev | Achado | Resolução no design |
|---|---|---|
| Crítico | `save_memory`/`memory.py:12` lê `t.name/.input/.id` de objeto | `ToolCall` definido com exatamente esses 3 campos |
| Crítico | Orquestrador faz `messages.append` inline (linhas 84, 93) — OpenAI quebraria | Todas as 3 mutações via métodos do adapter |
| Crítico | `config.py:4` `anthropic_api_key` obrigatório → app não sobe só com OpenAI | Tornado opcional + validator |
| Crítico | `_ping_anthropic` instancia Anthropic sempre → erro com só OpenAI | `_ping_llm()` provider-aware |
| Alto | Chatbot streaming ≠ agente — não compartilhar adapter | Chatbot é código próprio; SSE idêntico p/ não mexer no widget |
| Alto | `append_tool_results` deve receber (id, conteúdo), não dict pronto | Interface recebe `list[tuple[str,str]]` |
| Alto | Formato de TOOLS difere (`input_schema` → `function.parameters`) | Tradução explícita no openai_adapter |
| Alto | Faltam deps `openai` (py + npm) | Adicionadas |
| Médio | `max_tokens` (Anthropic exige, OpenAI opcional) | Sempre passado aos dois |
| Médio | Model IDs `gpt-4.1*` não confirmáveis estaticamente | Configuráveis por env var com default |

---

## Fora de escopo

- Outros provedores além de Anthropic/OpenAI (Gemini etc.).
- Troca de provedor em runtime (a detecção é no boot/por request; trocar chave exige redeploy).
- Paridade fina de comportamento entre os modelos (qualidade de tool-use pode diferir entre
  Sonnet e gpt-4.1 — fora do escopo garantir resultados idênticos).
- Streaming no agente (continua não-streaming; só o chatbot faz streaming).
