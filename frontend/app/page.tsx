'use client'

import { useEffect, useState, useCallback, useRef } from 'react'

const ORANGE = '#FF4D00'
const DARK = '#0a0a0a'
const CARD = '#111111'
const BORDER = '#222222'
const GREEN = '#00ff88'
const RED = '#ff4444'
const GRAY = '#666666'
const BLUE = '#4da6ff'

const VAPI_ASSISTANT_ID = '4537e7d8-39ec-4e72-a6f1-7f37ea5a1afa'
const VAPI_PUBLIC_KEY   = '181d9566-8642-44bb-a632-a011a82264ef'

// Factory schedules in UTC hours
const FACTORY_SCHEDULES: Record<string, number> = { b: 6, a: 7, c: 8 }

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

function getNextRun(utcHour: number): string {
  const now = new Date()
  const next = new Date()
  next.setUTCHours(utcHour, 0, 0, 0)
  if (next <= now) next.setUTCDate(next.getUTCDate() + 1)
  const diff = next.getTime() - now.getTime()
  const h = Math.floor(diff / 3600000)
  const m = Math.floor((diff % 3600000) / 60000)
  return `za ${h}h ${m}m`
}

function Badge({ color, children }: { color: string; children: string }) {
  return (
    <span style={{
      background: color + '22', color, border: `1px solid ${color}44`,
      borderRadius: 4, padding: '2px 8px', fontSize: 11, fontWeight: 700,
      textTransform: 'uppercase' as const, letterSpacing: 1,
    }}>{children}</span>
  )
}

// ── STATS BAR ─────────────────────────────────────────────────────────────────
function StatsBar({ status, outputs, health }: any) {
  const factories = status?.factories || {}
  const totalFiles = outputs?.total || 0
  const successCount = Object.values(factories).filter((f: any) => f.last_result === 'success').length
  const isOnline = health?.status === 'ok'

  return (
    <div style={{
      display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 32,
    }}>
      {[
        { label: 'Backend', value: isOnline ? '🟢 Online' : health ? '🔴 Offline' : '⏳ Checking', color: isOnline ? GREEN : health ? RED : GRAY },
        { label: 'Výstupy celkem', value: totalFiles, color: ORANGE },
        { label: 'Úspěšné factory', value: `${successCount}/3`, color: successCount === 3 ? GREEN : ORANGE },
        { label: 'Scheduler', value: isOnline ? '✅ Aktivní' : '❓ Neznámo', color: isOnline ? GREEN : GRAY },
      ].map((s, i) => (
        <div key={i} style={{ background: CARD, border: `1px solid ${BORDER}`, borderRadius: 10, padding: '14px 18px' }}>
          <div style={{ fontSize: 11, color: GRAY, textTransform: 'uppercase' as const, letterSpacing: 1, marginBottom: 6 }}>{s.label}</div>
          <div style={{ fontSize: 18, fontWeight: 700, color: s.color }}>{s.value}</div>
        </div>
      ))}
    </div>
  )
}

