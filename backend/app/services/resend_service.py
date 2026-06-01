import asyncio
import resend
from app.config import settings
from app.db.client import get_supabase
from app.services.email_templates import render_html
from datetime import datetime, timezone

# ─────────────────────────────────────────────────────────────────────────────
# RÉGUA DE COMUNICAÇÃO — Vigil Summit 2026
#
# PRÉ-EVENTO (D-14 até D-0)
#   NEW_LEAD  → welcome + agenda [T14, T10, T7, T3, T1, T0]
#   T-14      → confirmation_request  (sempre)
#   T-10      → confirmation_followup (se não abriu T-14) | warmup (se abriu)
#   T-7       → vip_briefing (decisores) | agenda (outros)
#   T-3       → agenda  (só CONFIRMED)
#   T-1       → logistics (só CONFIRMED)
#   T-0       → day_reminder (só CONFIRMED)
#
# PÓS-EVENTO — PRESENTES
#   ATTENDED  → thank_you + agenda [D+3, D+7, D+14]
#   D+3       → demo_followup + schedule_meeting (decisores) | pain_point (outros)
#   D+7       → pain_point (se não clicou) | schedule_meeting (se clicou, sem reunião)
#   D+14      → breakup (se ainda ATTENDED)
#
# PÓS-EVENTO — NO-SHOW
#   NO_SHOW   → no_show_missed + agenda [D+3, D+7]
#   D+3       → no_show_demo_offer + schedule_meeting
#   D+7       → no_show_final (se não clicou)
# ─────────────────────────────────────────────────────────────────────────────

