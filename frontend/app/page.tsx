'use client'

import { useEffect, useState, useCallback, useRef } from 'react'

const ORANGE = '#FF4D00'
const DARK = '#0a0a0a'
const CARD = '#111111'
const BORDER = '#222222'
const GREEN = '#00ff88'
const RED = '#ff4444'
const GRAY = '#555555'
const BLUE = '#4da6ff'
const YELLOW = '#ffcc00'

const VAPI_ASSISTANT_ID = '4537e7d8-39ec-4e72-a6f1-7f37ea5a1afa'
const VAPI_PUBLIC_KEY   = '181d9566-8642-44bb-a632-a011a82264ef'
const FACTORY_SCHEDULES: Record<string, number> = { b: 6, a: 7, c: 8, d: 9, e: 10, f: 11 }

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

function getNextRun(utcHour: number): { label: string; urgent: boolean } {
  const now = new Date()
  const next = new Date()
  next.setUTCHours(utcHour, 0, 0, 0)
  if (next <= now) next.setUTCDate(next.getUTCDate() + 1)
  const diff = next.getTime() - now.getTime()
  const h = Math.floor(diff / 3600000)
  const m = Math.floor((diff % 3600000) / 60000)
  return { label: h === 0 ? `za ${m}m` : `za ${h}h ${m}m`, urgent: h === 0 }
}

function notify(title: string, body: string) {
  if (typeof window !== 'undefined' && 'Notification' in window && Notification.permission === 'granted') {
    new Notification(title, { body, icon: '/favicon.ico' })
  }
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

function Skeleton({ h = 200 }: { h?: number }) {
  return (
    <div style={{ background: `linear-gradient(90deg, ${CARD} 25%, #181818 50%, ${CARD} 75%)`, backgroundSize: '200% 100%', borderRadius: 12, height: h, border: `1px solid ${BORDER}`, animation: 'shimmer 1.5s infinite' }} />
  )
}

// ── STATS BAR ─────────────────────────────────────────────────────────────────
function StatsBar({ status, outputs, health }: any) {
  const factories = status?.factories || {}
  const successCount = Object.values(factories).filter((f: any) => f.last_result === 'success').length
  const isOnline = health?.status === 'ok'
  const uptime = health?.uptime ? `${Math.floor(health.uptime / 3600)}h` : '—'

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 10, marginBottom: 28 }}>
      {[
        { label: 'Backend', value: isOnline ? '🟢 Online' : health ? '🔴 Offline' : '⏳ ...', color: isOnline ? GREEN : health ? RED : GRAY },
        { label: 'Uptime', value: uptime, color: '#ccc' },
        { label: 'Výstupy', value: String(outputs?.total || 0), color: ORANGE },
        { label: 'Factory OK', value: `${successCount}/6`, color: successCount === 6 ? GREEN : successCount >= 3 ? YELLOW : RED },
        { label: 'Scheduler', value: isOnline ? '✅ Běží' : '❓ Neznámo', color: isOnline ? GREEN : GRAY },
      ].map((s, i) => (
        <div key={i} style={{ background: CARD, border: `1px solid ${BORDER}`, borderRadius: 10, padding: '12px 16px' }}>
          <div style={{ fontSize: 10, color: GRAY, textTransform: 'uppercase' as const, letterSpacing: 1, marginBottom: 6 }}>{s.label}</div>
          <div style={{ fontSize: 16, fontWeight: 700, color: s.color }}>{s.value}</div>
        </div>
      ))}
    </div>
  )
}