// ── CALL BUTTON ───────────────────────────────────────────────────────────────
function CallButton() {
  const [callState, setCallState] = useState<'idle' | 'connecting' | 'active' | 'error'>('idle')
  const [transcript, setTranscript] = useState<string[]>([])
  const [volume, setVolume] = useState(0)
  const vapiRef = useRef<any>(null)

  const startCall = useCallback(async () => {
    setCallState('connecting'); setTranscript([])
    try {
      const { default: Vapi } = await import('@vapi-ai/web')
      const vapi = new Vapi(VAPI_PUBLIC_KEY)
      vapiRef.current = vapi
      vapi.on('call-start', () => { setCallState('active'); setTranscript(p => [...p, '🟢 Hovor zahájen']) })
      vapi.on('call-end', () => { setCallState('idle'); setTranscript(p => [...p, '🔴 Hovor ukončen']); vapiRef.current = null })
      vapi.on('message', (msg: any) => {
        if (msg.type === 'transcript' && msg.transcriptType === 'final') {
          const role = msg.role === 'user' ? '🎤 Ty' : '🤖 AI'
          setTranscript(p => [...p.slice(-20), `${role}: ${msg.transcript}`])
        }
        if (msg.type === 'function-call')
          setTranscript(p => [...p, `⚙️ Spouštím Factory ${msg.functionCall?.parameters?.factory_key?.toUpperCase()}...`])
      })
      vapi.on('volume-level', (v: number) => setVolume(v))
      vapi.on('error', () => { setCallState('error'); setTimeout(() => setCallState('idle'), 3000) })
      await vapi.start(VAPI_ASSISTANT_ID)
    } catch { setCallState('error'); setTimeout(() => setCallState('idle'), 3000) }
  }, [])

  const endCall = useCallback(() => {
    if (vapiRef.current) { vapiRef.current.stop(); vapiRef.current = null }
    setCallState('idle')
  }, [])

  const isActive = callState === 'active'
  const isConnecting = callState === 'connecting'

  return (
    <div style={{
      background: CARD, border: `1px solid ${isActive ? ORANGE : BORDER}`, borderRadius: 16, padding: 24, marginBottom: 24,
      boxShadow: isActive ? `0 0 40px ${ORANGE}22` : 'none', transition: 'all 0.3s',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
        <button onClick={isActive ? endCall : startCall} disabled={isConnecting} style={{
          width: 64, height: 64, borderRadius: '50%', border: 'none', flexShrink: 0,
          background: isActive ? RED : callState === 'error' ? RED : ORANGE,
          cursor: isConnecting ? 'wait' : 'pointer', fontSize: 26, transition: 'all 0.2s',
          boxShadow: isActive ? `0 0 0 ${8 + volume * 20}px ${ORANGE}44` : 'none',
        }}>
          {isConnecting ? '⏳' : isActive ? '📵' : '📞'}
        </button>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 18, fontWeight: 800, color: '#fff' }}>
            {isConnecting ? 'Připojuji...' : isActive ? 'Hovor aktivní' : callState === 'error' ? 'Chyba připojení' : 'Zavolej Dark Factory AI'}
          </div>
          <div style={{ fontSize: 12, color: GRAY, marginTop: 3 }}>
            {isActive ? 'Claude claude-sonnet-4-6 · CZ · řekni co chceš spustit' : 'Mluv přímo s AI — zná celý kontext projektu'}
          </div>
          {isActive && (
            <div style={{ marginTop: 8, display: 'flex', gap: 3, alignItems: 'center' }}>
              {Array.from({ length: 10 }).map((_, i) => (
                <div key={i} style={{
                  width: 3, borderRadius: 2, transition: 'height 0.1s, background 0.1s',
                  height: `${6 + (volume > (i / 10) ? 18 : 0)}px`,
                  background: volume > (i / 10) ? ORANGE : BORDER,
                }} />
              ))}
            </div>
          )}
        </div>
      </div>
      {transcript.length > 0 && (
        <div style={{ marginTop: 16, background: '#050505', borderRadius: 10, padding: 12, maxHeight: 180, overflowY: 'auto', fontSize: 12, border: `1px solid ${BORDER}` }}>
          {transcript.map((line, i) => (
            <div key={i} style={{ padding: '3px 0', color: line.startsWith('🤖') ? '#ccc' : line.startsWith('🎤') ? ORANGE : GREEN }}>
              {line}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ── FACTORY CARD ──────────────────────────────────────────────────────────────
function FactoryCard({ id, data, onTrigger, triggering }: any) {
  const isRunning = triggering === id
  const resultColor = data.last_result === 'success' ? GREEN : data.last_result === 'never' ? GRAY : RED
  const nextRun = FACTORY_SCHEDULES[id] !== undefined ? getNextRun(FACTORY_SCHEDULES[id]) : null

  return (
    <div style={{
      background: CARD, border: `1px solid ${isRunning ? ORANGE : BORDER}`, borderRadius: 12, padding: 20,
      transition: 'border-color 0.3s', boxShadow: isRunning ? `0 0 20px ${ORANGE}33` : 'none',
      display: 'flex', flexDirection: 'column' as const,
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
        <div>
          <div style={{ fontSize: 24, marginBottom: 2 }}>{data.icon}</div>
          <div style={{ fontSize: 16, fontWeight: 700, color: '#fff' }}>Factory {id.toUpperCase()}</div>
          <div style={{ fontSize: 12, color: GRAY, marginTop: 1 }}>{data.name}</div>
        </div>
        <Badge color={isRunning ? ORANGE : resultColor}>{isRunning ? 'BĚŽÍ...' : data.last_result}</Badge>
      </div>
      <div style={{ fontSize: 11, color: GRAY, marginBottom: 12, lineHeight: 1.5 }}>{data.description}</div>
      <div style={{ display: 'flex', gap: 16, fontSize: 11, marginBottom: 16 }}>
        <div>
          <div style={{ color: GRAY }}>Poslední běh</div>
          <div style={{ color: '#ccc', marginTop: 2 }}>{timeAgo(data.last_run)}</div>
        </div>
        <div>
          <div style={{ color: GRAY }}>Příští běh</div>
          <div style={{ color: BLUE, marginTop: 2 }}>{nextRun || data.schedule}</div>
        </div>
      </div>
      <button onClick={() => onTrigger(id)} disabled={isRunning} style={{
        marginTop: 'auto', width: '100%', padding: '10px 0',
        background: isRunning ? '#333' : ORANGE, color: isRunning ? GRAY : '#000',
        border: 'none', borderRadius: 8, cursor: isRunning ? 'not-allowed' : 'pointer',
        fontWeight: 700, fontSize: 12, fontFamily: 'monospace',
      }}>
        {isRunning ? '⏳ Spouštím...' : `▶ Spustit Factory ${id.toUpperCase()}`}
      </button>
    </div>
  )
}

// ── FILE PREVIEW ──────────────────────────────────────────────────────────────
function OutputFile({ file }: { file: any }) {
  const [preview, setPreview] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const icons: Record<string, string> = { pdf: '📄', md: '📝', csv: '📊', txt: '📋' }
  const canPreview = ['md', 'txt', 'csv'].includes(file.ext)

  const togglePreview = async () => {
    if (preview) { setPreview(null); return }
    if (!canPreview) return
    setLoading(true)
    try {
      const rawUrl = file.github_url.replace('github.com', 'raw.githubusercontent.com').replace('/blob/', '/')
      const r = await fetch(rawUrl)
      const text = await r.text()
      setPreview(text.slice(0, 2000))
    } catch { setPreview('Nepodařilo se načíst preview.') }
    setLoading(false)
  }

  return (
    <div style={{ border: `1px solid ${BORDER}`, borderRadius: 8, overflow: 'hidden' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '10px 14px', background: '#0f0f0f' }}>
        <span style={{ fontSize: 16 }}>{icons[file.ext] || '📁'}</span>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ color: '#fff', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontSize: 13 }}>{file.filename}</div>
          <div style={{ fontSize: 11, color: GRAY }}>{file.factory} · {file.size ? `${Math.round(file.size / 1024)}KB` : ''}</div>
        </div>
        <div style={{ display: 'flex', gap: 8, flexShrink: 0 }}>
          {canPreview && (
            <button onClick={togglePreview} style={{ background: 'none', border: `1px solid ${BORDER}`, borderRadius: 6, padding: '4px 10px', color: GRAY, cursor: 'pointer', fontSize: 11 }}>
              {loading ? '...' : preview ? 'Skrýt' : 'Preview'}
            </button>
          )}
          <a href={file.github_url} target="_blank" rel="noopener noreferrer" style={{ background: 'none', border: `1px solid ${BORDER}`, borderRadius: 6, padding: '4px 10px', color: GRAY, textDecoration: 'none', fontSize: 11 }}>↗ GitHub</a>
        </div>
      </div>
      {preview && (
        <div style={{ padding: 14, background: '#080808', fontFamily: 'monospace', fontSize: 11, color: '#aaa', maxHeight: 300, overflowY: 'auto', whiteSpace: 'pre-wrap', wordBreak: 'break-all' as const }}>
          {preview}
        </div>
      )}
    </div>
  )
}

// ── MAIN DASHBOARD ────────────────────────────────────────────────────────────
export default function Dashboard() {
  const [status, setStatus]     = useState<any>(null)
  const [outputs, setOutputs]   = useState<any>(null)
  const [logs, setLogs]         = useState<any[]>([])
  const [health, setHealth]     = useState<any>(null)
  const [triggering, setTriggering] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'outputs' | 'logs'>('outputs')
  const [triggerMsg, setTriggerMsg] = useState<string | null>(null)
  const [, setTick] = useState(0)

  const fetchAll = useCallback(async () => {
    const [s, o, l] = await Promise.allSettled([
      fetch('/api/status').then(r => r.ok ? r.json() : null),
      fetch('/api/outputs').then(r => r.ok ? r.json() : null),
      fetch('/api/logs').then(r => r.ok ? r.json() : null),
    ])
    if (s.status === 'fulfilled' && s.value) setStatus(s.value)
    if (o.status === 'fulfilled' && o.value) setOutputs(o.value)
    if (l.status === 'fulfilled' && l.value) setLogs(l.value.logs || [])
  }, [])

  const fetchHealth = useCallback(async () => {
    try {
      const r = await fetch(`${process.env.NEXT_PUBLIC_RAILWAY_API_URL || ''}/health`.replace('undefined', 'https://dark-factory-production.up.railway.app/health'))
      if (r.ok) setHealth(await r.json()); else setHealth({ status: 'error' })
    } catch { setHealth({ status: 'error' }) }
  }, [])

  useEffect(() => {
    fetchAll(); fetchHealth()
    const i1 = setInterval(fetchAll, 15000)
    const i2 = setInterval(fetchHealth, 30000)
    const i3 = setInterval(() => setTick(t => t + 1), 60000) // refresh countdown
    return () => { clearInterval(i1); clearInterval(i2); clearInterval(i3) }
  }, [])

  const trigger = async (factory: string) => {
    setTriggering(factory); setTriggerMsg(null)
    try {
      const r = await fetch('/api/trigger', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ factory }) })
      const d = await r.json()
      setTriggerMsg(d.success ? `✅ Factory ${factory.toUpperCase()} spuštěna!` : `⚠️ ${d.error || 'Chyba'}`)
    } catch { setTriggerMsg('❌ Nepodařilo se připojit') }
    finally { setTimeout(() => setTriggering(null), 3000); setTimeout(() => setTriggerMsg(null), 6000) }
  }

  const factories = status?.factories || {}
  const grouped   = outputs?.grouped  || {}
  const factoryLabels: Record<string, string> = {
    digital_products: '💰 Digital Products',
    web_hunter: '🕸️ Web Hunter',
    youtube: '🎬 YouTube',
  }

  return (
    <div style={{ minHeight: '100vh', background: DARK, padding: '0 0 60px' }}>
      {/* Header */}
      <div style={{ borderBottom: `1px solid ${BORDER}`, padding: '16px 24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', position: 'sticky' as const, top: 0, background: DARK, zIndex: 100 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ color: ORANGE, fontSize: 20, fontWeight: 900 }}>⚙ DARK FACTORY</span>
          <Badge color={health?.status === 'ok' ? GREEN : GRAY}>{health?.status === 'ok' ? 'ONLINE' : 'CHECKING'}</Badge>
        </div>
        <div style={{ fontSize: 11, color: GRAY }}>Auto-refresh 15s</div>
      </div>

      <div style={{ maxWidth: 1100, margin: '0 auto', padding: '24px 16px' }}>

        {/* Stats bar */}
        <StatsBar status={status} outputs={outputs} health={health} />

        {/* Call button */}
        <CallButton />

        {/* Trigger feedback */}
        {triggerMsg && (
          <div style={{
            marginBottom: 20, padding: '10px 16px',
            background: triggerMsg.startsWith('✅') ? '#00ff8811' : '#ff444411',
            border: `1px solid ${triggerMsg.startsWith('✅') ? '#00ff8844' : '#ff444444'}`,
            borderRadius: 8, fontSize: 13, color: triggerMsg.startsWith('✅') ? GREEN : RED,
          }}>{triggerMsg}</div>
        )}

        {/* Factory Cards — responsive grid */}
        <div style={{ fontSize: 11, color: GRAY, textTransform: 'uppercase' as const, letterSpacing: 2, marginBottom: 10 }}>Factories</div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 14, marginBottom: 36 }}>
          {Object.entries(factories).map(([id, data]) => (
            <FactoryCard key={id} id={id} data={data} onTrigger={trigger} triggering={triggering} />
          ))}
          {!status && [0,1,2].map(i => (
            <div key={i} style={{ background: CARD, border: `1px solid ${BORDER}`, borderRadius: 12, height: 200, display: 'flex', alignItems: 'center', justifyContent: 'center', color: GRAY, fontSize: 12 }}>Načítám...</div>
          ))}
        </div>

        {/* Tabs */}
        <div style={{ display: 'flex', gap: 2, marginBottom: 18, borderBottom: `1px solid ${BORDER}` }}>
          {(['outputs', 'logs'] as const).map(tab => (
            <button key={tab} onClick={() => setActiveTab(tab)} style={{
              background: 'none', border: 'none', cursor: 'pointer', padding: '8px 18px', fontSize: 12,
              fontFamily: 'monospace', color: activeTab === tab ? ORANGE : GRAY, fontWeight: activeTab === tab ? 700 : 400,
              borderBottom: activeTab === tab ? `2px solid ${ORANGE}` : '2px solid transparent', marginBottom: -1,
            }}>
              {tab === 'outputs' ? `📁 Výstupy (${outputs?.total || 0})` : `📋 Logy (${logs.length})`}
            </button>
          ))}
        </div>

        {/* Outputs tab */}
        {activeTab === 'outputs' && (
          <div>
            {Object.keys(grouped).length === 0 && (
              <div style={{ color: GRAY, fontSize: 13, padding: 20 }}>{outputs ? 'Zatím žádné výstupy.' : 'Načítám z GitHubu...'}</div>
            )}
            {Object.entries(grouped).map(([factory, files]: any) => (
              <div key={factory} style={{ marginBottom: 24 }}>
                <div style={{ fontSize: 11, color: GRAY, textTransform: 'uppercase' as const, letterSpacing: 2, marginBottom: 8 }}>
                  {factoryLabels[factory] || factory}
                </div>
                <div style={{ display: 'flex', flexDirection: 'column' as const, gap: 6 }}>
                  {files.map((f: any) => <OutputFile key={f.path} file={f} />)}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Logs tab */}
        {activeTab === 'logs' && (
          <div style={{ background: '#050505', border: `1px solid ${BORDER}`, borderRadius: 12, padding: 16, fontFamily: 'monospace', fontSize: 11, maxHeight: 500, overflowY: 'auto' as const }}>
            {logs.length === 0
              ? <div style={{ color: GRAY }}>Načítám logy z Railway...</div>
              : logs.slice().reverse().map((log: any, i: number) => {
                  const isErr = log.severity === 'ERROR' || log.message?.includes('❌')
                  const isOk  = log.message?.includes('✅')
                  const isInfo = log.message?.includes('SCHEDULER') || log.message?.includes('▶')
                  const color = isErr ? RED : isOk ? GREEN : isInfo ? ORANGE : '#777'
                  return (
                    <div key={i} style={{ display: 'flex', gap: 10, padding: '2px 0', borderBottom: `1px solid #111` }}>
                      <span style={{ color: '#333', flexShrink: 0 }}>
                        {log.timestamp ? new Date(log.timestamp).toLocaleTimeString('cs-CZ') : ''}
                      </span>
                      <span style={{ color }}>{log.message}</span>
                    </div>
                  )
                })
            }
          </div>
        )}

        {/* Recent commits */}
        {status?.recent_commits?.length > 0 && (
          <div style={{ marginTop: 36 }}>
            <div style={{ fontSize: 11, color: GRAY, textTransform: 'uppercase' as const, letterSpacing: 2, marginBottom: 10 }}>Poslední commity</div>
            <div style={{ display: 'flex', flexDirection: 'column' as const, gap: 5 }}>
              {status.recent_commits.map((c: any, i: number) => (
                <div key={i} style={{ display: 'flex', gap: 10, padding: '8px 12px', background: '#0f0f0f', borderRadius: 8, border: `1px solid ${BORDER}`, fontSize: 11, alignItems: 'center' }}>
                  <code style={{ color: ORANGE, flexShrink: 0 }}>{c.sha}</code>
                  <span style={{ color: '#bbb', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' as const }}>{c.message}</span>
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
