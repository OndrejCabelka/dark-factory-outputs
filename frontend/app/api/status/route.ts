import { NextResponse } from 'next/server'

const GITHUB_REPO  = process.env.GITHUB_REPO!
const GITHUB_TOKEN = process.env.GITHUB_TOKEN!

async function getGithubCommits() {
  const res = await fetch(
    `https://api.github.com/repos/${GITHUB_REPO}/commits?per_page=20`,
    {
      headers: {
        Authorization: `Bearer ${GITHUB_TOKEN}`,
        Accept: 'application/vnd.github.v3+json',
      },
      next: { revalidate: 30 },
    }
  )
  if (!res.ok) return []
  return res.json()
}

const FACTORY_META: Record<string, { name: string; icon: string; schedule: string; description: string }> = {
  b: { name: 'Digital Products', icon: '💰', schedule: '06:00 UTC', description: 'Generuje trendy digitální produkty + PDF, auto-publish na Gumroad' },
  a: { name: 'Web Hunter',       icon: '🕸️', schedule: '07:00 UTC', description: 'Hledá CZ/SK firmy bez webu, generuje HTML návrhy, cold emaily' },
  c: { name: 'YouTube',          icon: '🎬', schedule: '08:00 UTC', description: 'Generuje viral YT skripty + thumbnaily + metadata' },
  d: { name: 'Data Products',    icon: '📊', schedule: '09:00 UTC', description: 'Scrape ARES — nové CZ/SK firmy z registru + AI analytická zpráva' },
  e: { name: 'SEO Content',      icon: '📝', schedule: '10:00 UTC', description: 'Affiliate SEO články (nářadí/zahrada) — H1/H2, srovnání, FAQ, meta' },
  f: { name: 'Leads API',        icon: '📦', schedule: '11:00 UTC', description: 'Balíček leadů z WebHunter k prodeji agenturám (CSV + README)' },
}

const COMMIT_KEYS: Record<string, string> = {
  'Factory-B': 'b', 'Factory-A': 'a', 'Factory-C': 'c',
  'Factory-D': 'd', 'Factory-E': 'e', 'Factory-F': 'f',
}

export async function GET() {
  const commits = await getGithubCommits()

  const factoryRuns: Record<string, { last_run: string; result: string }> = {}
  for (const commit of commits) {
    const msg: string = commit.commit.message
    const ts: string  = commit.commit.author.date
    for (const [tag, key] of Object.entries(COMMIT_KEYS)) {
      if (msg.includes(tag) && !factoryRuns[key]) {
        factoryRuns[key] = { last_run: ts, result: msg.includes('Auto output') ? 'success' : 'unknown' }
      }
    }
  }

  const factories: Record<string, any> = {}
  for (const [key, meta] of Object.entries(FACTORY_META)) {
    factories[key] = {
      ...meta,
      last_run:    factoryRuns[key]?.last_run    || null,
      last_result: factoryRuns[key]?.result      || 'never',
      running:     false,
    }
  }

  return NextResponse.json({
    factories,
    recent_commits: commits.slice(0, 8).map((c: any) => ({
      message: c.commit.message,
      date:    c.commit.author.date,
      sha:     c.sha.slice(0, 7),
    })),
  })
}
