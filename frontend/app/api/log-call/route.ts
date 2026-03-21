import { NextResponse } from 'next/server'
import { createClient } from '@supabase/supabase-js'

const SUPABASE_URL = process.env.SUPABASE_URL || ''
const SUPABASE_KEY = process.env.SUPABASE_ANON_KEY || ''

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

  try {
    const db = createClient(SUPABASE_URL, SUPABASE_KEY)

    const update: Record<string, any> = {
      stav: result,
      call_attempt: db.rpc ? undefined : undefined, // increment handled below
    }
    if (note) update.call_note = note

    const { error } = await db
      .from('leads')
      .update(update)
      .eq('id', id)

    if (error) throw error

    // Pokud souhlas → naplánuj odeslání mailu (zatím jen stav)
    // Mail engine (Fáze 4) odešle mail na základě stavu 'souhlas_k_mailu'

    return NextResponse.json({ ok: true, id, result })
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 })
  }
}