// ── CALL BUTTON ───────────────────────────────────────────────────────────────
function CallButton() {
  const [callState, setCallState] = useState<'idle'|'connecting'|'active'|'error'>('idle')
  const [transcript, setTranscript] = useState<string[]>([])
  const [volume, setVolume] = useState(0)
  const vapiRef = useRef<any>(null)
  const transcriptRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (transcriptRef.current) transcriptRef.current.scrollTop = transcriptRef.current.scrollHeight
  }, [transcript])

  const startCall = useCallback(async () => {
    setCallState('connecting'); setTranscript([])
    if (typeof window !== 'undefined' && 'Notification' in window && Notification.permission === 'default')
      await Notification.requestPermission()
    try {
      const { default: Vapi } = await import('@vapi-ai/web')
      const vapi = new Vapi(VAPI_PUBLIC_KEY)
      vapiRef.current = vapi
      vapi.on('call-start', () => { setCallState('active'); setTranscript(p => [...p, '🟢 Hovor zahájen']) })
      vapi.on('call-end', () => { setCallState('idle'); setTranscript(p => [...p, '🔴 Hovor ukončen']); vapiRef.current = null })
      vapi.on('message', (msg: any) => {
        if (msg.type === 'transcript' && msg.transcriptType === 'final')
          setTranscript(p => [...p.slice(-30), `${msg.role === 'user' ? '🎤 Ty' : '🤖 AI'}: ${msg.transcript}`])
        if (msg.type === 'function-call')
          setTranscript(p => [...p, `⚙️ Spouštím Factory ${msg.functionCall?.parameters?.factory_key?.toUpperCase()}...`])
      })
      vapi.on('volume-level', (v: number) => setVolume(v))
      vapi.on('error', () => { setCallState('error'); setTimeout(() => setCallState('idle'), 3000) })
      await vapi.start(VAPI_ASSISTANT_ID)
    } catch { setCallState('error'); setTimeout(() => setCallState('idle'), 3000) }
  }, [])

  const endCall = useCallback(() => {
    vapiRef.current?.stop(); vapiRef.current = null; setCallState('idle')
  }, [])

  const isActive = callState === 'active'
  const isConnecting = callState === 'connecting'

  return (
    <div style={{ background: CARD, border: `1px solid ${isActive ? ORANGE : BORDER}`, borderRadius: 14, padding: 20, marginBottom: 20, boxShadow: isActive ? `0 0 40px ${ORANGE}22` : 'none', transition: 'all 0.3s' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
        <button onClick={isActive ? endCall : startCall} disabled={isConnecting} style={{
          width: 60, height: 60, borderRadius: '50%', border: 'none', flexShrink: 0,
          background: isActive ? RED : callState === 'error' ? RED : ORANGE,
          cursor: isConnecting ? 'wait' : 'pointer', fontSize: 24, transition: 'all 0.2s',
          boxShadow: isActive ? `0 0 0 ${6 + volume * 18}px ${ORANGE}33` : 'none',
        }}>
          {isConnecting ? '⏳' : isActive ? '📵' : '📞'}
        </button>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 16, fontWeight: 800, color: '#fff' }}>
            {isConnecting ? 'Připojuji...' : isActive ? 'Hovor aktivní' : callState === 'error' ? 'Chyba připojení' : 'Zavolej Dark Factory AI'}
          </div>
          <div style={{ fontSize: 11, color: GRAY, marginTop: 3 }}>
            {isActive ? 'Claude claude-sonnet-4-6 · CZ — řekni co chceš' : 'Mluv přímo s AI · zkratky: klávesy A–F spustí factory'}
          </div>
          {isActive && (
            <div style={{ marginTop: 8, display: 'flex', gap: 3, alignItems: 'center' }}>
              {Array.from({ length: 12 }).map((_, i) => (
                <div key={i} style={{ width: 3, borderRadius: 2, transition: 'height 0.08s, background 0.08s', height: `${5 + (volume > i/12 ? 20 : 0)}px`, background: volume > i/12 ? ORANGE : BORDER }} />
              ))}
            </div>
          )}
        </div>
      </div>
      {transcript.length > 0 && (
        <div ref={transcriptRef} style={{ marginTop: 14, background: '#060606', borderRadius: 10, padding: 12, maxHeight: 160, overflowY: 'auto', fontSize: 12, border: `1px solid ${BORDER}` }}>
          {transcript.map((line, i) => (
            <div key={i} style={{ padding: '2px 0', color: line.startsWith('🤖') ? '#bbb' : line.startsWith('🎤') ? ORANGE : GREEN }}>{line}</div>
          ))}
        </div>
      )}
    </div>
  )
}

