import asyncio
from datetime import datetime, timezone
from app.db.client import get_supabase


async def build_system_prompt(lead: dict, trigger: str) -> str:
    enrichment = lead.get("lead_enrichment") or {}
    if isinstance(enrichment, list):
        enrichment = enrichment[0] if enrichment else {}

    event = lead.get("event") or {}
    days_until_event = "N/A"
    event_date_str = event.get("event_date", "")
    if event_date_str:
        try:
            event_date = datetime.fromisoformat(event_date_str.replace("Z", "+00:00"))
            days_until_event = str((event_date - datetime.now(timezone.utc)).days)
        except Exception:
            pass

    enrichment_summary = (
        enrichment.get("enrichment_summary")
        or "Lead ainda não enriquecido — chame enrich_lead() antes de qualquer comunicação."
    )

    lead_id = lead.get("id", "")
    last_message_at, last_opened, last_clicked = await _fetch_last_engagement(lead_id)
    last_5_memory_entries = await _fetch_memory(lead_id)

    return f"""Você é o agente comercial do Vigil Summit, evento de cibersegurança da Vigil.AI.

Seu objetivo é guiar cada lead do momento da inscrição até uma reunião comercial agendada. Você toma decisões autônomas com base no estado atual do lead.

PERFIL DO LEAD:
{enrichment_summary}

ESTADO ATUAL:
- Stage: {lead.get('stage', 'REGISTERED')}
- Trigger: {trigger}
- Dias até o evento: {days_until_event}
- Último e-mail enviado: {last_message_at}
- Abriu último e-mail: {last_opened}
- Clicou no último e-mail: {last_clicked}
- Tem acompanhante: {lead.get('has_companion', False)}
- Optou por WhatsApp: {bool(lead.get('whatsapp_consent_at'))}  ← se False, nunca chame send_whatsapp()
- Decision maker: {enrichment.get('is_decision_maker', False)}
- Setor: {enrichment.get('sector', 'N/A')}

HISTÓRICO RECENTE:
{last_5_memory_entries}

Antes de qualquer ação, avalie o estado e decida a ação mais adequada.
Registre seu raciocínio antes de chamar qualquer tool.
Se stage=REGISTERED, a primeira ação é sempre enrich_lead()."""


async def _fetch_last_engagement(lead_id: str) -> tuple[str, str, str]:
    """Busca abertura e clique do último email enviado ao lead."""
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
    """Busca as 5 entradas mais recentes de lead_memory em ordem cronológica."""
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
        rows.reverse()  # mais antigo primeiro
        if not rows:
            return "Sem histórico anterior."
        return "\n".join(
            f"[{r['created_at'][:16]}] {r['role'].upper()}: {r['content'][:300]}"
            for r in rows
        )
    except Exception:
        return "Sem histórico anterior."
