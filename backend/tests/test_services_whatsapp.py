# backend/tests/test_services_whatsapp.py
from unittest.mock import patch, MagicMock


async def test_simulated_when_no_evolution_key():
    from app.config import settings
    from app.services.whatsapp import send_whatsapp_message

    sb = MagicMock()
    inserted = {}
    def capture_insert(row):
        inserted.update(row)
        return MagicMock(execute=MagicMock(return_value=MagicMock()))
    sb.table.return_value.insert.side_effect = capture_insert

    with patch.object(settings, "evolution_api_url", ""), \
         patch.object(settings, "evolution_api_key", ""):
        out = await send_whatsapp_message({"id": "lead-001", "phone": "+5511999"}, "Olá!", sb)

    assert out == {"simulated": True}
    assert inserted["channel"] == "WHATSAPP"
    assert inserted["status"] == "SIMULATED"
    assert inserted["body"] == "Olá!"
