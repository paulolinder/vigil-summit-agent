"""
Cria 3 personas sintéticas para demonstração do funil completo.
Uso: cd backend && python scripts/seed_personas.py
Pré-requisito: backend rodando em localhost:8000
"""
import asyncio
import os
import httpx

API_KEY = os.environ.get("API_KEY", "vigil-secret-key-2026")

BASE_URL = "http://localhost:8000"

PERSONAS = [
    {
        "name": "Maria Santos",
        "email": "maria.santos.demo@vigil-test.com",
        "company": "Banco Itararé",
        "role": "CISO",
        "phone": "+5511999990001",
        "scenario": "ATTENDED",
    },
    {
        "name": "Carlos Mendes",
        "email": "carlos.mendes.demo@vigil-test.com",
        "company": "TechManufatura SA",
        "role": "CTO",
        "phone": "+5511999990002",
        "scenario": "NO_SHOW",
    },
    {
        "name": "Pedro Alves",
        "email": "pedro.alves.demo@vigil-test.com",
        "company": "Clínica São Paulo",
        "role": "Diretor de TI",
        "phone": None,
        "scenario": "REGISTERED",
    },
]


async def seed():
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(f"{BASE_URL}/api/events/")
        events = resp.json()
        if not events:
            print("ERRO: nenhum evento encontrado. Execute o SQL da migration primeiro.")
            return
        event_id = events[0]["id"]
        print(f"Usando evento: {events[0]['name']} ({event_id})")

        for persona in PERSONAS:
            print(f"\nCriando {persona['name']} ({persona['scenario']})...")

            resp = await client.post(f"{BASE_URL}/api/leads/", json={
                "event_id": event_id,
                "name": persona["name"],
                "email": persona["email"],
                "company": persona["company"],
                "role": persona["role"],
                "phone": persona["phone"],
                "consent": True,
                "whatsapp_consent": bool(persona["phone"]),
            })

            if resp.status_code == 409:
                print(f"  ↳ Já existe, pulando.")
                continue
            if resp.status_code != 201:
                print(f"  ↳ ERRO {resp.status_code}: {resp.text}")
                continue

            lead_id = resp.json()["id"]
            print(f"  ↳ Criado: lead_id={lead_id}")

            await asyncio.sleep(3)

            if persona["scenario"] == "ATTENDED":
                resp2 = await client.post(
                    f"{BASE_URL}/api/leads/{lead_id}/checkin",
                    headers={"X-API-Key": API_KEY},
                )
                print(f"  ↳ Check-in: {resp2.status_code}")

            elif persona["scenario"] == "NO_SHOW":
                resp2 = await client.post(
                    f"{BASE_URL}/api/leads/{lead_id}/no-show",
                    headers={"X-API-Key": API_KEY},
                )
                print(f"  ↳ No-show: {resp2.status_code}")

    print("\n✓ Seed concluído. Verificar no dashboard ou Supabase.")


if __name__ == "__main__":
    asyncio.run(seed())
