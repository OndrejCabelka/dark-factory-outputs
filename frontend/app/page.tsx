'use client'

import { useEffect, useState, useCallback } from 'react'

const ORANGE = '#FF4D00'
const DARK = '#0a0a0a'
const CARD = '#111111'
const BORDER = '#222222'
const GREEN = '#00ff88'
const RED = '#ff4444'
const GRAY = '#666666'

function timeAgo(iso: string | null): string {
  if (!iso) return 'nikdy'
  const diff = Date.now() - new Date(iso).getTime()
  const m = Math.floor(diff / 60000)
  const h = Math.floor(m / 60)
  const d = Math.floor(h / 24)
  if (d > 0) return `před ${d}d`
  if (h > 0) return `před ${h}h`
  if (m > 0) return `před ${m}m`
  return 'právě teď'
}

function Badge({ color, children }: { color: string; children: string }) {
  return (
    <span style={{
      background: color + '22', color, border: `1px solid ${color}44`,
      borderRadius: 4, padding: '2px 8px', fontSize: 11, fontWeight: 700,
      textTransform: 'uppercase', letterSpacing: 1,
    }}>{children}</span>
  )
}

function FactoryCard({ id, data, onTrigger, triggering }: any) {
  const isRunning = triggering === id
  const resultColor = data.last_result === 'success' ? GREEN : data.last_result === 'never' ? GRAY : RED

  return (
    <div style={{
      background: CARD, border: `1px solid ${isRunning ? ORANGE : BORDER}`,
      borderRadius: 12, padding: 24, transition: 'border-color 0.3s',
      boxShadow: isRunning ? `0 0 20px ${ORANGE}33` : 'none',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 }}>
        <div>
          <div style={{ fontSize: 28, marginBottom: 4 }}>{data.icon}</div>
          <div style={{ fontSize: 18, fontWeight: 700, color: '#fff' }}>Factory {id.toUpperCase()}</div>
          <div style={{ fontSize: 13, color: GRAY, marginTop: 2 }}>{data.name}</div>
        </div>
        <Badge color={data.last_result === 'success' ? GREEN : data.last_result === 'never' ? GRAY : RED}>
          {isRunning ? 'BĚŽÍ...' : data.last_result}
        </Badge>
      </div>

      <div style={{ fontSize: 12, color: GRAY, marginBottom: 6 }}>{data.description}</div>

      <div style={{ display: 'flex', gap: 16, marginTop: 16, fontSize: 12 }}>
        <div>
          <div style={{ color: GRAY }}>Poslední běh</div>
          <div style={{ color: '#ccc', marginTop: 2 }}>{timeAgo(data.last_run)}</div>
        </div>
        <div>
          <div style={{ color: GRAY }}>Schedule</div>
          <div style={{ color: '#ccc', marginTop: 2 }}>{data.schedule}</div>
        </div>
      </div>

      <button
        onClick={() => onTrigger(id)}
        disabled={isRunning}
        style={{
          marginTop: 20, width: '100%', padding: '10px 0',
          background: isRunning ? '#333' : ORANGE,
          color: isRunning ? GRAY : '#000',
          border: 'none', borderRadius: 8, cursor: isRunning ? 'not-allowed' : 'pointer',
          fontWeight: 700, fontSize: 13, fontFamily: 'monospace',
          transition: 'background 0.2s',
        }}
      >
        {isRunning ? '⏳ Spouštím...' : `▶ Spustit Factory ${id.toUpperCase()}`}
      </button>
    </div>
  )
}

function OutputFile({ file }: { file: any }) {
  const icons: Record<string, string> = { pdf: '📄', md: '📝', csv: '📊', txt: '📋' }
  const icon = icons[file.ext] || '📁'

  return (
    <a
      href={file.github_url}
      target="_blank"
      rel="noopener noreferrer"
      style={{
        display: 'flex', alignItems: 'center', gap: 10,
        padding: '10px 14px', background: '#0f0f0f',
        border: `1px solid ${BORDER}`, borderRadius: 8,
        color: '#ccc', textDecoration: 'none', fontSize: 13,
        transition: 'border-color 0.2s',
      }}
      onMouseEnter={e => (e.currentTarget.style.borderColor = ORANGE)}
      onMouseLeave={e => (e.currentTarget.style.borderColor = BORDER)}
    >
      <span style={{ fontSize: 18 }}>{icon}</span>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ color: '#fff', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {file.filename}
        </div>
        <div style={{ fontSize: 11, color: GRAY }}>{file.factory} · {file.size ? `${Math.round(file.size / 1024)}KB` : ''}</div>
      </div>
      <span style={{ color: GRAY, fontSize: 11 }}>↗</span>
    </a>
  )
}

