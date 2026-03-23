import { NextResponse } from 'next/server'
import { createClient } from '@supabase/supabase-js'

const SUPABASE_URL  = process.env.SUPABASE_URL || ''
const SUPABASE_KEY  = process.env.SUPABASE_ANON_KEY || ''
const BACKEND_URL   = process.env.BACKEND_URL || 'https://dark-factory-production.up.railway.app'

// POST /api/log-call
// Body: { id: string, result: 'souhlas_k_mailu'|'nedostupny'|'odmitl', note?: string }
export async function POST(req: Request) {
  if (!SUPABASE_URL || !SUPABASE_KEY) {
    return NextResponse.json({ error: 'Supabase není nakonfigurováno' }, { status: 503 })
  }

  const body = await req.json()
  const { id, result, note } = body

  const VALID_RESULTS = ['souhlas_k_mailu', 'nedostupny', 'odmitl']
  if (!id || !VALID_RESULTS.includes(result)) {
    return NextResponse.json({ error: 'Chybí id nebo neplatný result' }, { status: 400 })
  }

  const db = createClient(SUPABASE_URL, SUPABASE_KEY)

  // 1. Načti lead pro email + metadata
  const { data: lead, error: fetchErr } = await db
    .from('leads')
    .select('*')
    .eq('id', id)
    .single()

  if (fetchErr || !lead) {
    return NextResponse.json({ error: 'Lead nenalezen' }, { status: 404 })
  }

  // 2. Ulož výsledek hovoru
  const update: Record<string, any> = { stav: result }
  if (note) update.call_note = note

  const { error: updateErr } = await db
    .from('leads')
    .update(update)
    .eq('id', id)

  if (updateErr) {
    return NextResponse.json({ error: updateErr.message }, { status: 500 })
  }

  // 3. Pokud souhlas → odešli mail přes backend (Railway)
  let mailResult: { sent?: boolean; url?: string; error?: string } = {}

  if (result === 'souhlas_k_mailu' && lead.email) {
    try {
      const mailRes = await fetch(`${BACKEND_URL}/api/send-mail`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          lead_id:  id,
          email:    lead.email,
          name:     lead.name,
          obor:     lead.obor,
          mesto:    lead.mesto,
        }),
        signal: AbortSignal.timeout(10000),
      })
      if (mailRes.ok) {
        const d = await mailRes.json()
        mailResult = { sent: true, url: d.proposal_url }
      } else {
        mailResult = { sent: false, error: `Backend ${mailRes.status}` }
      }
    } catch (e: any) {
      // Backend nedostupný — mail se odešle až při příštím /send-pending runu
      mailResult = { sent: false, error: e.message }
    }
  }

  // 4. Pokud nedostupný → naplánuj opakování (přidej zpět do fronty za 24h)
  if (result === 'nedostupny') {
    const attempts = (lead.call_attempt || 0) + 1
    const retryStav = attempts >= 3 ? 'neodpovida' : 'novy'  // po 3x vzdáme to
    await db.from('leads').update({
      stav: retryStav,
      call_attempt: attempts,
    }).eq('id', id)
  }

  return NextResponse.json({
    ok: true,
    id,
    result,
    mail: mailResult,
    lead_name: lead.name,
  })
}
