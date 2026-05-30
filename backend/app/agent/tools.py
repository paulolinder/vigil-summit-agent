TOOLS = [
    {
        "name": "enrich_lead",
        "description": "Enriquece o perfil do lead via Apollo.io com cargo real, setor, tamanho e technographics. Sempre chame isso primeiro se stage=REGISTERED.",
        "input_schema": {
            "type": "object",
            "properties": {
                "lead_id": {"type": "string", "description": "UUID do lead"}
            },
            "required": ["lead_id"],
        },
    },
    {
        "name": "send_pre_event_msg",
        "description": "Envia email pré-evento personalizado via Resend.",
        "input_schema": {
            "type": "object",
            "properties": {
                "lead_id": {"type": "string"},
                "template": {
                    "type": "string",
                    "enum": [
                        "welcome", "vip_briefing", "warmup", "confirmation_request",
                        "confirmation_followup", "agenda", "logistics", "day_reminder",
                    ],
                },
                "custom_note": {"type": "string", "description": "Nota personalizada inserida no template"},
            },
            "required": ["lead_id", "template"],
        },
    },
    {
        "name": "check_engagement",
        "description": "Verifica se o lead abriu e/ou clicou no último email enviado.",
        "input_schema": {
            "type": "object",
            "properties": {
                "lead_id": {"type": "string"}
            },
            "required": ["lead_id"],
        },
    },
    {
        "name": "send_whatsapp",
        "description": "Envia mensagem WhatsApp via Evolution API. Use SOMENTE se whatsapp_opted_in=True no contexto do sistema.",
        "input_schema": {
            "type": "object",
            "properties": {
                "lead_id": {"type": "string"},
                "text": {"type": "string", "description": "Texto da mensagem WhatsApp"},
            },
            "required": ["lead_id", "text"],
        },
    },
    {
        "name": "send_followup",
        "description": "Envia email de follow-up pós-evento via Resend.",
        "input_schema": {
            "type": "object",
            "properties": {
                "lead_id": {"type": "string"},
                "template": {
                    "type": "string",
                    "enum": [
                        "thank_you", "demo_followup", "pain_point", "breakup",
                        "no_show_missed", "no_show_demo_offer", "no_show_final",
                    ],
                },
                "custom_note": {"type": "string"},
            },
            "required": ["lead_id", "template"],
        },
    },
    {
        "name": "update_lead_stage",
        "description": "Atualiza o estágio do lead no funil.",
        "input_schema": {
            "type": "object",
            "properties": {
                "lead_id": {"type": "string"},
                "stage": {
                    "type": "string",
                    "enum": [
                        "REGISTERED", "ENRICHED", "CONFIRMED", "ATTENDED",
                        "NO_SHOW", "MEETING_SCHEDULED", "CONVERTED", "OPTED_OUT",
                    ],
                },
            },
            "required": ["lead_id", "stage"],
        },
    },
    {
        "name": "schedule_job",
        "description": "Agenda um job futuro para o lead (ex: follow-up D+3). Condições suportadas: only_if_stage, skip_if_opened, only_if_not_clicked.",
        "input_schema": {
            "type": "object",
            "properties": {
                "lead_id": {"type": "string"},
                "job_type": {"type": "string", "description": "Ex: FOLLOWUP_D3, CONFIRMATION_T14"},
                "run_at": {"type": "string", "description": "ISO 8601 UTC datetime"},
                "condition": {
                    "type": "object",
                    "description": 'Ex: {"only_if_stage": "ENRICHED"} ou {"skip_if_opened": true}',
                },
            },
            "required": ["lead_id", "job_type", "run_at"],
        },
    },
    {
        "name": "schedule_meeting",
        "description": "Gera link de agendamento Cal.com e atualiza stage para MEETING_SCHEDULED.",
        "input_schema": {
            "type": "object",
            "properties": {
                "lead_id": {"type": "string"},
                "context_note": {"type": "string", "description": "Nota de contexto para o email com o link"},
            },
            "required": ["lead_id"],
        },
    },
]
