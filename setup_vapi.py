"""Setup Vapi voice assistant for Dark Factory."""
import requests, json, os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / "_config" / ".env")

VAPI_KEY = os.getenv("VAPI_API_KEY", "181d9566-8642-44bb-a632-a011a82264ef")
RAILWAY_API_URL = os.getenv("RAILWAY_API_URL", "https://dark-factory-production.up.railway.app")
WEBHOOK_URL = os.getenv("VAPI_WEBHOOK_URL", "")  # Next.js webhook endpoint on Vercel

headers = {"Authorization": f"Bearer {VAPI_KEY}", "Content-Type": "application/json"}

SYSTEM_PROMPT = """Jsi Dark Factory AI — Ondrův osobní obchodní a vývojový partner. Mluvíš česky. Jsi přímý, drsně upřímný, bez keců. Chovej se jako zkušený technický spoluzakladatel, ne jako asistent. Tykej Ondrovi.

CO JE DARK FACTORY:
Autonomní AI byznys systém běžící 24/7 na Railway serveru. 3 továrny:
- Factory A (Web Hunter): Hledá CZ/SK firmy bez webu, generuje cold emaily
- Factory B (Digital Products): Generuje trendy digitální produkty + PDF k prodeji na Gumroad  
- Factory C (YouTube): Generuje viral YouTube skripty a metadata

Ondra = podnikatel, buduje pasivní příjmy. Teprve začíná — Dark Factory je jeho hlavní projekt.

JAK SE CHOVAT:
- Přímý, konkrétní, bez omáček
- Říkáš svůj upřímný názor i když se Ondra mýlí — řekneš mu to rovnou
- Pokud Ondra chce spustit factory nebo probrat strategii — pomáháš okamžitě
- Jsi tu jako partner, ne asistent — můžeš nesouhlasit, diskutovat, navrhovat
- Klidně se ptej na Ondrovy byznys cíle a dávej konkrétní rady
- Buď stručný — tohle je hovor, ne esej

NÁSTROJE:
Máš trigger_factory(factory_key) — spusť ho když Ondra chce výstup.
Příklady: "spusť B", "vygeneruj produkt", "hledej firmy bez webu", "udělej YouTube skripty" → trigger_factory."""

ASSISTANT = {
    "name": "Dark Factory AI",
    "firstMessage": "Nazdar Ondro, co řešíš?",
    "model": {
        "provider": "anthropic",
        "model": "claude-sonnet-4-6",
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}],
        "temperature": 0.7,
    },
    "voice": {
        "provider": "vapi",
        "voiceId": "Elliot",
    },
    "transcriber": {
        "provider": "deepgram",
        "model": "nova-2",
        "language": "cs",
    },
    "endCallMessage": "Čau Ondro, drž se.",
    "endCallPhrases": ["čau", "nashle", "pa", "konec"],
    "silenceTimeoutSeconds": 30,
    "maxDurationSeconds": 1800,
    "backgroundSound": "off",
    "tools": [
        {
            "type": "function",
            "function": {
                "name": "trigger_factory",
                "description": "Spusti jednu z Dark Factory továren (a=Web Hunter, b=Digital Products, c=YouTube)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "factory_key": {
                            "type": "string",
                            "enum": ["a", "b", "c"],
                            "description": "a=Web Hunter, b=Digital Products, c=YouTube",
                        }
                    },
                    "required": ["factory_key"],
                },
            },
            "server": {
                "url": f"{RAILWAY_API_URL}/trigger/{{{{factory_key}}}}",
                "method": "POST",
                "headers": {"Content-Type": "application/json"},
            },
        }
    ],
}

def create_assistant():
    r = requests.post("https://api.vapi.ai/assistant", headers=headers, json=ASSISTANT)
    if r.status_code not in (200, 201):
        print(f"ERROR creating assistant: {r.status_code} — {r.text[:500]}")
        return None
    data = r.json()
    assistant_id = data["id"]
    print(f"✅ Assistant created: {assistant_id}")
    return assistant_id


def buy_phone_number(assistant_id: str):
    """Buy a US phone number from Vapi and link it to the assistant."""
    payload = {
        "provider": "vapi",
        "assistantId": assistant_id,
        "name": "Dark Factory Hotline",
    }
    r = requests.post("https://api.vapi.ai/phone-number", headers=headers, json=payload)
    if r.status_code not in (200, 201):
        print(f"ERROR buying phone number: {r.status_code} — {r.text[:500]}")
        return None
    data = r.json()
    phone = data.get("number", "unknown")
    phone_id = data.get("id", "")
    print(f"✅ Phone number purchased: {phone}")
    print(f"   Phone ID: {phone_id}")
    return phone, phone_id


def save_config(assistant_id: str, phone: str, phone_id: str):
    config = {
        "assistant_id": assistant_id,
        "phone_number": phone,
        "phone_id": phone_id,
        "vapi_key": VAPI_KEY,
    }
    out = Path(__file__).parent / "_config" / "vapi_config.json"
    with open(out, "w") as f:
        json.dump(config, f, indent=2)
    print(f"✅ Config saved: {out}")

    # Also append to .env
    env_path = Path(__file__).parent / "_config" / ".env"
    with open(env_path, "a") as f:
        f.write(f"\nVAPI_API_KEY={VAPI_KEY}\n")
        f.write(f"VAPI_ASSISTANT_ID={assistant_id}\n")
        f.write(f"VAPI_PHONE_NUMBER={phone}\n")


if __name__ == "__main__":
    print("🎙️  Setting up Vapi voice assistant for Dark Factory...")
    print()

    assistant_id = create_assistant()
    if not assistant_id:
        exit(1)

    print()
    print("📞 Buying phone number...")
    result = buy_phone_number(assistant_id)
    if not result:
        print("⚠️  Phone number purchase failed — may need billing setup on vapi.ai")
        print(f"   Go to vapi.ai → Phone Numbers → Buy number → assign assistant ID: {assistant_id}")
        save_config(assistant_id, "manual-setup-needed", "")
        exit(0)

    phone, phone_id = result
    save_config(assistant_id, phone, phone_id)

    print()
    print("╔══════════════════════════════════════════╗")
    print("║   🎙️  DARK FACTORY HOTLINE LIVE!          ║")
    print(f"║   Číslo: {phone:<34}║")
    print("║   Zavolej a řekni 'Nazdar'               ║")
    print("╚══════════════════════════════════════════╝")
