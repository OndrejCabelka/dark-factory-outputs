import { NextResponse } from 'next/server'
import { createClient } from '@supabase/supabase-js'

const SUPABASE_URL = process.env.SUPABASE_URL || ''
const SUPABASE_KEY = process.env.SUPABASE_ANON_KEY || ''

export async function GET() {
  // Fallback demo data pokud není Supabase nakonfigurované
  if (!SUPABASE_URL || !SUPABASE_KEY) {
    return NextResponse.json({
      leads: [],
      total: 0,
      supabase_configured: false,
      message: 'Nastav SUPABASE_URL a SUPABASE_ANON_KEY v Vercel env vars',
    })
  }

  try {
    const db = createClient(SUPABASE_URL, SUPABASE_KEY)

    // Leady k volání: nové + po 24h retry pro nedostupné (max 3 pokusy)
    const cutoff24h = new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString()

    const { data, error, count } = await db
      .from('leads')
      .select('*, web_navrhy(url, slug)', { count: 'exact' })
      .or(
        `stav.in.(navrh_vygenerovan,novy),` +
        `and(stav.eq.nedostupny,call_attempt.lt.3,updated_at.lt.${cutoff24h})`
      )
      .order('priority', { ascending: true })
      .order('stav', { ascending: false })   // navrh_vygenerovan před novy
      .order('created_at', { ascending: true })
      .limit(50)

    if (error) throw error

    // Přidej proposal_url z web_navrhy join nebo z GitHub Pages slug
    const BASE_PROPOSALS = 'https://ondrejcabelka.github.io/dark-factory-outputs/navrhy'
    const leads = (data || []).map((lead: any) => {
      const navrh = Array.isArray(lead.web_navrhy) ? lead.web_navrhy[0] : lead.web_navrhy
      const proposal_url = navrh?.url || (navrh?.slug ? `${BASE_PROPOSALS}/${navrh.slug}/` : null)
      return { ...lead, proposal_url, web_navrhy: undefined }
    })

    return NextResponse.json({
      leads,
      total: count || 0,
      supabase_configured: true,
    })
  } catch (err: any) {
    return NextResponse.json({ error: err.message, leads: [], total: 0 }, { status: 500 })
  }
}
