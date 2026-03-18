import { NextRequest, NextResponse } from 'next/server'

const RAILWAY_TOKEN = process.env.RAILWAY_TOKEN!
const RAILWAY_PROJECT_ID = process.env.RAILWAY_PROJECT_ID!
const RAILWAY_SERVICE_ID = process.env.RAILWAY_SERVICE_ID!
const RAILWAY_API_URL = process.env.RAILWAY_API_URL || ''

const FACTORY_NAMES: Record<string, string> = {
  a: 'Web Hunter',
  b: 'Digital Products',
  c: 'YouTube',
}

export async function POST(req: NextRequest) {
  const { factory } = await req.json()

  if (!FACTORY_NAMES[factory]) {
    return NextResponse.json({ error: 'Unknown factory. Use: a, b, c' }, { status: 400 })
  }

  // Try calling the scheduler's HTTP API directly
  if (RAILWAY_API_URL) {
    try {
      const res = await fetch(`${RAILWAY_API_URL}/trigger/${factory}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        signal: AbortSignal.timeout(10000),
      })
      if (res.ok) {
        const data = await res.json()
        return NextResponse.json({ success: true, ...data })
      }
    } catch (e) {
      // Fall through to Railway API redeploy
    }
  }

  // Fallback: trigger via Railway GraphQL — set RUN_FACTORY env var + redeploy
  const mutation = `
    mutation {
      serviceInstanceRedeploy(
        environmentId: "production"
        serviceId: "${RAILWAY_SERVICE_ID}"
      )
    }
  `
  try {
    const res = await fetch('https://backboard.railway.com/graphql/v2', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${RAILWAY_TOKEN}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ query: mutation }),
    })
    const data = await res.json()
    return NextResponse.json({
      success: true,
      method: 'railway_redeploy',
      factory,
      name: FACTORY_NAMES[factory],
      note: 'Railway redeploy triggered. RUN_ON_STARTUP must be true to auto-run.',
      data,
    })
  } catch (e: any) {
    return NextResponse.json({ error: e.message }, { status: 500 })
  }
}
