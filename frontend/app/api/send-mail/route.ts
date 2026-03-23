import { NextResponse } from 'next/server'
import { createClient }  from '@supabase/supabase-js'

const SUPABASE_URL  = process.env.SUPABASE_URL  || ''
const SUPABASE_KEY  = process.env.SUPABASE_ANON_KEY || ''
const RESEND_KEY    = process.env.RESEND_API_KEY || ''
const MAIL_FROM     = process.env.MAIL_FROM || 'ondrej@webhunter.cz'
const MAIL_FROM_NAME = 'Ondřej Čábelka'
const PROPOSALS_BASE = 'https://ondrejcabelka.github.io/dark-factory-outputs/navrhy'

// POST /api/send-mail
// Body: { lead_id, email, name, obor, mesto }
// Nebo: { send_pending: true } → odešle všem čekajícím leadům
export async function POST(req: Request) {
  const body = await req.json()

  if (!RESEND_KEY) {
    return NextResponse.json({
      error: 'RESEND_API_KEY není nakonfigurováno',
      hint: 'Nastav RESEND_API_KEY ve Vercel env vars',
    }, { status: 503 })
  }

  const { Resend } = await import('resend')
  const resend = new Resend(RESEND_KEY)

  // Mode: send_pending — odešle všem leadům se stavem souhlas_k_mailu
  if (body.send_pending) {
    return sendPending(resend)
  }

  // Mode: single lead
  const { lead_id, email, name, obor, mesto } = body
  if (!lead_id || !email) {
    return NextResponse.json({ error: 'Chybí lead_id nebo email' }, { status: 400 })
  }

  const result = await sendToLead(resend, { id: lead_id, email, name, obor, mesto })
  return NextResponse.json(result)
}

// ── HELPERS ───────────────────────────────────────────────────────────────────

function getProposalUrl(name: string, obor: string, mesto: string): string {
  const slug = [name, obor, mesto]
    .join('-')
    .toLowerCase()
    .normalize('NFD').replace(/[\u0300-\u036f]/g, '')  // remove diacritics
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '')
    .slice(0, 50)
  return `${PROPOSALS_BASE}/${slug}/`
}

function buildHtml(lead: any, proposalUrl: string): string {
  const name = lead.name || lead.nazev || 'Vaše firma'
  const obor = lead.obor || 'řemeslník'
  const benefits = [
    'Profesionální design přizpůsobený oboru',
    'Mobilní verze (funguje na telefonu)',
    'Kontaktní formulář + klikatelný telefon',
    'Sekce služeb a reference zákazníků',
    'Připraveno ke spuštění do 48 hodin',
  ]
  return `<!DOCTYPE html><html lang="cs"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f4f4f4;font-family:system-ui,sans-serif">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f4f4;padding:30px 0">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 2px 20px rgba(0,0,0,.08)">
<tr><td style="background:linear-gradient(135deg,#FF4D00,#ff7c47);padding:32px 40px;text-align:center">
  <div style="font-size:26px;font-weight:900;color:#fff">⚙ WebHunter</div>
  <div style="color:rgba(255,255,255,.85);font-size:13px;margin-top:6px">Návrh webu připravený speciálně pro vás</div>
</td></tr>
<tr><td style="padding:36px 40px">
  <p style="font-size:16px;color:#111;margin:0 0 16px">Dobrý den,</p>
  <p style="font-size:15px;color:#333;line-height:1.7;margin:0 0 20px">
    jak jsem slíbil při hovoru — posílám vám <strong>bezplatný návrh webu</strong> pro <strong>${name}</strong> (${obor}).
  </p>
  <table cellpadding="0" cellspacing="0" style="margin:0 auto 32px">
    <tr><td style="background:#FF4D00;border-radius:8px">
      <a href="${proposalUrl}" target="_blank" style="display:block;padding:16px 36px;color:#fff;font-size:16px;font-weight:700;text-decoration:none">
        👀 Zobrazit návrh webu →
      </a>
    </td></tr>
  </table>
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f9f9f9;border-radius:10px;padding:20px;margin-bottom:28px">
  <tr><td>
    <p style="font-size:12px;font-weight:700;color:#555;margin:0 0 10px;text-transform:uppercase;letter-spacing:1px">Co web obsahuje</p>
    ${benefits.map(b => `<p style="margin:5px 0;font-size:13px;color:#333">✅ ${b}</p>`).join('')}
  </td></tr>
  </table>
  <p style="font-size:14px;color:#333;line-height:1.7;margin:0 0 24px">
    Pokud máte zájem, odpovězte na tento email nebo mi zavolejte.
  </p>
  <p style="font-size:14px;color:#333;margin:0 0 32px">
    S pozdravem,<br><strong>Ondřej Čábelka</strong><br>
    <span style="color:#888;font-size:12px">Webdesigner · ondrej.cabelka@gmail.com</span>
  </p>
  <div style="border-top:1px solid #eee;padding-top:16px;text-align:center">
    <a href="${proposalUrl}" style="color:#FF4D00;font-size:13px;font-weight:600;text-decoration:none">🔗 ${proposalUrl}</a>
  </div>
</td></tr>
<tr><td style="background:#f9f9f9;padding:16px 40px;text-align:center;border-top:1px solid #eee">
  <p style="font-size:10px;color:#aaa;margin:0">
    Odesláno na základě vašeho souhlasu při hovoru.
    <a href="mailto:ondrej.cabelka@gmail.com?subject=Odhlasit" style="color:#aaa">Odhlásit se</a>
  </p>
</td></tr>
</table>
</td></tr>
</table>
</body></html>`
}

