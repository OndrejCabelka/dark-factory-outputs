import { NextResponse } from 'next/server'
import { createClient } from '@supabase/supabase-js'

const SUPABASE_URL = process.env.SUPABASE_URL || ''
const SUPABASE_KEY = process.env.SUPABASE_ANON_KEY || ''

// GET /api/call-stats?days=7
export async function GET(req: Request) {
  if (!SUPABASE_URL || !SUPABASE_KEY) {
    return NextResponse.json({ stats: [], today: null })
  }

  const { searchParams } = new URL(req.url)
  const days = Math.min(parseInt(searchParams.get('days') || '7'), 30)

  const db = createClient(SUPABASE_URL, SUPABASE_KEY)
  const since = new Date(Date.now() - days * 86400000).toISOString().slice(0, 10)

  const { data, error } = await db
    .from('call_stats')
    .select('*')
    .gte('date', since)
    .order('date', { ascending: false })

  if (error) return NextResponse.json({ error: error.message }, { status: 500 })

  const today = (data || []).find((r: any) => r.date === new Date().toISOString().slice(0, 10)) || null

  return NextResponse.json({ stats: data || [], today })
}
