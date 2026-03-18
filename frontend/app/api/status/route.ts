import { NextResponse } from 'next/server'

const GITHUB_REPO = process.env.GITHUB_REPO!
const GITHUB_TOKEN = process.env.GITHUB_TOKEN!
const RAILWAY_TOKEN = process.env.RAILWAY_TOKEN!
const RAILWAY_SERVICE_ID = process.env.RAILWAY_SERVICE_ID!
const RAILWAY_PROJECT_ID = process.env.RAILWAY_PROJECT_ID!

async function getGithubCommits() {
  const res = await fetch(
    `https://api.github.com/repos/${GITHUB_REPO}/commits?per_page=10`,
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

async function getRailwayLogs() {
  const query = `
    query {
      deploymentLogs(deploymentId: "", serviceId: "${RAILWAY_SERVICE_ID}") {
        timestamp
        message
        severity
      }
    }
  `
  try {
    const res = await fetch('https://backboard.railway.com/graphql/v2', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${RAILWAY_TOKEN}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ query }),
      next: { revalidate: 10 },
    })
    const data = await res.json()
    return data?.data?.deploymentLogs || []
  } catch {
    return []
  }
}

export async function GET() {
  const [commits] = await Promise.all([getGithubCommits()])

  // Parse factory runs from commit messages
  const factoryRuns: Record<string, { last_run: string; result: string }> = {}
  for (const commit of commits) {
    const msg: string = commit.commit.message
    const ts: string = commit.commit.author.date
    if (msg.includes('Factory-B') && !factoryRuns['b']) {
      factoryRuns['b'] = { last_run: ts, result: msg.includes('Auto output') ? 'success' : 'unknown' }
    }
    if (msg.includes('Factory-A') && !factoryRuns['a']) {
      factoryRuns['a'] = { last_run: ts, result: 'success' }
    }
    if (msg.includes('Factory-C') && !factoryRuns['c']) {
      factoryRuns['c'] = { last_run: ts, result: 'success' }
    }
  }

  return NextResponse.json({
    factories: {
      b: {
        name: 'Digital Products',
        icon: '💰',
        last_run: factoryRuns['b']?.last_run || null,
        last_result: factoryRuns['b']?.result || 'never',
        schedule: '08:00 CZ',
        description: 'Generuje trendy digitální produkty + PDF',
      },
      a: {
        name: 'Web Hunter',
        icon: '🕸️',
        last_run: factoryRuns['a']?.last_run || null,
        last_result: factoryRuns['a']?.result || 'never',
        schedule: '09:00 CZ',
        description: 'Hledá CZ/SK firmy bez webu, píše cold emaily',
      },
      c: {
        name: 'YouTube',
        icon: '🎬',
        last_run: factoryRuns['c']?.last_run || null,
        last_result: factoryRuns['c']?.result || 'never',
        schedule: '10:00 CZ',
        description: 'Generuje viral YT skripty + metadata',
      },
    },
    recent_commits: commits.slice(0, 5).map((c: any) => ({
      message: c.commit.message,
      date: c.commit.author.date,
      sha: c.sha.slice(0, 7),
    })),
  })
}
