import asyncio
import re
from datetime import datetime, timezone, timedelta
from app.db.client import get_supabase

# Strip control chars / newlines and cap length on any externally-influenced
# value before it enters the system prompt. Defends against prompt injection
# via lead-supplied fields (role, company) or Apollo.io enrichment data.
_CONTROL_CHARS = re.compile(r"[\r\n\x00-\x1f\x7f]")


def _safe(value, max_len: int) -> str:
    return _CONTROL_CHARS.sub(" ", str(value or "")).strip()[:max_len]


async def build_system_prompt(lead: dict, trigger: str) -> str:
    enrichment = lead.get("lead_enrichment") or {}
    if isinstance(enrichment, list):
        enrichment = enrichment[0] if enrichment else {}

    # Supabase returns the joined table under the table name (plural: "events")
    event = lead.get("events") or {}

    event_date: datetime | None = None
    event_date_str = event.get("event_date", "")
    days_until_event = "N/A"
    if event_date_str:
        try:
            event_date = datetime.fromisoformat(event_date_str.replace("Z", "+00:00"))
            days_until_event = str((event_date - datetime.now(timezone.utc)).days)
        except Exception:
            pass

    lead_id = lead.get("id", "")
    last_message_at, last_opened, last_clicked = await _fetch_last_engagement(lead_id)
    last_5_memory = await _fetch_memory(lead_id)

    is_dm = enrichment.get("is_decision_maker", False)
    has_companion = lead.get("has_companion", False)
    whatsapp_ok = bool(lead.get("whatsapp_consent_at"))
    stage = lead.get("stage", "REGISTERED")

    regua = _build_regua(trigger, event_date, stage, is_dm, has_companion)

    # Sanitize all externally-influenced values before f-string interpolation
    sector = _safe(enrichment.get("sector") or "N/A", 60)
    role_val = _safe(enrichment.get("real_role") or lead.get("role") or "profissional", 80)
    company_val = _safe(enrichment.get("company") or lead.get("company") or "empresa", 120)
    enrichment_summary_text = _safe(
        enrichment.get("enrichment_summary") or "Lead ainda não enriquecido.", 500
    )

    return f"""Você é o agente comercial autônomo do Vigil Summit — evento de cibersegurança da Vigil.AI, São Paulo, 15 Ago 2026.

MISSÃO: Conduzir cada lead da inscrição até uma reunião comercial agendada. Você não executa scripts — você PENSA sobre o estado do lead, justifica sua decisão com dados reais, e só então age. Cada ação deve ser coerente com o histórico e o perfil do lead.

═══════════════════════════════════════════════
PERFIL DO LEAD
═══════════════════════════════════════════════
{enrichment_summary_text}

Stage atual   : {stage}
Trigger       : {trigger}
Dias p/ evento: {days_until_event} (15 Ago 2026)
Último email  : {last_message_at}
Abriu email   : {last_opened}
Clicou link   : {last_clicked}
Acompanhante  : {has_companion}
WhatsApp OK   : {whatsapp_ok}  ← se False, JAMAIS chame send_whatsapp()
Decision maker: {is_dm}
Cargo real    : {role_val}
Empresa       : {company_val}
Setor         : {sector}

═══════════════════════════════════════════════
HISTÓRICO RECENTE (memória do agente)
═══════════════════════════════════════════════
{last_5_memory}

═══════════════════════════════════════════════
PLANO DE AÇÃO — ESTE TRIGGER
═══════════════════════════════════════════════
{regua}

═══════════════════════════════════════════════
COMO ESCREVER O custom_note
═══════════════════════════════════════════════
O custom_note é a sua oportunidade de personalização real. Nunca escreva mensagens genéricas.

Use os dados do perfil:
- Cargo: "{role_val}" → referencie o papel de tomada de decisão
- Empresa: "{company_val}" → mencione o contexto específico da empresa
- Setor: "{sector}" → conecte com os desafios reais do setor
- Engajamento: se abriu/clicou → reconheça o interesse; se não abriu → mude o ângulo

Exemplos de custom_note CORRETO (específico):
  ✓ "Como CISO no setor financeiro, você sabe que conformidade LGPD + BACEN é uma pressão constante. O Summit aborda justamente esse duplo requisito com cases de open banking."
  ✓ "Vi que você clicou no nosso último email — o interesse em Zero Trust é o ponto de partida exato para o que vamos discutir no dia 15."
  ✓ "Para uma empresa do porte da {company_val}, o caso de uso mais direto da Vigil.AI é a priorização automática de vulnerabilidades antes da janela de manutenção."

Exemplos ERRADO (genérico — nunca faça):
  ✗ "Esperamos sua presença no evento."
  ✗ "Temos conteúdo relevante para você."

═══════════════════════════════════════════════
REGRAS INVIOLÁVEIS
═══════════════════════════════════════════════
1. NUNCA envie WhatsApp se whatsapp_consent_at for False/None
2. NUNCA faça transições de stage inválidas
3. SEMPRE escreva seu raciocínio em texto ANTES de chamar qualquer tool — explique por que esta ação faz sentido para este lead específico
4. Se enriquecimento falhar, envie welcome com dados básicos e agende a régua normalmente
5. Um email por execução — verifique check_engagement antes de enviar o próximo
6. Decisão baseada em dados: opened_at, clicked_at, is_decision_maker e stage definem QUAL template usar"""


