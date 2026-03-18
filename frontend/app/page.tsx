'use client'

import { useEffect, useState, useCallback, useRef } from 'react'

const ORANGE = '#FF4D00'
const DARK = '#0a0a0a'
const CARD = '#111111'
const BORDER = '#222222'
const GREEN = '#00ff88'
const RED = '#ff4444'
const GRAY = '#666666'

const VAPI_ASSISTANT_ID = '4537e7d8-39ec-4e72-a6f1-7f37ea5a1afa'
const VAPI_PUBLIC_KEY   = '181d9566-8642-44bb-a632-a011a82264ef'

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
      textTransform: 'uppercase' as const, letterSpacing: 1,
    }}>{children}</span>
  )
}

// ── VAPI CALL BUTTON ──────────────────────────────────────────────────────────
function CallButton() {
  const [callState, setCallState] = useState<'idle' | 'connecting' | 'active' | 'error'>('idle')
  const [transcript, setTranscript] = useState<string[]>([])
  const [volume, setVolume] = useState(0)
  const vapiRef = useRef<any>(null)

  const startCall = useCallback(async () => {
    setCallState('connecting')
    setTranscript([])

    try {
      // Dynamically import Vapi SDK
      const { default: Vapi } = await import('@vapi-ai/web')
      const vapi = new Vapi(VAPI_PUBLIC_KEY)
      vapiRef.current = vapi

      vapi.on('call-start', () => {
        setCallState('active')
        setTranscript(prev => [...prev, '🟢 Hovor zahájen'])
      })
      vapi.on('call-end', () => {
        setCallState('idle')
        setTranscript(prev => [...prev, '🔴 Hovor ukončen'])
        vapiRef.current = null
      })
      vapi.on('message', (msg: any) => {
        if (msg.type === 'transcript' && msg.transcriptType === 'final') {
          const role = msg.role === 'user' ? '🎤 Ty' : '🤖 AI'
          setTranscript(prev => [...prev.slice(-20), `${role}: ${msg.transcript}`])
        }
        if (msg.type === 'function-call') {
          setTranscript(prev => [...prev, `⚙️ Spouštím Factory ${msg.functionCall?.parameters?.factory_key?.toUpperCase()}...`])
        }
      })
      vapi.on('volume-level', (v: number) => setVolume(v))
      vapi.on('error', (e: any) => {
        console.error('Vapi error:', e)
        setCallState('error')
        setTimeout(() => setCallState('idle'), 3000)
      })

      await vapi.start(VAPI_ASSISTANT_ID)
    } catch (e: any) {
      console.error(e)
      setCallState('error')
      setTimeout(() => setCallState('idle'), 3000)
    }
  }, [])

  const endCall = useCallback(() => {
    if (vapiRef.current) {
      vapiRef.current.stop()
      vapiRef.current = null
    }
    setCallState('idle')
  }, [])

  const isActive = callState === 'active'
  const isConnecting = callState === 'connecting'
  const pulse = isActive ? `0 0 0 ${8 + volume * 20}px ${ORANGE}44` : 'none'

  return (
    <div style={{
      background: CARD, border: `1px solid ${isActive ? ORANGE : BORDER}`,
      borderRadius: 16, padding: 28, marginBottom: 32,
      boxShadow: isActive ? `0 0 40px ${ORANGE}22` : 'none',
      transition: 'all 0.3s',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 20, marginBottom: isActive ? 20 : 0 }}>
        {/* Call button */}
        <button
          onClick={isActive ? endCall : startCall}
          disabled={isConnecting}
          style={{
            width: 72, height: 72, borderRadius: '50%', border: 'none',
            background: isActive ? RED : callState === 'error' ? RED : ORANGE,
            cursor: isConnecting ? 'wait' : 'pointer',
            fontSize: 28, transition: 'all 0.2s',
            boxShadow: pulse,
            flexShrink: 0,
          }}
        >
          {isConnecting ? '⏳' : isActive ? '📵' : '📞'}
        </button>

        <div>
          <div style={{ fontSize: 20, fontWeight: 800, color: '#fff' }}>
            {isConnecting ? 'Připojuji...' : isActive ? 'Hovor aktivní' : callState === 'error' ? 'Chyba připojení' : 'Zavolej Dark Factory AI'}
          </div>
          <div style={{ fontSize: 13, color: GRAY, marginTop: 4 }}>
            {isActive
              ? 'Mluvíš přímo s AI · Claude claude-sonnet-4-6 · CZ'
              : 'Klikni a mluv — Claude zná celý kontext Dark Factory'}
          </div>
          {isActive && (
            <div style={{ marginTop: 8, display: 'flex', gap: 4, alignItems: 'center' }}>
              {Array.from({ length: 8 }).map((_, i) => (
                <div key={i} style={{
                  width: 3, borderRadius: 2,
                  height: `${8 + (volume > (i / 8) ? 16 : 0)}px`,
                  background: volume > (i / 8) ? ORANGE : BORDER,
                  transition: 'height 0.1s, background 0.1s',
                }} />
              ))}
              <span style={{ marginLeft: 8, fontSize: 11, color: GRAY }}>mikrofon aktivní</span>
            </div>
          )}
        </div>
      </div>

      {/* Transcript */}
      {transcript.length > 0 && (
        <div style={{
          background: '#050505', borderRadius: 10, padding: 14,
          maxHeight: 200, overflowY: 'auto', fontSize: 13,
          border: `1px solid ${BORDER}`,
        }}>
          {transcript.map((line, i) => (
            <div key={i} style={{
              padding: '4px 0',
              color: line.startsWith('🤖') ? '#ccc' : line.startsWith('🎤') ? ORANGE : GREEN,
              borderBottom: i < transcript.length - 1 ? `1px solid #111` : 'none',
            }}>
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
        <Badge color={isRunning ? ORANGE : resultColor}>
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
        }}
      >
        {isRunning ? '⏳ Spouštím...' : `▶ Spustit Factory ${id.toUpperCase()}`}
      </button>
    </div>
  )
}

function OutputFile({ file }: { file: any }) {
  const icons: Record<string, string> = { pdf: '📄', md: '📝', csv: '📊' }
  return (
    <a href={file.github_url} target="_blank" rel="noopener noreferrer" style={{
      display: 'flex', alignItems: 'center', gap: 10, padding: '10px 14px',
      background: '#0f0f0f', border: `1px solid ${BORDER}`, borderRadius: 8,
      color: '#ccc', textDecoration: 'none', fontSize: 13,
    }}>
      <span style={{ fontSize: 18 }}>{icons[file.ext] || '📁'}</span>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ color: '#fff', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{file.filename}</div>
        <div style={{ fontSize: 11, color: GRAY }}>{file.factory} · {file.size ? `${Math.round(file.size / 1024)}KB` : ''}</div>
      </div>
      <span style={{ color: GRAY, fontSize: 11 }}>↗</span>
    </a>
  )
}

// ── MAIN DASHBOARD ────────────────────────────────────────────────────────────
export default function Dashboard() {
  const [status, setStatus]     = useState<any>(null)
  const [outputs, setOutputs]   = useState<any>(null)
  const [logs, setLogs]         = useState<any[]>([])
  const [triggering, setTriggering] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'outputs' | 'logs'>('outputs')
  const [triggerMsg, setTriggerMsg] = useState<string | null>(null)

  const fetchStatus = useCallback(async () => {
    const r = await fetch('/api/status'); if (r.ok) setStatus(await r.json())
  }, [])
  const fetchOutputs = useCallback(async () => {
    const r = await fetch('/api/outputs'); if (r.ok) setOutputs(await r.json())
  }, [])
  const fetchLogs = useCallback(async () => {
    const r = await fetch('/api/logs'); if (r.ok) { const d = await r.json(); setLogs(d.logs || []) }
  }, [])

  useEffect(() => {
    fetchStatus(); fetchOutputs(); fetchLogs()
    const interval = setInterval(() => { fetchStatus(); fetchLogs() }, 15000)
    return () => clearInterval(interval)
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
      <div style={{ borderBottom: `1px solid ${BORDER}`, padding: '20px 32px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span style={{ color: ORANGE, fontSize: 22, fontWeight: 900 }}>⚙ DARK FACTORY</span>
          <Badge color={GREEN}>ONLINE</Badge>
        </div>
        <div style={{ fontSize: 12, color: GRAY }}>Auto-refresh 15s</div>
      </div>

      <div style={{ maxWidth: 1100, margin: '0 auto', padding: '32px 24px' }}>

        {/* CALL BUTTON — hero section */}
        <CallButton />

        {/* Trigger feedback */}
        {triggerMsg && (
          <div style={{
            marginBottom: 24, padding: '12px 18px',
            background: triggerMsg.startsWith('✅') ? '#00ff8811' : '#ff444411',
            border: `1px solid ${triggerMsg.startsWith('✅') ? '#00ff8844' : '#ff444444'}`,
            borderRadius: 8, fontSize: 13,
            color: triggerMsg.startsWith('✅') ? GREEN : RED,
          }}>{triggerMsg}</div>
        )}

        {/* Factory Cards */}
        <div style={{ marginBottom: 8, fontSize: 11, color: GRAY, textTransform: 'uppercase' as const, letterSpacing: 2 }}>Factories</div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16, marginBottom: 40 }}>
          {Object.entries(factories).map(([id, data]) => (
            <FactoryCard key={id} id={id} data={data} onTrigger={trigger} triggering={triggering} />
          ))}
          {!status && [0,1,2].map(i => (
            <div key={i} style={{ background: CARD, border: `1px solid ${BORDER}`, borderRadius: 12, height: 220, display: 'flex', alignItems: 'center', justifyContent: 'center', color: GRAY, fontSize: 13 }}>Načítám...</div>
          ))}
        </div>

        {/* Tabs */}
        <div style={{ display: 'flex', gap: 2, marginBottom: 20, borderBottom: `1px solid ${BORDER}` }}>
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

        {activeTab === 'outputs' && (
          <div>
            {Object.keys(grouped).length === 0 && (
              <div style={{ color: GRAY, fontSize: 13, padding: 20 }}>{outputs ? 'Zatím žádné výstupy.' : 'Načítám z GitHubu...'}</div>
            )}
            {Object.entries(grouped).map(([factory, files]: any) => (
              <div key={factory} style={{ marginBottom: 28 }}>
                <div style={{ fontSize: 12, color: GRAY, textTransform: 'uppercase' as const, letterSpacing: 2, marginBottom: 10 }}>
                  {factoryLabels[factory] || factory}
                </div>
                <div style={{ display: 'flex', flexDirection: 'column' as const, gap: 6 }}>
                  {files.map((f: any) => <OutputFile key={f.path} file={f} />)}
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'logs' && (
          <div style={{ background: '#050505', border: `1px solid ${BORDER}`, borderRadius: 12, padding: 20, fontFamily: 'monospace', fontSize: 12, maxHeight: 500, overflowY: 'auto' as const }}>
            {logs.length === 0
              ? <div style={{ color: GRAY }}>Načítám logy z Railway...</div>
              : logs.slice().reverse().map((log: any, i: number) => {
                  const isError = log.severity === 'ERROR' || log.message?.includes('❌')
                  const isSuccess = log.message?.includes('✅')
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
            }
          </div>
        )}

        {status?.recent_commits?.length > 0 && (
          <div style={{ marginTop: 40 }}>
            <div style={{ fontSize: 11, color: GRAY, textTransform: 'uppercase' as const, letterSpacing: 2, marginBottom: 12 }}>Poslední GitHub commity</div>
            <div style={{ display: 'flex', flexDirection: 'column' as const, gap: 6 }}>
              {status.recent_commits.map((c: any, i: number) => (
                <div key={i} style={{ display: 'flex', gap: 12, padding: '8px 14px', background: '#0f0f0f', borderRadius: 8, border: `1px solid ${BORDER}`, fontSize: 12, alignItems: 'center' }}>
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
