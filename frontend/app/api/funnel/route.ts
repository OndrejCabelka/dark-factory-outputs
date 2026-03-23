export const dynamic = 'force-dynamic'

import { NextResponse } from 'next/server'
import { createClient } from '@supabase/supabase-js'

const SUPABASE_URL = process.env.SUPABASE_URL || ''
const SUPABASE_KEY = process.env.SUPABASE_ANON_KEY || ''

// GET /api/funnel — počty leadů v každém stavu (pipeline zdraví)
export async function GET() {
  if (!SUPABASE_URL || !SUPABASE_KEY) {
    return NextResponse.json({ funnel: [], total: 0, configured: false })
  }

  const db = createClient(SUPABASE_URL, SUPABASE_KEY)

  const { data, error } = await db
    .from('leads')
    .select('stav, priority')

  if (error) return NextResponse.json({ error: error.message }, { status: 500 })

  const counts: Record<string, number> = {}
  for (const row of data || []) {
    counts[row.stav] = (counts[row.stav] || 0) + 1
  }

  // Seřazení podle pipeline pořadí
  const ORDER = [
    'novy', 'navrh_vygenerovan', 'ceka_na_hovor', 'hovor_proveden',
    'souhlas_k_mailu', 'mail_odeslan', 'otevrel_mail', 'navrh_odeslan',
    'zakaznik', 'odmitl', 'nedostupny', 'neodpovida',
  ]

  const LABELS: Record<string, string> = {
    novy:              '🆕 Nový lead',
    navrh_vygenerovan: '🎨 Návrh připraven',
    ceka_na_hovor:     '📋 Čeká na hovor',
    hovor_proveden:    '📞 Hovor proveden',
    souhlas_k_mailu:   '✅ Souhlas',
    mail_odeslan:      '📧 Mail odeslán',
    otevrel_mail:      '👁 Otevřel mail',
    navrh_odeslan:     '🌐 Návrh odeslán',
    zakaznik:          '💰 Zákazník',
    odmitl:            '❌ Odmítl',
    nedostupny:        '📵 Nedostupný',
    neodpovida:        '🔇 Neodpovídá',
  }

  const funnel = ORDER.map(stav => ({
    stav,
    label: LABELS[stav] || stav,
    count: counts[stav] || 0,
    is_win:  stav === 'zakaznik',
    is_loss: ['odmitl', 'neodpovida'].includes(stav),
    is_active: !['odmitl', 'neodpovida', 'zakaznik'].includes(stav),
  })).filter(s => s.count > 0 || s.is_win)

  const total = (data || []).length
  const active = funnel.filter(s => s.is_active).reduce((a, s) => a + s.count, 0)
  const won = counts['zakaznik'] || 0
  const conversion = total > 0 ? ((won / total) * 100).toFixed(1) : '0'

  return NextResponse.json({ funnel, total, active, won, conversion, configured: true })
}
