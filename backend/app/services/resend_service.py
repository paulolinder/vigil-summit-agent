import asyncio
import resend
from app.config import settings
from app.db.client import get_supabase
from datetime import datetime, timezone

TEMPLATES = {
    "welcome": {
        "subject": "{name}, sua inscrição no Vigil Summit foi confirmada",
        "body": """Olá {name},

Sua inscrição no Vigil Summit — Segurança para a Era da IA foi confirmada com sucesso.

{role_personalization}

Em breve você receberá mais detalhes sobre a programação e logística.

Nos vemos lá,
Equipe Vigil.AI"""
    },
    "vip_briefing": {
        "subject": "{name}, preparamos um briefing exclusivo para você",
        "body": """Olá {name},

Como {role} na {company}, preparamos um briefing exclusivo sobre os tópicos mais relevantes para {sector}.

{sector_content}

{custom_note}

Equipe Vigil.AI"""
    },
    # CORRIGIDO: template warmup adicionado (estava na tool definition mas ausente aqui)
    "warmup": {
        "subject": "{name}, o que esperar do Vigil Summit",
        "body": """Olá {name},

Faltam algumas semanas para o Vigil Summit e queremos que você chegue preparado.

Para profissionais de segurança e TI no setor de {sector}, os temas mais relevantes este ano são:

{sector_content}

Nos vemos em breve,
Equipe Vigil.AI"""
    },
    "confirmation_request": {
        "subject": "{name}, sua vaga no Vigil Summit está reservada — confirme presença",
        "body": """Olá {name},

Faltam 14 dias para o Vigil Summit e sua vaga ainda está reservada.

Como {role} na {company}, você vai encontrar no Summit exatamente o que move a agenda de segurança do {sector} agora.

{sector_content}

Confirme sua presença respondendo este email com "Confirmo".

{custom_note}

Nos vemos em 14 dias,
Equipe Vigil.AI"""
    },
    # CORRIGIDO: template confirmation_followup adicionado
    "confirmation_followup": {
        "subject": "{name}, ainda dá tempo de confirmar — Vigil Summit em 10 dias",
        "body": """Olá {name},

Notamos que você ainda não confirmou presença no Vigil Summit, que acontece em 10 dias.

{sector_content}

Sua vaga está reservada, mas precisamos da sua confirmação para garantir o credenciamento.

Responda "Confirmo" para garantir seu lugar.

{custom_note}

Equipe Vigil.AI"""
    },
    # CORRIGIDO: template agenda adicionado
    "agenda": {
        "subject": "{name}, sua agenda personalizada para o Vigil Summit",
        "body": """Olá {name},

Com base no seu perfil como {role} na {company}, separamos as sessões mais relevantes para você no Vigil Summit:

{sector_content}

Prepare suas perguntas — será um dia intenso.

{custom_note}

Equipe Vigil.AI"""
    },
    "logistics": {
        "subject": "Vigil Summit — tudo que você precisa saber para amanhã",
        "body": """Olá {name},

O Vigil Summit acontece amanhã! Aqui estão as informações de acesso:

📍 Local: Centro de Convenções SP, Av. Paulista, 1000
🕘 Início: 9h00 (credenciamento a partir das 8h30)
🎫 Leve: documento com foto e confirmação de inscrição
🚗 Estacionamento: disponível no local (validamos até 8h)

{custom_note}

Até amanhã,
Equipe Vigil.AI"""
    },
    "day_reminder": {
        "subject": "Hoje é o dia — Vigil Summit começa em breve",
        "body": """Bom dia, {name}!

O Vigil Summit começa hoje às 9h. Credenciamento aberto a partir das 8h30.

{custom_note}

Nos vemos lá,
Equipe Vigil.AI"""
    },
    "thank_you": {
        "subject": "{name}, obrigado por estar no Vigil Summit",
        "body": """Olá {name},

Foi um prazer ter você no Vigil Summit ontem.

{event_context}

Gostaríamos de continuar a conversa. {custom_note}

Um abraço,
Equipe Vigil.AI"""
    },
    "demo_followup": {
        "subject": "{name}, {demo_context}",
        "body": """Olá {name},

{demo_content}

Consigo te mostrar como a Vigil.AI se integraria ao ambiente real de vocês em 30 minutos?

{custom_note}

Ana Beatriz Costa
Account Executive, Vigil.AI"""
    },
    "pain_point": {
        "subject": "Uma pergunta rápida, {name}",
        "body": """Olá {name},

{pain_point_content}

Vale uma conversa de 30 minutos?

{custom_note}

Ana Beatriz Costa
Account Executive, Vigil.AI"""
    },
    "breakup": {
        "subject": "Última mensagem, {name}",
        "body": """Olá {name},

Tentei entrar em contato algumas vezes após o Vigil Summit.

Entendo que o timing pode não ser ideal. Vou deixar o espaço livre — se em algum momento quiser conversar sobre como a Vigil.AI pode ajudar a {company}, é só responder este email.

{custom_note}

Um abraço,
Ana Beatriz Costa"""
    },
    "no_show_missed": {
        "subject": "{name}, sentimos sua falta no Vigil Summit",
        "body": """Olá {name},

Notamos que você não pôde comparecer ao Vigil Summit. Entendemos que imprevistos acontecem.

Os principais insights do evento: {event_highlights}

Gostaríamos de apresentar a plataforma Vigil.AI em uma sessão exclusiva para você. {custom_note}

Equipe Vigil.AI"""
    },
    "no_show_demo_offer": {
        "subject": "Demo privada da Vigil.AI para {name}",
        "body": """Olá {name},

Como você não pôde participar do Vigil Summit, gostaríamos de oferecer uma demo privada da plataforma Vigil.AI.

Em 30 minutos, você vê o que os participantes presenciais viram: {demo_preview}

{custom_note}

Ana Beatriz Costa
Account Executive, Vigil.AI"""
    },
    "no_show_final": {
        "subject": "Último convite — Demo Vigil.AI para {name}",
        "body": """Olá {name},

Esta é nossa última tentativa de contato.

Se quiser ver como a Vigil.AI funciona para empresas como a {company}, este é o link: {custom_note}

Caso contrário, não incomodaremos mais.

Atenciosamente,
Equipe Vigil.AI"""
    },
}