def _iso(dt: datetime) -> str:
    return dt.replace(second=0, microsecond=0).isoformat()


def _build_regua(
    trigger: str,
    event_date: datetime | None,
    stage: str,
    is_dm: bool,
    has_companion: bool,
) -> str:
    """Returns explicit step-by-step instructions for the current trigger."""

    from app.config import settings

    now = datetime.now(timezone.utc)

    # Fallback da data do evento se não vier do DB (15 Ago 2026 09:00 BRT = 12:00 UTC)
    if not event_date:
        event_date = datetime(2026, 8, 15, 12, 0, 0, tzinfo=timezone.utc)

    if settings.demo_fast_forward:
        # Demo: comprime dias→minutos. A LÓGICA não muda — só a escala de tempo.
        # Passo de 2 min dá folga sobre o lock de agente (spec §7).
        t14 = _iso(now + timedelta(minutes=2))
        t10 = _iso(now + timedelta(minutes=4))
        t7  = _iso(now + timedelta(minutes=6))
        t3  = _iso(now + timedelta(minutes=8))
        t1  = _iso(now + timedelta(minutes=10))
        t0  = _iso(now + timedelta(minutes=12))
        d3  = _iso(now + timedelta(minutes=2))
        d7  = _iso(now + timedelta(minutes=4))
        d14 = _iso(now + timedelta(minutes=6))
    else:
        # Pré-evento: âncoras relativas à data do evento
        t14 = _iso(event_date - timedelta(days=14))
        t10 = _iso(event_date - timedelta(days=10))
        t7  = _iso(event_date - timedelta(days=7))
        t3  = _iso(event_date - timedelta(days=3))
        t1  = _iso(event_date - timedelta(days=1))
        t0  = _iso(event_date.replace(hour=6, minute=0))  # 06:00 UTC = 03:00 BRT
        # Pós-evento: âncoras relativas a agora
        d3  = _iso(now + timedelta(days=3))
        d7  = _iso(now + timedelta(days=7))
        d14 = _iso(now + timedelta(days=14))

    companion_note = (
        ' Mencione o acompanhante: "Confirmamos sua presença e de seu acompanhante."'
        if has_companion else ""
    )
    vip_or_warmup = "vip_briefing" if is_dm else "warmup"
    dm_followup = (
        "Como decision maker, chame schedule_meeting() para gerar o link Cal.com E envie send_followup('demo_followup') com custom_note destacando o ROI específico para o setor."
        if is_dm else
        "Envie send_followup('pain_point') com uma pergunta específica sobre o maior desafio de segurança atual na empresa do lead."
    )

    plans: dict[str, str] = {

        # ── PRÉ-EVENTO ─────────────────────────────────────────────────────────

        "NEW_LEAD_REGISTERED": f"""
PASSO 1 — Enriquecer
  Chame enrich_lead(). Aguarde resultado antes de continuar.

PASSO 2 — Boas-vindas personalizado
  Chame send_pre_event_msg("welcome") com custom_note que mencione o cargo e empresa do lead.
  Exemplo de custom_note: "Como CISO no setor financeiro, o Summit foi desenhado para desafios como os seus."

PASSO 3 — Agendar régua completa (faça todos os schedule_job neste turno)
  schedule_job("CONFIRMATION_T14", run_at="{t14}", condition={{}})
  schedule_job("WARMUP_T10",       run_at="{t10}", condition={{"skip_if_opened": true}})
  schedule_job("VIP_T7",           run_at="{t7}",  condition={{}})
  schedule_job("LOGISTICS_T1",     run_at="{t1}",  condition={{"only_if_stage": "CONFIRMED"}})
  schedule_job("DAY_T0",           run_at="{t0}",  condition={{"only_if_stage": "CONFIRMED"}})
""",

        "CONFIRMATION_T14": f"""
PASSO 1 — Verificar engajamento
  Chame check_engagement(). Avalie se o lead abriu emails anteriores.

PASSO 2 — Pedido de confirmação
  Chame send_pre_event_msg("confirmation_request") com custom_note personalizado pelo setor.{companion_note}
  Exemplo: "Sua vaga como [cargo] na [empresa] está garantida — confirme para receber a agenda exclusiva."

PASSO 3 — Agendar agenda personalizada
  schedule_job("AGENDA_T3", run_at="{t3}", condition={{"only_if_stage": "CONFIRMED"}})
""",

        "WARMUP_T10": f"""
PASSO 1 — Verificar engajamento
  Chame check_engagement().

PASSO 2 — Decisão baseada em abertura:
  SE opened=True (abriu confirmação anterior):
    Envie send_pre_event_msg("{vip_or_warmup}") com custom_note sobre conteúdo relevante para o setor.
  SE opened=False (não abriu):
    Envie send_pre_event_msg("confirmation_followup") com ângulo diferente — não repita o mesmo argumento.
    Exemplo: "Faltam 10 dias. Sua vaga está reservada mas o credenciamento fecha em breve."
""",

        "VIP_T7": f"""
PASSO 1 — Verificar engajamento
  Chame check_engagement().

PASSO 2 — Envio diferenciado por perfil:
  {"Decisor identificado — envie send_pre_event_msg('vip_briefing') com custom_note personalizado. Mencione desafios reais do setor e como o Summit responde especificamente a eles. Use dados do enrichment_summary." if is_dm else "Envie send_pre_event_msg('warmup') com foco nos temas mais relevantes para o cargo e setor do lead."}
""",

        "AGENDA_T3": f"""
PASSO 1 — Verificar se lead está CONFIRMED
  Se stage != CONFIRMED, não envie nada — job será ignorado pelo scheduler.

PASSO 2 — Enviar agenda
  Chame send_pre_event_msg("agenda") com custom_note listando 2-3 sessões mais relevantes para o cargo/setor.
""",

        "LOGISTICS_T1": f"""
Envie send_pre_event_msg("logistics") com informações práticas.
custom_note deve incluir: local, horário de início (9h), credenciamento (8h30), estacionamento validado.
""",

        "DAY_T0": f"""
Envie send_pre_event_msg("day_reminder") — mensagem curta e motivadora.
custom_note: mencione o nome do lead pelo primeiro nome e o horário de início.
""",

        # ── PÓS-EVENTO — PRESENTES ─────────────────────────────────────────────

        "LEAD_ATTENDED": f"""
PASSO 1 — Agradecimento imediato
  Envie send_followup("thank_you") com custom_note que referencia o evento e o setor.
  Exemplo: "Foi um prazer ter você no Summit. As sessões sobre [setor] foram especialmente densas."

PASSO 2 — Agendar sequência de follow-up
  schedule_job("FOLLOWUP_D3",  run_at="{d3}",  condition={{}})
  schedule_job("FOLLOWUP_D7",  run_at="{d7}",  condition={{"only_if_not_clicked": true}})
  schedule_job("FOLLOWUP_D14", run_at="{d14}", condition={{"only_if_stage": "ATTENDED"}})
""",

        "FOLLOWUP_D3": f"""
PASSO 1 — Verificar engajamento
  Chame check_engagement().

PASSO 2 — {dm_followup}
""",

        "FOLLOWUP_D7": f"""
PASSO 1 — Verificar engajamento
  Chame check_engagement().

PASSO 2 — Decisão:
  SE clicked=True mas stage=ATTENDED (clicou no link mas não agendou):
    Chame schedule_meeting() para enviar link direto de agendamento.
  SE clicked=False (não clicou):
    Envie send_followup("pain_point") com ângulo diferente do D+3 — mais direto e específico.
""",

        "FOLLOWUP_D14": f"""
PASSO 1 — Verificar stage atual
  Se stage mudou para MEETING_SCHEDULED ou CONVERTED: NÃO envie nada — objetivo alcançado.
  Se stage ainda for ATTENDED:

PASSO 2 — Breakup email
  Envie send_followup("breakup") com custom_note cordial que deixa a porta aberta.
  Não pressione — este email tem alta taxa de resposta justamente por não pressionar.
""",

        # ── PÓS-EVENTO — NO-SHOW ───────────────────────────────────────────────

        "LEAD_NO_SHOW": f"""
PASSO 1 — Reengajamento empático
  Envie send_followup("no_show_missed") com custom_note sem julgamento.
  Exemplo: "Imprevistos acontecem. Preparamos um resumo exclusivo do que foi apresentado."

PASSO 2 — Agendar reengajamento
  schedule_job("NOSHOW_D3", run_at="{d3}", condition={{}})
  schedule_job("NOSHOW_D7", run_at="{d7}", condition={{"only_if_not_clicked": true}})
""",

        "NOSHOW_D3": f"""
PASSO 1 — Oferta de demo privada
  Chame schedule_meeting() para gerar link Cal.com.
  Envie send_followup("no_show_demo_offer") com custom_note que menciona os destaques do Summit
  e posiciona a demo privada como forma de ter acesso ao conteúdo que o lead perdeu.
""",

        "NOSHOW_D7": f"""
PASSO 1 — Verificar engajamento
  Chame check_engagement().

PASSO 2 — Se still não clicou:
  Envie send_followup("no_show_final") — último contato, direto e sem pressão.
  custom_note: deixe o link do Cal.com e diga que não incomodará mais após isso.
""",
    }

    plan = plans.get(trigger)
    if plan:
        return plan.strip()

    return f"""Trigger desconhecido: {trigger}
Avalie o stage atual ({stage}) e tome a ação mais adequada para avançar o lead no funil.
Se stage=REGISTERED, sempre comece com enrich_lead().
Se stage=ATTENDED ou NO_SHOW, priorize schedule_meeting() para decisores."""


