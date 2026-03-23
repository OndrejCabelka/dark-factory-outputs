# 🚀 WebHunter — Deploy Checklist

## Stav
- ✅ Supabase DB live (353 leadů, 27+ návrhů vygenerováno)
- ✅ GitHub Pages: navrhy live na `ondrejcabelka.github.io/dark-factory-outputs/navrhy/`
- ✅ Frontend build: OK, všechny API routes jsou dynamic
- ✅ Railway: dashboard Next.js JIŽ běží — stačí přidat env vars
- ⚠️ Resend: **nutno registrovat + ověřit doménu**

---

## ⚡ NEJRYCHLEJŠÍ CESTA (2 minuty) — Začni volat ještě dnes

Dashboard je **již nasazen** na: `https://dark-factory-production.up.railway.app`

Nefunguje kvůli chybějícím env vars. Stačí přidat na Railway:

1. Jdi na **[railway.app](https://railway.app)** → projekt Dark Factory → karta **Variables**
2. Přidej tyto 4 klíče a klikni Save:

| Klíč | Hodnota |
|------|---------|
| `SUPABASE_URL` | `https://wqlbbxhieboybyvwdvjr.supabase.co` |
| `SUPABASE_ANON_KEY` | `sb_publishable_nl9YngghvSmjjCoqOjtvzg_Sez5XXH-` |
| `NEXT_PUBLIC_SUPABASE_URL` | `https://wqlbbxhieboybyvwdvjr.supabase.co` |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | `sb_publishable_nl9YngghvSmjjCoqOjtvzg_Sez5XXH-` |

3. Railway automaticky redeploys (cca 2 min) → otevři dashboard → **27 leadů připravených k volání**

---

---

## 1. Vercel — Next.js Dashboard (5 minut)

```bash
# V terminálu:
cd /Users/ondrejcabelka/Desktop/DarkFactory/frontend
npx vercel login        # přihlásíš se přes browser
npx vercel --prod       # nasadí na produkci
```

Vercel se zeptá na nastavení — vždy potvrď defaulty.
Po deployi dostaneš URL jako `dark-factory-frontend.vercel.app`.

### Env vars na Vercel (Settings → Environment Variables):
| Klíč | Hodnota |
|------|---------|
| `SUPABASE_URL` | `https://wqlbbxhieboybyvwdvjr.supabase.co` |
| `SUPABASE_ANON_KEY` | `sb_publishable_nl9YngghvSmjjCoqOjtvzg_Sez5XXH-` |
| `NEXT_PUBLIC_SUPABASE_URL` | `https://wqlbbxhieboybyvwdvjr.supabase.co` |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | `sb_publishable_nl9YngghvSmjjCoqOjtvzg_Sez5XXH-` |
| `RESEND_API_KEY` | `re_TVŮJ_KLÍČ` (viz bod 3) |
| `MAIL_FROM` | `ondrej@tvoje-domena.cz` |
| `BACKEND_URL` | URL Python backendu z Railway (viz bod 2) |

Po nastavení env vars: **Redeploy** (Settings → Deployments → Redeploy).

---

## 2. Railway — Python Orchestrator

Jdi na [railway.app](https://railway.app) → projekt Dark Factory.

### 2a. Přidej env vars (Settings → Variables):
| Klíč | Hodnota |
|------|---------|
| `SUPABASE_URL` | `https://wqlbbxhieboybyvwdvjr.supabase.co` |
| `SUPABASE_ANON_KEY` | `sb_publishable_nl9YngghvSmjjCoqOjtvzg_Sez5XXH-` |
| `ANTHROPIC_API_KEY` | tvůj Anthropic klíč |
| `SERPER_API_KEY` | tvůj Serper klíč |
| `GITHUB_PERSONAL_ACCESS_TOKEN` | tvůj GitHub token |
| `RESEND_API_KEY` | tvůj Resend klíč |
| `MAIL_FROM` | `ondrej@tvoje-domena.cz` |

### 2b. Ověř že start command je:
```
python scheduler.py
```
(Dockerfile `CMD` nebo railway.json `startCommand`)

### 2c. Zkontroluj URL Railway Python backendu
Railway Python service má vlastní URL (jiná než frontend).
Zkopíruj ji a přidej do Vercel jako `BACKEND_URL`.

---

## 3. Resend — Email (10 minut)

1. Registrace: [resend.com](https://resend.com) (zdarma, 3000 mailů/měsíc)
2. Ověř doménu: Resend → Domains → Add Domain
   - Přidej DNS záznamy SPF/DKIM/DMARC u svého registrátora
   - Free tier funguje i bez vlastní domény (z `onboarding@resend.dev`)
3. API Keys → Create API Key → zkopíruj jako `RESEND_API_KEY`

---

## 4. Ověření pipeline (po deployi)

1. Otevři Vercel URL → uvidíš WebHunter Dashboard
2. Tab "📞 Volání" → zobrazí leady připravené k volání s "🌐 Návrh" tlačítkem
3. Klikni "🌐 Návrh" → otevře se personalizovaný návrh webu pro firmu
4. Po hovoru klikni: ✅ Souhlas / 📞 Nedostupný / ❌ Odmítl
5. Souhlas → systém automaticky odešle mail s návrhem

---

## Rychlý test mailu (volitelné):
```bash
cd /Users/ondrejcabelka/Desktop/DarkFactory
source .venv/bin/activate
python3 -c "
from mail_engine import send_mail
send_mail(
    to_email='ondrej.cabelka@gmail.com',
    lead={'name': 'Test firma', 'obor': 'instalatér', 'mesto': 'Praha'},
    proposal_url='https://ondrejcabelka.github.io/dark-factory-outputs/navrhy/instalater-novak-instalater-praha/',
    tracking_id='test-001'
)
"
```
