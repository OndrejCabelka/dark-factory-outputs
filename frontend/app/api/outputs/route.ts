export const dynamic = 'force-dynamic'

import { NextResponse } from 'next/server'

const GITHUB_REPO = process.env.GITHUB_REPO!
const GITHUB_TOKEN = process.env.GITHUB_TOKEN!

export async function GET() {
  const res = await fetch(
    `https://api.github.com/repos/${GITHUB_REPO}/git/trees/main?recursive=1`,
    {
      headers: {
        Authorization: `Bearer ${GITHUB_TOKEN}`,
        Accept: 'application/vnd.github.v3+json',
      },
      next: { revalidate: 60 },
    }
  )

  if (!res.ok) {
    return NextResponse.json({ error: 'GitHub API error', outputs: [] })
  }

  const data = await res.json()
  const tree: any[] = data.tree || []

  const outputs = tree
    .filter((f: any) => f.path.startsWith('_outputs/') && f.type === 'blob')
    .map((f: any) => {
      const parts = f.path.split('/')
      const factory = parts[1] // digital_products, web_hunter, youtube
      const filename = parts[parts.length - 1]
      const ext = filename.split('.').pop() || ''
      return {
        path: f.path,
        factory,
        filename,
        ext,
        size: f.size,
        url: `https://raw.githubusercontent.com/${GITHUB_REPO}/main/${f.path}`,
        github_url: `https://github.com/${GITHUB_REPO}/blob/main/${f.path}`,
      }
    })
    .sort((a: any, b: any) => b.path.localeCompare(a.path))

  const grouped: Record<string, any[]> = {}
  for (const f of outputs) {
    if (!grouped[f.factory]) grouped[f.factory] = []
    grouped[f.factory].push(f)
  }

  return NextResponse.json({ outputs, grouped, total: outputs.length })
}