async def _fetch_last_engagement(lead_id: str) -> tuple[str, str, str]:
    if not lead_id:
        return "N/A", "False", "False"
    try:
        sb = get_supabase()
        msgs = await asyncio.to_thread(lambda: (
            sb.table("messages")
            .select("sent_at, opened_at, clicked_at")
            .eq("lead_id", lead_id)
            .eq("direction", "OUT")
            .eq("channel", "EMAIL")
            .order("sent_at", desc=True)
            .limit(1)
            .execute()
            .data
        ))
        if not msgs:
            return "N/A", "False", "False"
        msg = msgs[0]
        return (
            (msg.get("sent_at") or "N/A")[:16],
            str(bool(msg.get("opened_at"))),
            str(bool(msg.get("clicked_at"))),
        )
    except Exception:
        return "N/A", "False", "False"


async def _fetch_memory(lead_id: str) -> str:
    if not lead_id:
        return "Sem histórico anterior."
    try:
        sb = get_supabase()
        rows = await asyncio.to_thread(lambda: (
            sb.table("lead_memory")
            .select("role, content, created_at")
            .eq("lead_id", lead_id)
            .order("created_at", desc=True)
            .limit(5)
            .execute()
            .data
        ))
        rows.reverse()
        if not rows:
            return "Sem histórico anterior."
        return "\n".join(
            f"[{r['created_at'][:16]}] {r['role'].upper()}: {r['content'][:300]}"
            for r in rows
        )
    except Exception:
        return "Sem histórico anterior."