export default function Dashboard() {
  const [status, setStatus] = useState<any>(null)
  const [outputs, setOutputs] = useState<any>(null)
  const [logs, setLogs] = useState<any[]>([])
  const [triggering, setTriggering] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'outputs' | 'logs'>('outputs')
  const [triggerMsg, setTriggerMsg] = useState<string | null>(null)

  const fetchStatus = useCallback(async () => {
    const res = await fetch('/api/status')
    if (res.ok) setStatus(await res.json())
  }, [])

  const fetchOutputs = useCallback(async () => {
    const res = await fetch('/api/outputs')
    if (res.ok) setOutputs(await res.json())
  }, [])

  const fetchLogs = useCallback(async () => {
    const res = await fetch('/api/logs')
    if (res.ok) {
      const data = await res.json()
      setLogs(data.logs || [])
    }
  }, [])

  useEffect(() => {
    fetchStatus()
    fetchOutputs()
    fetchLogs()
    const interval = setInterval(() => { fetchStatus(); fetchLogs() }, 15000)
    return () => clearInterval(interval)
  }, [])

  const trigger = async (factory: string) => {
    setTriggering(factory)
    setTriggerMsg(null)
    try {
      const res = await fetch('/api/trigger', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ factory }),
      })
      const data = await res.json()
      if (data.success) {
        setTriggerMsg(`✅ Factory ${factory.toUpperCase()} spuštěna! Výsledky se objeví na GitHubu.`)
      } else {
        setTriggerMsg(`⚠️ ${data.error || 'Chyba při spouštění'}`)
      }
    } catch {
      setTriggerMsg('❌ Nepodařilo se připojit k API')
    } finally {
      setTimeout(() => setTriggering(null), 3000)
      setTimeout(() => setTriggerMsg(null), 6000)
    }
  }

  const factories = status?.factories || {}
  const grouped = outputs?.grouped || {}
  const factoryLabels: Record<string, string> = {
    digital_products: '💰 Digital Products',
    web_hunter: '🕸️ Web Hunter',
    youtube: '🎬 YouTube',
  }

  return (
    <div style={{ minHeight: '100vh', background: DARK, padding: '0 0 60px' }}>
      {/* Header */}
      <div style={{
        borderBottom: `1px solid ${BORDER}`, padding: '20px 32px',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span style={{ color: ORANGE, fontSize: 22, fontWeight: 900 }}>⚙ DARK FACTORY</span>
          <Badge color={GREEN}>ONLINE</Badge>
        </div>
        <div style={{ fontSize: 12, color: GRAY }}>
          Auto-refresh 15s · {new Date().toLocaleTimeString('cs-CZ')}
        </div>
      </div>

      <div style={{ maxWidth: 1100, margin: '0 auto', padding: '32px 24px' }}>

        {/* Trigger feedback */}
        {triggerMsg && (
          <div style={{
            marginBottom: 24, padding: '12px 18px',
            background: triggerMsg.startsWith('✅') ? '#00ff8811' : '#ff444411',
            border: `1px solid ${triggerMsg.startsWith('✅') ? '#00ff8844' : '#ff444444'}`,
            borderRadius: 8, fontSize: 13,
            color: triggerMsg.startsWith('✅') ? GREEN : RED,
          }}>
            {triggerMsg}
          </div>
        )}

        {/* Factory Cards */}
        <div style={{ marginBottom: 8, fontSize: 11, color: GRAY, textTransform: 'uppercase', letterSpacing: 2 }}>
          Factories
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16, marginBottom: 40 }}>
          {Object.entries(factories).map(([id, data]) => (
            <FactoryCard key={id} id={id} data={data} onTrigger={trigger} triggering={triggering} />
          ))}
          {!status && [0, 1, 2].map(i => (
            <div key={i} style={{
              background: CARD, border: `1px solid ${BORDER}`, borderRadius: 12, height: 220,
              display: 'flex', alignItems: 'center', justifyContent: 'center', color: GRAY, fontSize: 13,
            }}>Načítám...</div>
          ))}
        </div>

        {/* Tabs */}
        <div style={{ display: 'flex', gap: 2, marginBottom: 20, borderBottom: `1px solid ${BORDER}`, paddingBottom: 0 }}>
          {(['outputs', 'logs'] as const).map(tab => (
            <button key={tab} onClick={() => setActiveTab(tab)} style={{
              background: 'none', border: 'none', cursor: 'pointer',
              padding: '8px 20px', fontSize: 13, fontFamily: 'monospace',
              color: activeTab === tab ? ORANGE : GRAY,
              borderBottom: activeTab === tab ? `2px solid ${ORANGE}` : '2px solid transparent',
              marginBottom: -1, fontWeight: activeTab === tab ? 700 : 400,
            }}>
              {tab === 'outputs' ? `📁 Výstupy (${outputs?.total || 0})` : '📋 Logy'}
            </button>
          ))}
        </div>

        {/* Outputs tab */}
        {activeTab === 'outputs' && (
          <div>
            {Object.keys(grouped).length === 0 && (
              <div style={{ color: GRAY, fontSize: 13, padding: 20 }}>
                {outputs ? 'Zatím žádné výstupy.' : 'Načítám výstupy z GitHubu...'}
              </div>
            )}
            {Object.entries(grouped).map(([factory, files]: any) => (
              <div key={factory} style={{ marginBottom: 28 }}>
                <div style={{ fontSize: 12, color: GRAY, textTransform: 'uppercase', letterSpacing: 2, marginBottom: 10 }}>
                  {factoryLabels[factory] || factory}
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {files.map((f: any) => <OutputFile key={f.path} file={f} />)}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Logs tab */}
        {activeTab === 'logs' && (
          <div style={{
            background: '#050505', border: `1px solid ${BORDER}`, borderRadius: 12,
            padding: 20, fontFamily: 'monospace', fontSize: 12, maxHeight: 500, overflowY: 'auto',
          }}>
            {logs.length === 0 ? (
              <div style={{ color: GRAY }}>Načítám logy z Railway...</div>
            ) : (
              logs.slice().reverse().map((log: any, i: number) => {
                const isError = log.severity === 'ERROR' || log.message?.includes('ERROR') || log.message?.includes('❌')
                const isSuccess = log.message?.includes('✅') || log.message?.includes('COMPLETED')
                const isInfo = log.message?.includes('SCHEDULER') || log.message?.includes('▶')
                const color = isError ? RED : isSuccess ? GREEN : isInfo ? ORANGE : '#888'
                return (
                  <div key={i} style={{ display: 'flex', gap: 12, padding: '3px 0', borderBottom: `1px solid #111` }}>
                    <span style={{ color: '#444', flexShrink: 0, fontSize: 11 }}>
                      {log.timestamp ? new Date(log.timestamp).toLocaleTimeString('cs-CZ') : ''}
                    </span>
                    <span style={{ color }}>{log.message}</span>
                  </div>
                )
              })
            )}
          </div>
        )}

        {/* Recent commits */}
        {status?.recent_commits?.length > 0 && (
          <div style={{ marginTop: 40 }}>
            <div style={{ fontSize: 11, color: GRAY, textTransform: 'uppercase', letterSpacing: 2, marginBottom: 12 }}>
              Poslední GitHub commity
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {status.recent_commits.map((c: any, i: number) => (
                <div key={i} style={{
                  display: 'flex', gap: 12, padding: '8px 14px',
                  background: '#0f0f0f', borderRadius: 8, border: `1px solid ${BORDER}`,
                  fontSize: 12, alignItems: 'center',
                }}>
                  <code style={{ color: ORANGE, flexShrink: 0 }}>{c.sha}</code>
                  <span style={{ color: '#ccc', flex: 1 }}>{c.message}</span>
                  <span style={{ color: GRAY, flexShrink: 0 }}>{timeAgo(c.date)}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
