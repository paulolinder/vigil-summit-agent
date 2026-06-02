from unittest.mock import patch, MagicMock


def _lead():
    return {"id": "lead-1", "email": "a@b.com", "name": "Ana", "company": "BankCo",
            "role": "CISO", "stage": "REGISTERED", "event_id": "ev-1",
            "lead_enrichment": {"sector": "financial services", "real_role": "CISO", "company": "BankCo"}}


def _sb():
    sb = MagicMock()
    sb.table.return_value.insert.return_value.execute.return_value.data = [{"id": "msg-1"}]
    sb.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
    return sb


async def test_send_email_sends_html_and_text_and_stores_text():
    from app.services import resend_service
    sb = _sb()
    sent = {}
    def fake_send(payload):
        sent.update(payload)
        return {"id": "resend-1"}
    with patch.object(resend_service, "get_supabase", return_value=sb), \
         patch.object(resend_service, "sign_confirm_token", return_value="lead-1.fakesig"), \
         patch.object(resend_service.resend.Emails, "send", side_effect=fake_send):
        await resend_service.send_email(_lead(), "welcome", custom_note="Olá", phase="pre_event")

    assert "html" in sent and "text" in sent
    assert "<table" in sent["html"].lower()       # HTML real
    assert "<table" not in sent["text"].lower()   # text puro
    # messages.body recebeu TEXTO (não HTML): procura a chamada de insert
    insert_args = str(sb.table.return_value.insert.call_args)
    assert "<table" not in insert_args


async def test_send_email_falls_back_to_text_if_render_raises():
    from app.services import resend_service
    sb = _sb()
    sent = {}
    with patch.object(resend_service, "get_supabase", return_value=sb), \
         patch.object(resend_service, "render_html", side_effect=RuntimeError("boom")), \
         patch.object(resend_service.resend.Emails, "send", side_effect=lambda p: sent.update(p) or {"id": "r"}):
        result = await resend_service.send_email(_lead(), "welcome", custom_note="x")

    assert "text" in sent           # ainda enviou
    assert "html" not in sent       # render falhou → só texto
    assert "error" not in result    # não falhou