// ── FACTORY CARD ──────────────────────────────────────────────────────────────
function FactoryCard({ id, data, onTrigger, triggering, hotkey }: any) {
  const isRunning = triggering === id
  const resultColor = data.last_result === 'success' ? GREEN : data.last_result === 'never' ? GRAY : RED
  const next = FACTORY_SCHEDULES[id] !== undefined ? getNextRun(FACTORY_SCHEDULES[id]) : null

  return (
    <div style={{
      background: CARD, border: `1px solid ${isRunning ? ORANGE : BORDER}`, borderRadius: 12, padding: 18,
      transition: 'all 0.3s', boxShadow: isRunning ? `0 0 24px ${ORANGE}44` : 'none',
      display: 'flex', flexDirection: 'column' as const, position: 'relative' as const, overflow: 'hidden',
    }}>
      {/* Running pulse bar */}
      {isRunning && <div style={{ position: 'absolute' as const, top: 0, left: 0, right: 0, height: 2, background: `linear-gradient(90deg, transparent, ${ORANGE}, transparent)`, animation: 'slide 1.5s infinite' }} />}

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 10 }}>
        <div>
          <div style={{ fontSize: 22, marginBottom: 2 }}>{data.icon}</div>
          <div style={{ fontSize: 15, fontWeight: 700, color: '#fff' }}>
            Factory {id.toUpperCase()}
            <span style={{ marginLeft: 8, fontSize: 10, color: GRAY, border: `1px solid ${BORDER}`, borderRadius: 4, padding: '1px 6px' }}>{hotkey}</span>
          </div>
          <div style={{ fontSize: 11, color: GRAY, marginTop: 1 }}>{data.name}</div>
        </div>
        <Badge color={isRunning ? ORANGE : resultColor}>{isRunning ? 'BĚŽÍ' : data.last_result}</Badge>
      </div>

      <div style={{ fontSize: 11, color: '#555', marginBottom: 12, lineHeight: 1.6 }}>{data.description}</div>

      <div style={{ display: 'flex', gap: 20, fontSize: 11, marginBottom: 14 }}>
        <div>
          <div style={{ color: GRAY }}>Poslední běh</div>
          <div style={{ color: '#bbb', marginTop: 2 }}>{timeAgo(data.last_run)}</div>
        </div>
        {next && (
          <div>
            <div style={{ color: GRAY }}>Příští run</div>
            <div style={{ color: next.urgent ? YELLOW : BLUE, marginTop: 2, fontWeight: next.urgent ? 700 : 400 }}>{next.label}</div>
          </div>
        )}
      </div>

      <button onClick={() => onTrigger(id)} disabled={isRunning} style={{
        marginTop: 'auto', width: '100%', padding: '10px 0',
        background: isRunning ? '#1a1a1a' : ORANGE, color: isRunning ? GRAY : '#000',
        border: isRunning ? `1px solid ${BORDER}` : 'none', borderRadius: 8,
        cursor: isRunning ? 'not-allowed' : 'pointer', fontWeight: 700, fontSize: 12, fontFamily: 'monospace',
        transition: 'all 0.2s',
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
  const [copied, setCopied] = useState(false)
  const icons: Record<string, string> = { pdf: '📄', md: '📝', csv: '📊', txt: '📋', json: '🔧' }
  const canPreview = ['md', 'txt', 'csv', 'json'].includes(file.ext)

  const togglePreview = async () => {
    if (preview) { setPreview(null); return }
    setLoading(true)
    try {
      const rawUrl = file.github_url.replace('github.com', 'raw.githubusercontent.com').replace('/blob/', '/')
      const text = await fetch(rawUrl).then(r => r.text())
      setPreview(text.slice(0, 3000))
    } catch { setPreview('Nepodařilo se načíst preview.') }
    setLoading(false)
  }

  const copyContent = () => {
    if (preview) { navigator.clipboard.writeText(preview); setCopied(true); setTimeout(() => setCopied(false), 2000) }
  }

  return (
    <div style={{ border: `1px solid ${BORDER}`, borderRadius: 8, overflow: 'hidden', background: '#0d0d0d' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '9px 12px' }}>
        <span style={{ fontSize: 15 }}>{icons[file.ext] || '📁'}</span>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ color: '#ddd', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontSize: 12 }}>{file.filename}</div>
          <div style={{ fontSize: 10, color: GRAY }}>{file.factory} {file.size ? `· ${Math.round(file.size/1024)}KB` : ''}</div>
        </div>
        <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
          {canPreview && (
            <button onClick={togglePreview} style={{ background: preview ? ORANGE+'22' : 'none', border: `1px solid ${preview ? ORANGE+'44' : BORDER}`, borderRadius: 5, padding: '3px 8px', color: preview ? ORANGE : GRAY, cursor: 'pointer', fontSize: 10 }}>
              {loading ? '...' : preview ? 'Skrýt' : 'Preview'}
            </button>
          )}
          {preview && (
            <button onClick={copyContent} style={{ background: 'none', border: `1px solid ${BORDER}`, borderRadius: 5, padding: '3px 8px', color: copied ? GREEN : GRAY, cursor: 'pointer', fontSize: 10 }}>
              {copied ? '✓ Zkopírováno' : '⎘ Kopírovat'}
            </button>
          )}
          <a href={file.github_url} target="_blank" rel="noopener noreferrer" style={{ background: 'none', border: `1px solid ${BORDER}`, borderRadius: 5, padding: '3px 8px', color: GRAY, textDecoration: 'none', fontSize: 10 }}>↗</a>
        </div>
      </div>
      {preview && (
        <div style={{ padding: 12, background: '#070707', fontFamily: 'monospace', fontSize: 11, color: '#999', maxHeight: 280, overflowY: 'auto', whiteSpace: 'pre-wrap', wordBreak: 'break-word' as const, borderTop: `1px solid ${BORDER}` }}>
          {preview}{preview.length >= 3000 && <span style={{ color: ORANGE }}>\n\n... zkráceno na 3000 znaků</span>}
        </div>
      )}
    </div>
  )
}

