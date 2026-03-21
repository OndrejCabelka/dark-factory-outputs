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

    const { data, error, count } = await db
      .from('leads')
      .select('*', { count: 'exact' })
      .in('stav', ['navrh_vygenerovan', 'novy'])
      .order('priority', { ascending: true })
      .order('created_at', { ascending: true })
      .limit(50)

    if (error) throw error

    return NextResponse.json({
      leads: data || [],
      total: count || 0,
      supabase_configured: true,
    })
  } catch (err: any) {
    return NextResponse.json({ error: err.message, leads: [], total: 0 }, { status: 500 })
  }
}