async function sendToLead(resend: any, lead: any): Promise<any> {
  const name = lead.name || lead.nazev || 'Vaše firma'
  const obor = lead.obor || 'řemeslník'
  const mesto = lead.mesto || ''
  const proposalUrl = getProposalUrl(name, obor, mesto)

  try {
    const r = await resend.emails.send({
      from:    `${MAIL_FROM_NAME} <${MAIL_FROM}>`,
      to:      [lead.email],
      subject: `Návrh webu pro ${name} — živý náhled`,
      html:    buildHtml(lead, proposalUrl),
      text:    `Dobrý den,\n\njak jsem slíbil — posílám návrh webu pro ${name}.\n\nNáhled: ${proposalUrl}\n\nS pozdravem,\nOndřej Čábelka`,
    })

    // Ulož do Supabase že mail byl odeslán
    if (SUPABASE_URL && SUPABASE_KEY && lead.id) {
      const db = createClient(SUPABASE_URL, SUPABASE_KEY)
      await db.from('leads').update({
        stav: 'mail_odeslan',
        mail_odeslan_at: new Date().toISOString(),
      }).eq('id', lead.id)
    }

    return { sent: true, id: r?.data?.id, proposal_url: proposalUrl }
  } catch (e: any) {
    return { sent: false, error: e.message }
  }
}

async function sendPending(resend: any): Promise<Response> {
  if (!SUPABASE_URL || !SUPABASE_KEY) {
    return NextResponse.json({ error: 'Supabase není nakonfigurováno' }, { status: 503 })
  }

  const db = createClient(SUPABASE_URL, SUPABASE_KEY)
  const { data: leads } = await db
    .from('leads')
    .select('*')
    .eq('stav', 'souhlas_k_mailu')
    .not('email', 'is', null)
    .is('mail_odeslan_at', null)

  if (!leads?.length) {
    return NextResponse.json({ sent: 0, message: 'Žádné čekající leady' })
  }

  const results = await Promise.allSettled(
    leads.map(lead => sendToLead(resend, lead))
  )

  const sent  = results.filter(r => r.status === 'fulfilled' && (r.value as any).sent).length
  const fails = results.length - sent

  return NextResponse.json({ sent, fails, total: leads.length })
}