// ── MAIN DASHBOARD ────────────────────────────────────────────────────────────
export default function Dashboard() {
  const [status, setStatus]   = useState<any>(null)
  const [outputs, setOutputs] = useState<any>(null)
  const [logs, setLogs]       = useState<any[]>([])
  const [health, setHealth]   = useState<any>(null)
  const [triggering, setTriggering] = useState<string | null>(null)
  const [activeTab, setActiveTab]   = useState<'outputs'|'logs'>('outputs')
  const [triggerMsg, setTriggerMsg] = useState<{ text: string; ok: boolean } | null>(null)
  const [filterExt, setFilterExt]   = useState<string>('all')
  const [filterFactory, setFilterFactory] = useState<string>('all')
  const [logSearch, setLogSearch]   = useState('')
  const [, setTick] = useState(0)

  const fetchAll = useCallback(async () => {
    const [s, o, l] = await Promise.allSettled([
      fetch('/api/status').then(r => r.ok ? r.json() : null),
      fetch('/api/outputs').then(r => r.ok ? r.json() : null),
      fetch('/api/logs').then(r => r.ok ? r.json() : null),
    ])
    if (s.status==='fulfilled' && s.value) setStatus(s.value)
    if (o.status==='fulfilled' && o.value) setOutputs(o.value)
    if (l.status==='fulfilled' && l.value) setLogs(l.value.logs || [])
  }, [])

  const fetchHealth = useCallback(async () => {
    try {
      const r = await fetch('https://dark-factory-production.up.railway.app/health')
      setHealth(r.ok ? await r.json() : { status: 'error' })
    } catch { setHealth({ status: 'error' }) }
  }, [])

  const trigger = useCallback(async (factory: string) => {
    setTriggering(factory); setTriggerMsg(null)
    try {
      const r = await fetch('/api/trigger', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ factory }) })
      const d = await r.json()
      const ok = !!d.success
      setTriggerMsg({ text: ok ? `✅ Factory ${factory.toUpperCase()} spuštěna!` : `⚠️ ${d.error || 'Chyba'}`, ok })
      if (ok) notify('Dark Factory', `Factory ${factory.toUpperCase()} byla spuštěna`)
    } catch { setTriggerMsg({ text: '❌ Nepodařilo se připojit', ok: false }) }
    finally { setTimeout(() => setTriggering(null), 3000); setTimeout(() => setTriggerMsg(null), 6000) }
  }, [])

  // Keyboard shortcuts: A / B / C
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return
      const key = e.key.toLowerCase()
      if (['a','b','c','d','e','f'].includes(key) && !triggering) trigger(key)
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [trigger, triggering])

  useEffect(() => {
    fetchAll(); fetchHealth()
    const i1 = setInterval(fetchAll, 15000)
    const i2 = setInterval(fetchHealth, 30000)
    const i3 = setInterval(() => setTick(t => t+1), 60000)
    return () => { clearInterval(i1); clearInterval(i2); clearInterval(i3) }
  }, [])

  const factories = status?.factories || {}
  const grouped   = outputs?.grouped  || {}
  const factoryLabels: Record<string, string> = {
    digital_products: '💰 Digital Products',
    web_hunter:       '🕸️ Web Hunter',
    youtube:          '🎬 YouTube',
    data_products:    '📊 Data Products',
    seo_content:      '📝 SEO Content',
    leads_api:        '📦 Leads API',
  }
  const hotkeys: Record<string, string> = { a:'A', b:'B', c:'C', d:'D', e:'E', f:'F' }

  // Build filtered file list
  const allFiles: any[] = Object.entries(grouped).flatMap(([factory, files]: any) =>
    (files as any[]).map((f: any) => ({ ...f, factoryKey: factory }))
  )
  const filteredFiles = allFiles.filter(f =>
    (filterExt === 'all' || f.ext === filterExt) &&
    (filterFactory === 'all' || f.factoryKey === filterFactory)
  )
  const allExts = Array.from(new Set(allFiles.map(f => f.ext).filter(Boolean)))

  // Filter logs
  const filteredLogs = logSearch
    ? logs.filter(l => l.message?.toLowerCase().includes(logSearch.toLowerCase()))
    : logs

  return (
    <div style={{ minHeight: '100vh', background: DARK, padding: '0 0 80px' }}>
      <style>{`
        @keyframes shimmer { 0%{background-position:200% 0} 100%{background-position:-200% 0} }
        @keyframes slide { 0%{transform:translateX(-100%)} 100%{transform:translateX(100%)} }
        * { box-sizing: border-box; }
        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: #111; }
        ::-webkit-scrollbar-thumb { background: #333; border-radius: 3px; }
      `}</style>

      {/* Header */}
      <div style={{ borderBottom:`1px solid ${BORDER}`, padding:'14px 20px', display:'flex', alignItems:'center', justifyContent:'space-between', position:'sticky' as const, top:0, background:'rgba(10,10,10,0.95)', backdropFilter:'blur(10px)', zIndex:100 }}>
        <div style={{ display:'flex', alignItems:'center', gap:10 }}>
          <span style={{ color:ORANGE, fontSize:18, fontWeight:900, letterSpacing:1 }}>⚙ DARK FACTORY</span>
          <Badge color={health?.status==='ok' ? GREEN : GRAY}>{health?.status==='ok' ? 'ONLINE' : health ? 'OFFLINE' : '...'}</Badge>
        </div>
        <div style={{ display:'flex', gap:16, alignItems:'center', fontSize:11, color:GRAY }}>
          <span>Klávesy: {['A','B','C','D','E','F'].map(k => <code key={k} style={{ color:ORANGE, marginRight:2 }}>{k}</code>)}</span>
          <span>↻ 15s</span>
        </div>
      </div>

      <div style={{ maxWidth:1100, margin:'0 auto', padding:'20px 16px' }}>
        <StatsBar status={status} outputs={outputs} health={health} />
        <CallButton />

        {triggerMsg && (
          <div style={{ marginBottom:16, padding:'10px 16px', background: triggerMsg.ok ? '#00ff8811' : '#ff444411', border:`1px solid ${triggerMsg.ok ? '#00ff8844' : '#ff444444'}`, borderRadius:8, fontSize:13, color: triggerMsg.ok ? GREEN : RED }}>
            {triggerMsg.text}
          </div>
        )}

        {/* Factory grid */}
        <div style={{ fontSize:10, color:GRAY, textTransform:'uppercase' as const, letterSpacing:2, marginBottom:8 }}>Factories</div>
        <div style={{ display:'grid', gridTemplateColumns:'repeat(auto-fit, minmax(260px, 1fr))', gap:12, marginBottom:32 }}>
          {status
            ? Object.entries(factories).map(([id, data]) => (
                <FactoryCard key={id} id={id} data={data} onTrigger={trigger} triggering={triggering} hotkey={hotkeys[id]} />
              ))
            : [0,1,2,3,4,5].map(i => <Skeleton key={i} h={220} />)
          }
        </div>

        {/* Tabs */}
        <div style={{ display:'flex', gap:2, marginBottom:16, borderBottom:`1px solid ${BORDER}` }}>
          {(['outputs','logs'] as const).map(tab => (
            <button key={tab} onClick={() => setActiveTab(tab)} style={{
              background:'none', border:'none', cursor:'pointer', padding:'8px 16px', fontSize:12,
              fontFamily:'monospace', color: activeTab===tab ? ORANGE : GRAY, fontWeight: activeTab===tab ? 700 : 400,
              borderBottom: activeTab===tab ? `2px solid ${ORANGE}` : '2px solid transparent', marginBottom:-1,
            }}>
              {tab==='outputs' ? `📁 Výstupy (${outputs?.total || 0})` : `📋 Logy (${logs.length})`}
            </button>
          ))}
        </div>

        {/* Outputs tab */}
        {activeTab==='outputs' && (
          <div>
            {/* Filters */}
            {allFiles.length > 0 && (
              <div style={{ display:'flex', gap:8, marginBottom:16, flexWrap:'wrap' as const }}>
                <select value={filterFactory} onChange={e => setFilterFactory(e.target.value)} style={{ background:CARD, border:`1px solid ${BORDER}`, color:'#ccc', padding:'5px 10px', borderRadius:6, fontSize:11, cursor:'pointer' }}>
                  <option value="all">Všechny factory</option>
                  {Object.keys(grouped).map(k => <option key={k} value={k}>{factoryLabels[k] || k}</option>)}
                </select>
                <select value={filterExt} onChange={e => setFilterExt(e.target.value)} style={{ background:CARD, border:`1px solid ${BORDER}`, color:'#ccc', padding:'5px 10px', borderRadius:6, fontSize:11, cursor:'pointer' }}>
                  <option value="all">Všechny typy</option>
                  {allExts.map(ext => <option key={ext} value={ext}>.{ext}</option>)}
                </select>
                {(filterExt!=='all' || filterFactory!=='all') && (
                  <button onClick={() => { setFilterExt('all'); setFilterFactory('all') }} style={{ background:'none', border:`1px solid ${BORDER}`, color:GRAY, padding:'5px 10px', borderRadius:6, fontSize:11, cursor:'pointer' }}>✕ Reset</button>
                )}
                <span style={{ fontSize:11, color:GRAY, alignSelf:'center', marginLeft:4 }}>{filteredFiles.length} souborů</span>
              </div>
            )}

            {filteredFiles.length === 0 && (
              <div style={{ color:GRAY, fontSize:13, padding:'40px 0', textAlign:'center' as const }}>
                {outputs ? (allFiles.length > 0 ? '🔍 Žádné výsledky pro tento filtr.' : '📭 Zatím žádné výstupy.') : 'Načítám z GitHubu...'}
              </div>
            )}

            {/* Group by factory */}
            {Object.entries(grouped).map(([factory, files]: any) => {
              const filtered = (files as any[]).filter((f:any) =>
                (filterExt==='all' || f.ext===filterExt) && (filterFactory==='all' || factory===filterFactory)
              )
              if (filtered.length === 0) return null
              return (
                <div key={factory} style={{ marginBottom:20 }}>
                  <div style={{ fontSize:11, color:GRAY, textTransform:'uppercase' as const, letterSpacing:2, marginBottom:8, display:'flex', alignItems:'center', gap:8 }}>
                    {factoryLabels[factory] || factory}
                    <span style={{ color:BORDER }}>({filtered.length})</span>
                  </div>
                  <div style={{ display:'flex', flexDirection:'column' as const, gap:5 }}>
                    {filtered.map((f:any) => <OutputFile key={f.path} file={f} />)}
                  </div>
                </div>
              )
            })}
          </div>
        )}

        {/* Logs tab */}
        {activeTab==='logs' && (
          <div>
            <input
              value={logSearch} onChange={e => setLogSearch(e.target.value)}
              placeholder="Hledat v lozích..."
              style={{ width:'100%', background:CARD, border:`1px solid ${BORDER}`, color:'#ccc', padding:'8px 12px', borderRadius:8, fontSize:12, marginBottom:12, outline:'none' }}
            />
            <div style={{ background:'#050505', border:`1px solid ${BORDER}`, borderRadius:12, padding:14, fontFamily:'monospace', fontSize:11, maxHeight:500, overflowY:'auto' as const }}>
              {filteredLogs.length === 0
                ? <div style={{ color:GRAY }}>{logSearch ? 'Žádné výsledky.' : 'Načítám logy z Railway...'}</div>
                : filteredLogs.slice().reverse().map((log:any, i:number) => {
                    const isErr  = log.severity==='ERROR' || log.message?.includes('❌')
                    const isOk   = log.message?.includes('✅')
                    const isInfo = log.message?.includes('SCHEDULER') || log.message?.includes('▶')
                    const color  = isErr ? RED : isOk ? GREEN : isInfo ? ORANGE : '#666'
                    return (
                      <div key={i} style={{ display:'flex', gap:10, padding:'2px 0', borderBottom:`1px solid #0f0f0f` }}>
                        <span style={{ color:'#2a2a2a', flexShrink:0, minWidth:60 }}>
                          {log.timestamp ? new Date(log.timestamp).toLocaleTimeString('cs-CZ') : ''}
                        </span>
                        <span style={{ color }}>{log.message}</span>
                      </div>
                    )
                  })
              }
            </div>
          </div>
        )}

        {/* Recent commits */}
        {status?.recent_commits?.length > 0 && (
          <div style={{ marginTop:32 }}>
            <div style={{ fontSize:10, color:GRAY, textTransform:'uppercase' as const, letterSpacing:2, marginBottom:8 }}>Poslední commity</div>
            <div style={{ display:'flex', flexDirection:'column' as const, gap:4 }}>
              {status.recent_commits.map((c:any, i:number) => (
                <div key={i} style={{ display:'flex', gap:10, padding:'7px 12px', background:'#0d0d0d', borderRadius:8, border:`1px solid ${BORDER}`, fontSize:11, alignItems:'center' }}>
                  <code style={{ color:ORANGE, flexShrink:0 }}>{c.sha}</code>
                  <span style={{ color:'#bbb', flex:1, overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap' as const }}>{c.message}</span>
                  <span style={{ color:GRAY, flexShrink:0 }}>{timeAgo(c.date)}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