SECTOR_CONTENT = {
    "Financial Services": "conformidade LGPD na prática, Zero Trust para open banking e priorização inteligente de vulnerabilidades em ambiente regulado",
    "Manufacturing": "segurança OT/ICS para chão de fábrica conectado, proteção de redes industriais e continuidade operacional",
    "Healthcare": "proteção de dados de pacientes (LGPD + HIPAA), segurança em sistemas hospitalares e gestão de risco em infraestrutura crítica",
    "Government": "conformidade com LGPD governamental, proteção de dados sensíveis e frameworks de segurança para setor público",
}

async def send_email(lead: dict, template_key: str, custom_note: str = "", phase: str = "pre_event") -> dict:
    # lazy: evita falha na importação quando RESEND_API_KEY não está no ambiente de teste
    resend.api_key = settings.resend_api_key

    enrichment = lead.get("lead_enrichment") or {}
    if isinstance(enrichment, list):
        enrichment = enrichment[0] if enrichment else {}

    sector = enrichment.get("sector", "tecnologia")
    sector_content = SECTOR_CONTENT.get(sector, "gestão de riscos e conformidade em segurança cibernética")

    template = TEMPLATES.get(template_key, TEMPLATES["welcome"])

    # CORRIGIDO: name.split()[0] lançava IndexError se name fosse string vazia
    raw_name = lead.get("name") or "Prezado(a)"
    first_name = raw_name.split()[0] if raw_name.split() else "Prezado(a)"

    # Escape curly braces in AI-generated text before str.format() to prevent KeyError/ValueError
    safe_custom_note = custom_note.replace("{", "{{").replace("}", "}}")

    ctx = {
        "name": first_name,
        "role": enrichment.get("real_role") or lead.get("role", "profissional"),
        "company": enrichment.get("company") or lead.get("company", "sua empresa"),
        "sector": sector,
        "sector_content": sector_content,
        "custom_note": safe_custom_note,
        "role_personalization": f"Como {lead.get('role', 'profissional')} em {lead.get('company', 'sua empresa')}, o Summit foi pensado para você.",
        "event_context": f"Esperamos que a programação tenha sido relevante para seus desafios em {sector}.",
        "demo_context": "sobre o que você viu ontem",
        "demo_content": f"Você demonstrou interesse em nossa plataforma durante o Vigil Summit. Para {lead.get('company', 'sua empresa')} no setor de {sector}, o caso de uso seria especialmente relevante.",
        "pain_point_content": f"Qual é o maior desafio de segurança que você enfrenta hoje na {lead.get('company', 'sua empresa')}?",
        "event_highlights": "Zero Trust na prática, IA na priorização de vulnerabilidades e conformidade automatizada",
        "demo_preview": "detecção contínua de vulnerabilidades, dashboard de postura de segurança e relatórios automáticos de conformidade",
    }

    subject = template["subject"].format(**ctx)
    body = template["body"].format(**ctx)

    try:
        payload = {
            "from": settings.resend_from_email,
            "to": [lead["email"]],
            "subject": subject,
            "text": body,
        }
        response = await asyncio.to_thread(lambda: resend.Emails.send(payload))

        sb = get_supabase()
        row = {
            "lead_id": lead["id"],
            "event_id": lead.get("event_id"),
            "channel": "EMAIL",
            "direction": "OUT",
            "subject": subject,
            "body": body,
            "funnel_stage": lead.get("stage", "REGISTERED"),
            "resend_id": response.get("id"),
            "sent_at": datetime.now(timezone.utc).isoformat(),
        }
        await asyncio.to_thread(lambda: sb.table("messages").insert(row).execute())

        return response
    except Exception as e:
        return {"error": str(e)}
