import { NextResponse } from 'next/server'

const RAILWAY_TOKEN = process.env.RAILWAY_TOKEN!
const RAILWAY_SERVICE_ID = process.env.RAILWAY_SERVICE_ID!
const RAILWAY_PROJECT_ID = process.env.RAILWAY_PROJECT_ID!

export async function GET() {
  // Get latest deployment ID first
  const deployQuery = `
    query {
      deployments(
        input: { projectId: "${RAILWAY_PROJECT_ID}", serviceId: "${RAILWAY_SERVICE_ID}" }
        first: 1
      ) {
        edges {
          node {
            id
            status
            createdAt
          }
        }
      }
    }
  `

  try {
    const depRes = await fetch('https://backboard.railway.com/graphql/v2', {
      method: 'POST',
      headers: { Authorization: `Bearer ${RAILWAY_TOKEN}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: deployQuery }),
      next: { revalidate: 0 },
    })
    const depData = await depRes.json()
    const deploymentId = depData?.data?.deployments?.edges?.[0]?.node?.id
    const deploymentStatus = depData?.data?.deployments?.edges?.[0]?.node?.status

    if (!deploymentId) {
      return NextResponse.json({ logs: [], status: 'no_deployment' })
    }

    // Get logs for this deployment
    const logQuery = `
      query {
        deploymentLogs(deploymentId: "${deploymentId}", limit: 200) {
          timestamp
          message
          severity
        }
      }
    `
    const logRes = await fetch('https://backboard.railway.com/graphql/v2', {
      method: 'POST',
      headers: { Authorization: `Bearer ${RAILWAY_TOKEN}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: logQuery }),
      next: { revalidate: 0 },
    })
    const logData = await logRes.json()
    const logs = logData?.data?.deploymentLogs || []

    return NextResponse.json({
      logs,
      deployment_id: deploymentId,
      deployment_status: deploymentStatus,
    })
  } catch (e: any) {
    return NextResponse.json({ error: e.message, logs: [] })
  }
}