TEMPLATES = {

    # ── PRÉ-EVENTO ────────────────────────────────────────────────────────────

    "welcome": {
        "subject": "{name}, sua vaga no Vigil Summit está garantida",
        "body": """Olá {name},

Sua inscrição no Vigil Summit — Segurança para a Era da IA foi confirmada. Estamos reservando sua vaga entre as 120 disponíveis.

O Summit acontece em 15 de agosto de 2026, em São Paulo, com foco em três temas que dominam a agenda de segurança deste ano:

→ Zero Trust na prática para ambientes híbridos e multicloud
→ IA aplicada à detecção de ameaças e resposta a incidentes
→ Conformidade automatizada: LGPD, ISO 27001 e SOC 2

{role_personalization}

Acompanhe os próximos emails — em breve enviarei uma agenda personalizada com as sessões mais relevantes para o seu perfil.

{custom_note}

Até breve,
Ana Beatriz Costa
Account Executive, Vigil.AI"""
    },

    "confirmation_request": {
        "subject": "{name}, sua vaga expira em 48h — confirme presença",
        "body": """Olá {name},

Faltam 14 dias para o Vigil Summit e sua vaga ainda não foi confirmada.

Com 120 participantes no total e lista de espera ativa, preciso da sua confirmação para garantir o credenciamento e o kit exclusivo do evento.

Por que vale a presença:

{sector_content}

Esses são exatamente os desafios que vão estruturar as discussões do dia 15.

{custom_note}

Para confirmar: basta responder este email com "Confirmo" ou clicar no botão abaixo.

Nos vemos em São Paulo,
Ana Beatriz Costa
Account Executive, Vigil.AI"""
    },

    "confirmation_followup": {
        "subject": "10 dias para o Summit — sua vaga ainda está disponível, {name}",
        "body": """Olá {name},

Ainda não recebi sua confirmação para o Vigil Summit, que acontece em 10 dias.

Entendo que a agenda de {role} é intensa. Por isso vou ser direto: este é o evento onde CISOs e CTOs de empresas como a {company} vão decidir o que entra no roadmap de segurança de 2027.

O que você vai encontrar lá:

{sector_content}

Sua vaga está reservada por mais 48 horas.

{custom_note}

Para confirmar, responda "Confirmo".

Ana Beatriz Costa
Account Executive, Vigil.AI"""
    },

    "warmup": {
        "subject": "{name}, preparei o que você precisa saber antes do Summit",
        "body": """Olá {name},

Com 10 dias para o Vigil Summit, quero garantir que você chegue aproveitando cada hora do evento.

Com base no seu perfil, estas são as sessões mais estratégicas para você:

{sector_content}

{custom_note}

Se tiver alguma dúvida ou quiser alinhar expectativas antes do evento, é só responder este email.

Até lá,
Ana Beatriz Costa
Account Executive, Vigil.AI"""
    },

    "vip_briefing": {
        "subject": "{name}, briefing exclusivo C-level — Vigil Summit",
        "body": """Olá {name},

Preparei um briefing exclusivo para os executivos de segurança confirmados no Vigil Summit.

Como {role}, você vai liderar decisões que impactam diretamente o que discutiremos no dia 15. Por isso quero garantir que chegue com o contexto certo.

O que está em pauta para o seu setor:

{sector_content}

Além das sessões abertas, reservamos um espaço exclusivo para decisores — uma conversa sem palco, direta com o time técnico da Vigil.AI sobre casos reais de implementação.

{custom_note}

Nos vemos em 7 dias.

Ana Beatriz Costa
Account Executive, Vigil.AI"""
    },

    "agenda": {
        "subject": "Sua agenda personalizada para o dia 15, {name}",
        "body": """Olá {name},

O Vigil Summit acontece em 3 dias. Selecionei as sessões mais relevantes para o seu perfil:

{sector_content}

{custom_note}

Programação completa:
→ 8h30 — Credenciamento e café
→ 9h00 — Abertura: IA e o novo perímetro de segurança
→ 10h30 — Track 1: Zero Trust | Track 2: IA em Segurança | Track 3: Conformidade
→ 12h30 — Almoço executivo
→ 14h00 — Mesas redondas por setor
→ 16h30 — Encerramento e networking

Até sábado,
Ana Beatriz Costa
Account Executive, Vigil.AI"""
    },

    "logistics": {
        "subject": "Vigil Summit amanhã — tudo que você precisa saber",
        "body": """Olá {name},

Amanhã é o dia. Aqui estão as informações de acesso:

📍 Centro de Convenções Rebouças
   Av. Dr. Enéas de Carvalho Aguiar, 23 — Pinheiros, São Paulo

🕘 Credenciamento: 8h30 | Início: 9h00

🎫 Leve documento com foto — seu nome está na lista

🚗 Estacionamento no local (validamos com apresentação do crachá)

🍽️ Almoço incluído para todos os confirmados

{custom_note}

Nos vemos amanhã,
Ana Beatriz Costa
Account Executive, Vigil.AI"""
    },

    "day_reminder": {
        "subject": "Hoje é o dia, {name} — Vigil Summit começa às 9h",
        "body": """Bom dia, {name}!

O Vigil Summit começa hoje. Credenciamento aberto a partir das 8h30 no Centro de Convenções Rebouças.

{custom_note}

Até já,
Ana Beatriz Costa
Account Executive, Vigil.AI"""
    },

    # ── PÓS-EVENTO — PRESENTES ────────────────────────────────────────────────

    "thank_you": {
        "subject": "{name}, foi um prazer ter você no Vigil Summit",
        "body": """Olá {name},

Obrigada por ter estado conosco ontem no Vigil Summit.

As discussões foram densas — especialmente as mesas redondas sobre {event_context}. Saí com a sensação de que o nível do grupo estava acima da média de eventos que participo.

Gostaria de continuar a conversa sobre como a Vigil.AI poderia se aplicar especificamente à realidade da {company}.

{custom_note}

Quando tiver 30 minutos, me avise.

Ana Beatriz Costa
Account Executive, Vigil.AI"""
    },

    "demo_followup": {
        "subject": "{name}, sobre o que conversamos ontem no Summit",
        "body": """Olá {name},

{demo_content}

A Vigil.AI resolve exatamente o que foi discutido ontem: visibilidade contínua sobre postura de segurança, priorização inteligente de riscos e relatórios automáticos de conformidade — tudo integrado ao seu ambiente atual, sem substituir o que já funciona.

Para {company}, o caso de uso mais direto seria {sector_content}.

Consigo mostrar isso em 30 minutos, com uma demonstração no ambiente de vocês.

{custom_note}

Ana Beatriz Costa
Account Executive, Vigil.AI"""
    },

    "pain_point": {
        "subject": "Uma pergunta direta, {name}",
        "body": """Olá {name},

Após o Vigil Summit, ficou uma pergunta que quero trazer diretamente para você:

{pain_point_content}

Não estou pedindo para agendar uma demo agora. Só quero entender se estou mapeando o problema certo antes de incomodar sua agenda.

Me responde em duas linhas?

{custom_note}

Ana Beatriz Costa
Account Executive, Vigil.AI"""
    },

    "breakup": {
        "subject": "Última mensagem, {name}",
        "body": """Olá {name},

Tentei entrar em contato algumas vezes desde o Vigil Summit, mas entendo que o timing pode não ser ideal.

Vou deixar o espaço livre por enquanto. Se em algum momento — agora ou daqui a meses — fizer sentido conversar sobre como empresas do setor de {sector} estão resolvendo os desafios que discutimos no Summit, é só responder este email.

{custom_note}

Um abraço,
Ana Beatriz Costa
Account Executive, Vigil.AI"""
    },

    # ── PÓS-EVENTO — NO-SHOW ──────────────────────────────────────────────────

    "no_show_missed": {
        "subject": "{name}, sentimos sua falta — o que aconteceu no Summit",
        "body": """Olá {name},

Notamos que você não pôde comparecer ao Vigil Summit ontem. Imprevistos acontecem.

Para não perder o conteúdo, aqui vai um resumo dos principais pontos do dia:

{event_highlights}

O nível das discussões — especialmente nas mesas redondas por setor — foi acima do esperado. Vários participantes saíram com clareza sobre o que priorizar em segurança nos próximos 12 meses.

{custom_note}

Posso fazer uma sessão privada para você com os mesmos temas. Sem custo, sem compromisso.

Ana Beatriz Costa
Account Executive, Vigil.AI"""
    },

    "no_show_demo_offer": {
        "subject": "Demo privada: o que você teria visto no Vigil Summit",
        "body": """Olá {name},

Preparei uma sessão exclusiva para quem não pôde comparecer ao Vigil Summit.

Em 30 minutos, você vê:

{demo_preview}

Tudo adaptado para o contexto de {company} no setor de {sector}.

{custom_note}

Ana Beatriz Costa
Account Executive, Vigil.AI"""
    },

    "no_show_final": {
        "subject": "Último contato, {name}",
        "body": """Olá {name},

Esta é minha última tentativa de contato.

Se quiser ver como a Vigil.AI funciona para empresas como a {company} — detecção de vulnerabilidades, dashboard de postura e conformidade automatizada — este é o link para agendar: {custom_note}

Caso contrário, não incomodaremos mais.

Atenciosamente,
Ana Beatriz Costa
Account Executive, Vigil.AI"""
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# Conteúdo por setor — usado nos templates via {sector_content}
# ─────────────────────────────────────────────────────────────────────────────

_SECTOR_CONTENT_RAW = {
    "financial": (
        "Zero Trust para open banking e PIX: como segmentar acesso sem travar operações. "
        "Conformidade LGPD + BACEN em ambientes legados. "
        "Priorização inteligente de vulnerabilidades em infraestrutura regulada."
    ),
    "manufacturing": (
        "Proteção de redes OT/ICS sem parar a produção. "
        "Segmentação de chão de fábrica conectado (Indústria 4.0). "
        "Continuidade operacional frente a ransomware em ambientes industriais."
    ),
    "healthcare": (
        "Proteção de dados de pacientes: LGPD + HIPAA na prática. "
        "Segurança em sistemas hospitalares integrados (PACS, HIS, prontuário digital). "
        "Gestão de risco em infraestrutura crítica de saúde."
    ),
    "government": (
        "Conformidade com LGPD governamental e frameworks do GSI. "
        "Proteção de dados sensíveis em sistemas de gestão pública. "
        "Resposta a incidentes em infraestrutura crítica nacional."
    ),
    "technology": (
        "Segurança em pipelines CI/CD e ambientes cloud-native. "
        "Detecção de ameaças em tempo real com IA aplicada. "
        "Resposta a incidentes em infraestrutura distribuída e multi-cloud."
    ),
    "retail": (
        "Proteção de dados de consumidores: PCI-DSS + LGPD integrados. "
        "Segurança em e-commerce e prevenção a fraudes digitais. "
        "Conformidade em ambientes omnichannel com alto volume de transações."
    ),
    "energy": (
        "Segurança em infraestrutura crítica: SCADA e sistemas de controle. "
        "Proteção de redes elétricas frente a ameaças APT. "
        "Conformidade regulatória: ANEEL, ONS e frameworks setoriais."
    ),
    "education": (
        "Proteção de dados de alunos e pesquisadores (LGPD aplicada). "
        "Segurança em ambientes EaD e infraestrutura de pesquisa. "
        "Gestão de identidade em larga escala para corporações educacionais."
    ),
    "telecom": (
        "Segurança de rede em larga escala: SS7, VoIP e infraestrutura crítica. "
        "Proteção contra ataques DDoS em operadoras. "
        "Conformidade com regulações da ANATEL e frameworks setoriais."
    ),
}

_APOLLO_TO_SECTOR: dict[str, str] = {
    "financial services": "financial", "banking": "financial", "insurance": "financial",
    "investment banking": "financial", "capital markets": "financial",
    "venture capital & private equity": "financial", "accounting": "financial",
    "manufacturing": "manufacturing", "automotive": "manufacturing",
    "chemicals": "manufacturing", "mining & metals": "manufacturing",
    "industrial automation": "manufacturing",
    "mechanical or industrial engineering": "manufacturing",
    "hospital & health care": "healthcare", "health, wellness and fitness": "healthcare",
    "medical devices": "healthcare", "pharmaceuticals": "healthcare",
    "biotechnology": "healthcare", "medical practice": "healthcare",
    "government administration": "government", "defense & space": "government",
    "law enforcement": "government", "public safety": "government",
    "political organization": "government",
    "information technology and services": "technology",
    "computer software": "technology", "internet": "technology",
    "computer & network security": "technology", "semiconductors": "technology",
    "computer hardware": "technology",
    "telecommunications": "telecom", "wireless": "telecom",
    "retail": "retail", "consumer goods": "retail",
    "food & beverages": "retail", "e-commerce": "retail",
    "oil & energy": "energy", "renewables & environment": "energy",
    "utilities": "energy",
    "education management": "education", "higher education": "education",
    "e-learning": "education",
}


def _resolve_sector_content(sector: str | None) -> str:
    default = (
        "Gestão de riscos cibernéticos com visibilidade contínua. "
        "Conformidade LGPD integrada ao ambiente de TI. "
        "Priorização inteligente de vulnerabilidades com IA."
    )
    if not sector:
        return default
    key = _APOLLO_TO_SECTOR.get(sector.lower().strip())
    if key:
        return _SECTOR_CONTENT_RAW[key]
    sl = sector.lower()
    for apollo_key, normalized in _APOLLO_TO_SECTOR.items():
        if apollo_key in sl or sl in apollo_key:
            return _SECTOR_CONTENT_RAW[normalized]
    return default


async def send_email(lead: dict, template_key: str, custom_note: str = "", phase: str = "pre_event", cta_url: str | None = None) -> dict:
    resend.api_key = settings.resend_api_key

    enrichment = lead.get("lead_enrichment") or {}
    if isinstance(enrichment, list):
        enrichment = enrichment[0] if enrichment else {}

    sector = enrichment.get("sector", "")
    sector_content = _resolve_sector_content(sector)

    template = TEMPLATES.get(template_key, TEMPLATES["welcome"])

    raw_name = lead.get("name") or "Prezado(a)"
    first_name = raw_name.split()[0] if raw_name.split() else "Prezado(a)"

    role = enrichment.get("real_role") or lead.get("role") or "profissional de segurança"
    company = enrichment.get("company") or lead.get("company") or "sua empresa"

    safe_custom_note = custom_note.replace("{", "{{").replace("}", "}}")

    ctx = {
        "name": first_name,
        "role": role,
        "company": company,
        "sector": sector or "tecnologia",
        "sector_content": sector_content,
        "custom_note": safe_custom_note,
        "role_personalization": (
            f"Como {role} em {company}, o Summit foi estruturado para os desafios que você enfrenta hoje."
            if role and company else
            "O Summit foi estruturado para líderes de segurança que tomam decisões de alto impacto."
        ),
        "event_context": f"segurança aplicada ao setor de {sector or 'tecnologia'}",
        "demo_context": "a conversa que começamos no Summit",
        "demo_content": (
            f"Você esteve no Vigil Summit e viu em primeira mão os desafios que discutimos. "
            f"Para {company} no setor de {sector or 'tecnologia'}, a Vigil.AI resolve especificamente: {sector_content}"
        ),
        "pain_point_content": (
            f"Qual é o maior gargalo de segurança que você enfrenta hoje em {company}? "
            f"Conformidade, visibilidade sobre vulnerabilidades ou resposta a incidentes?"
        ),
        "event_highlights": (
            "→ Zero Trust na prática: cases reais de implementação em 90 dias\n"
            "→ IA em detecção de ameaças: o que funciona além do hype\n"
            "→ Conformidade LGPD/ISO 27001: automação que reduz 60% do esforço manual\n"
            "→ Mesas redondas setoriais: discussões diretas entre pares do seu setor"
        ),
        "demo_preview": (
            "dashboard de postura de segurança em tempo real, "
            "priorização automática de vulnerabilidades com contexto de negócio, "
            "e relatórios de conformidade prontos para auditoria"
        ),
    }

    subject = template["subject"].format(**ctx)
    body = template["body"].format(**ctx)

    # HTML é best-effort: se render falhar, envia só texto (nunca bloqueia o envio).
    try:
        html_body = render_html(template_key, ctx, cta_url)
    except Exception:
        html_body = None

    sb = get_supabase()
    now = datetime.now(timezone.utc).isoformat()

    pending_row = await asyncio.to_thread(lambda: sb.table("messages").insert({
        "lead_id": lead["id"],
        "event_id": lead.get("event_id"),
        "channel": "EMAIL",
        "direction": "OUT",
        "subject": subject,
        "body": body,
        "funnel_stage": lead.get("stage", "REGISTERED"),
        "resend_id": None,
        "status": "PENDING",
        "sent_at": now,
    }).execute())

    message_id = pending_row.data[0]["id"]

    try:
        payload = {
            "from": settings.resend_from_email,
            "to": [lead["email"]],
            "subject": subject,
            "text": body,
        }
        if html_body:
            payload["html"] = html_body
        response = await asyncio.to_thread(lambda: resend.Emails.send(payload))

        await asyncio.to_thread(lambda: sb.table("messages").update({
            "resend_id": response.get("id"),
            "status": "SENT",
        }).eq("id", message_id).execute())

        return response
    except Exception as e:
        await asyncio.to_thread(lambda: sb.table("messages").update({
            "status": "FAILED",
        }).eq("id", message_id).execute())
        return {"error": str(e)}
