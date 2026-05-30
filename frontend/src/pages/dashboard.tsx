import { useEffect, useState } from 'react'

import { AppShell } from '../components/layout/app-shell'
import { Icon } from '../components/ui/icon'
import { ApiError, getProfile, type UserProfileResponseData } from '../lib/api'
import { getAccessToken, getAuthProfile, saveAuthProfile } from '../lib/auth'
import { navigateTo } from '../lib/navigation'

/* ── Activity chart ─────────────────────────────────────────────── */

const chartData = [
  { d: '01', v: 28 }, { d: '03', v: 34 }, { d: '05', v: 42 },
  { d: '07', v: 38 }, { d: '09', v: 52 }, { d: '11', v: 48 },
  { d: '13', v: 64 }, { d: '15', v: 68 }, { d: '17', v: 72 },
  { d: '19', v: 88 }, { d: '21', v: 76 }, { d: '23', v: 82 },
  { d: '25', v: 92 }, { d: '26', v: 86 },
]

function ActivityChart() {
  const [hover, setHover] = useState(9)

  const W = 640, H = 200, pL = 32, pR = 16, pT = 18, pB = 28
  const iW = W - pL - pR
  const iH = H - pT - pB
  const max = 100
  const xFor = (i: number) => pL + (i / (chartData.length - 1)) * iW
  const yFor = (v: number) => pT + iH - (v / max) * iH

  const pts = chartData.map((d, i): [number, number] => [xFor(i), yFor(d.v)])
  let line = `M${pts[0][0]},${pts[0][1]}`
  for (let i = 1; i < pts.length; i++) {
    const [x0, y0] = pts[i - 1]
    const [x1, y1] = pts[i]
    const cx = x0 + (x1 - x0) / 2
    line += ` C${cx},${y0} ${cx},${y1} ${x1},${y1}`
  }
  const area = line + ` L${xFor(chartData.length - 1)},${pT + iH} L${xFor(0)},${pT + iH} Z`

  return (
    <div className="card">
      <div className="card-head">
        <div>
          <h2 className="card-title">Atividade de estudo</h2>
          <div className="card-sub">Itens estudados — últimos 14 dias</div>
        </div>
        <div style={{ display: 'flex', gap: 6 }}>
          {(['Semana', 'Mês', 'Ano'] as const).map((l, i) => (
            <button
              className={i === 0 ? 'tab active' : 'tab'}
              key={l}
              style={{ padding: '5px 12px', fontSize: 11.5 }}
              type="button"
            >
              {l}
            </button>
          ))}
        </div>
      </div>

      <div className="total-balance">
        <div className="total-label">Total estudado</div>
        <div className="total-amount">
          986{' '}
          <span style={{ fontSize: 16, color: 'var(--ink-3)', fontWeight: 500, letterSpacing: '0.04em' }}>
            itens
          </span>
        </div>
        <div className="progress-bar">
          <i style={{ width: '72%' }} />
          <i className="alt" style={{ width: '84%' }} />
        </div>
        <div className="progress-legend">
          <span>
            <i className="leg-dot" />
            Concluídas <strong style={{ color: 'var(--ink)', marginLeft: 4 }}>712</strong>
          </span>
          <span>
            <i className="leg-dot alt-dot" />
            Pendentes <strong style={{ color: 'var(--ink)', marginLeft: 4 }}>118</strong>
          </span>
          <span style={{ marginLeft: 'auto', color: 'var(--ink-4)' }}>156 ainda em fila</span>
        </div>
        <span className="show-details">Ver detalhes →</span>
      </div>

      <div style={{ padding: '0 18px 14px' }}>
        <svg className="chart" viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none">
          <defs>
            <linearGradient id="chartArea" x1="0" x2="0" y1="0" y2="1">
              <stop offset="0%" stopColor="var(--accent)" stopOpacity="0.22" />
              <stop offset="100%" stopColor="var(--accent)" stopOpacity="0" />
            </linearGradient>
          </defs>
          {[0, 25, 50, 75, 100].map((g) => {
            const y = yFor(g)
            return (
              <g key={g}>
                <line x1={pL} x2={W - pR} y1={y} y2={y} stroke="var(--line)" strokeWidth="1" strokeDasharray={g === 0 ? '' : '3 5'} />
                <text x={pL - 8} y={y + 3.5} textAnchor="end" fontSize="9.5" fill="var(--ink-4)" fontWeight="500">{g}</text>
              </g>
            )
          })}
          <path d={area} fill="url(#chartArea)" />
          <path d={line} fill="none" stroke="var(--accent)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          {chartData.map((d, i) => {
            const x = xFor(i)
            const y = yFor(d.v)
            const isHov = hover === i
            return (
              <g key={i} onMouseEnter={() => setHover(i)}>
                <rect x={x - 14} y={pT} width="28" height={iH} fill="transparent" />
                {isHov && (
                  <>
                    <line x1={x} x2={x} y1={pT} y2={pT + iH} stroke="var(--accent)" strokeWidth="1" strokeDasharray="3 3" opacity="0.6" />
                    <circle cx={x} cy={y} r="5" fill="var(--card)" stroke="var(--accent)" strokeWidth="2" />
                    <g transform={`translate(${Math.min(x + 8, W - pR - 80)},${Math.max(pT + 2, y - 36)})`}>
                      <rect width="72" height="32" rx="6" fill="var(--ink)" />
                      <text x="10" y="13" fontSize="9" fill="oklch(85% 0.01 270)" fontWeight="500">{d.d} Maio</text>
                      <text x="10" y="26" fontSize="12" fill="#fff" fontWeight="700">{d.v} itens</text>
                    </g>
                  </>
                )}
              </g>
            )
          })}
          {chartData.filter((_, i) => i % 2 === 0).map((d, i) => (
            <text key={d.d} x={xFor(i * 2)} y={H - 8} textAnchor="middle" fontSize="10" fill="var(--ink-4)" fontWeight="500">
              {d.d} Mai
            </text>
          ))}
        </svg>
      </div>

      <div className="card-foot">
        <span>Média semanal · <strong>62 itens/dia</strong></span>
        <span>Pico recente · <strong>25 Mai · 92 itens</strong></span>
      </div>
    </div>
  )
}

/* ── Reminders card ──────────────────────────────────────────────── */

function RemindersCard() {
  return (
    <div className="card">
      <div className="card-head">
        <h2 className="card-title">Lembretes</h2>
        <span className="tag">2 hoje</span>
      </div>
      <div className="card-body" style={{ paddingTop: 2 }}>
        <div className="reminder accent">
          <div>
            <div className="reminder-title" style={{ color: 'var(--accent-ink)' }}>Sessão de revisão ativa</div>
            <div className="reminder-time" style={{ color: 'var(--accent-ink)' }}>
              <Icon name="clock" size={11} />
              <span>14:00 — 16:00</span>
            </div>
          </div>
          <button
            className="btn btn-primary btn-sm"
            onClick={() => navigateTo('/exams')}
            style={{ alignSelf: 'flex-start' }}
            type="button"
          >
            <Icon name="video" size={13} />
            <span>Iniciar sessão</span>
          </button>
        </div>
        <div className="reminder">
          <div>
            <div className="reminder-title">BIOMOL 106 — revisão final</div>
            <div className="reminder-time">
              <Icon name="clock" size={11} />
              <span>Hoje · 17:30</span>
            </div>
          </div>
          <div style={{ fontSize: 12, color: 'var(--ink-3)', fontWeight: 500 }}>
            3 questões aguardam revisão manual.
          </div>
        </div>
      </div>
    </div>
  )
}

/* ── Progress ring card ──────────────────────────────────────────── */

function ProgressRingCard({ progress = 41 }: { progress?: number }) {
  const R = 48
  const C = 2 * Math.PI * R
  const offset = C - (progress / 100) * C

  return (
    <div className="card">
      <div className="card-head">
        <h2 className="card-title">Progresso do ciclo</h2>
        <span className="tag accent">2026.1</span>
      </div>
      <div className="card-body">
        <div className="ring-wrap">
          <div className="ring">
            <svg width="116" height="116" viewBox="0 0 116 116" aria-hidden="true">
              <circle cx="58" cy="58" r={R} fill="none" stroke="var(--bg-sunken)" strokeWidth="9" />
              <circle
                cx="58" cy="58" r={R}
                fill="none"
                stroke="var(--accent)"
                strokeWidth="9"
                strokeLinecap="round"
                strokeDasharray={C}
                strokeDashoffset={offset}
                transform="rotate(-90 58 58)"
              />
            </svg>
            <div className="ring-num">
              <strong>{progress}%</strong>
              <small>concluído</small>
            </div>
          </div>
          <dl className="ring-legend">
            <dt>Concluídas</dt>
            <dd>52 de 128 provas</dd>
            <dt>Tempo médio</dt>
            <dd>04:12 por questão</dd>
            <dt>Próximo marco</dt>
            <dd style={{ color: 'var(--accent)' }}>50% nesta sexta</dd>
          </dl>
        </div>
      </div>
    </div>
  )
}

/* ── Team table ──────────────────────────────────────────────────── */

const teamRows = [
  { date: '26 Mai', color: 'purple', initial: 'B', name: 'Biologia Molecular', sub: 'BIOMOL 106 I · Bloco II', score: '78%', time: '04:32', pill: 'Em revisão', pclass: 'pill-warn' },
  { date: '20 Mai', color: 'blue', initial: 'C', name: 'Clínica Médica', sub: 'Residência Clínica Médica 2026', score: '91%', time: '03:08', pill: 'Concluída', pclass: 'pill-ok' },
  { date: '18 Mai', color: 'orange', initial: 'F', name: 'Farmacologia', sub: 'Antibióticos β-lactâmicos', score: '—', time: '—', pill: 'Em fila', pclass: 'pill-mute' },
  { date: '15 Mai', color: 'pink', initial: 'P', name: 'Patologia Geral', sub: 'Inflamação aguda · Bloco I', score: '84%', time: '05:01', pill: 'Concluída', pclass: 'pill-ok' },
]

function TeamTable() {
  return (
    <div className="card">
      <div className="card-head">
        <div>
          <h2 className="card-title">Colaboração e grupos</h2>
          <div className="card-sub">3 disciplinas em curso · ciclo 2026.1</div>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button className="btn btn-ghost btn-sm" type="button">
            <Icon name="filter" size={13} />
            <span>Filtrar</span>
          </button>
          <button className="btn btn-primary btn-sm" type="button">
            <Icon name="plus" size={13} />
            <span>Adicionar</span>
          </button>
        </div>
      </div>

      <div className="table">
        <div className="table-head">
          <div>Data</div>
          <div>Disciplina</div>
          <div className="right">Acerto</div>
          <div className="right">Tempo médio</div>
          <div className="right">Status</div>
        </div>
        {teamRows.map((r) => (
          <div className="table-row" key={r.name}>
            <div className="muted">{r.date}</div>
            <div className="tx-desc">
              <div
                className={`avatar ${r.color}`}
                style={{ width: 32, height: 32, borderRadius: 8, fontSize: 12.5 }}
              >
                {r.initial}
              </div>
              <div style={{ minWidth: 0 }}>
                <div style={{ fontWeight: 700, fontSize: 13.5, letterSpacing: '-0.01em' }}>{r.name}</div>
                <div style={{ fontSize: 12, color: 'var(--ink-3)', fontWeight: 500 }}>{r.sub}</div>
              </div>
            </div>
            <div className="right" style={{ fontSize: 15, fontWeight: 700, letterSpacing: '-0.01em' }}>{r.score}</div>
            <div className="right muted" style={{ fontFamily: 'var(--mono)', fontWeight: 500, fontSize: 13 }}>{r.time}</div>
            <div className="right">
              <span className={`pill ${r.pclass}`}>{r.pill}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

/* ── Stat cards ──────────────────────────────────────────────────── */

const stats = [
  { icon: 'layers' as const, color: 'purple', label: 'Total de provas', value: '128', trend: { dir: 'up', label: '18%' } },
  { icon: 'check' as const, color: 'blue', label: 'Concluídas', value: '99,2%', unit: '', trend: { dir: 'up', label: '1,4 pp' } },
  { icon: 'sparkles' as const, color: 'orange', label: 'Em processamento', value: '06', trend: { dir: 'flat', label: '● agora' } },
  { icon: 'alertTriangle' as const, color: 'pink', label: 'Pendentes', value: '02', trend: { dir: 'down', label: '−2' } },
]

/* ── Main page ───────────────────────────────────────────────────── */

export function DashboardPage() {
  const [profile, setProfile] = useState<UserProfileResponseData | null>(() => getAuthProfile())
  const [isLoadingProfile, setIsLoadingProfile] = useState(() => !getAuthProfile())

  useEffect(() => {
    if (!getAccessToken()) {
      navigateTo('/login', { replace: true })
      return
    }

    if (profile) return

    let mounted = true

    async function load() {
      setIsLoadingProfile(true)
      try {
        const next = await getProfile()
        if (!mounted) return
        saveAuthProfile(next)
        setProfile(next)
      } catch (err) {
        if (err instanceof ApiError && err.kind === 'validation') {
          // profile load error — user stays on page
        }
      } finally {
        if (mounted) setIsLoadingProfile(false)
      }
    }

    void load()
    return () => { mounted = false }
  }, [profile])

  const userName = profile?.name ?? (isLoadingProfile ? '...' : 'Estudante')
  const today = new Date().toLocaleDateString('pt-BR', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })
  const todayLabel = today.charAt(0).toUpperCase() + today.slice(1)

  return (
    <AppShell
      activeItem="dashboard"
      searchPlaceholder="Buscar tarefa, prova ou questão"
      userEmail={profile?.email}
      userName={profile?.name}
    >
      {/* Hero */}
      <div className="hero">
        <div className="hero-grain" />
        <span className="hero-orb h1" />
        <span className="hero-orb h2" />
        <div className="hero-content">
          <div className="hero-left">
            <div className="hero-eyebrow">
              <span className="eyebrow-dot" />
              {todayLabel}
            </div>
            <h1 className="hero-title">
              Olá, {userName} 👋<br />
              Seus estudos estão <em>fluindo</em>.
            </h1>
            <p className="hero-sub">
              Acompanhe todos os módulos — provas, flashcards, transcrições e anotações.
              Você tem 2 itens em análise e uma sessão de revisão marcada para esta tarde.
            </p>
            <div className="hero-actions">
              <button
                className="btn btn-glass"
                onClick={() => navigateTo('/exams')}
                type="button"
              >
                <Icon name="upload" size={14} />
                <span>Importar material</span>
              </button>
              <button
                className="btn btn-light"
                onClick={() => navigateTo('/exams')}
                type="button"
              >
                <Icon name="plus" size={14} />
                <span>Gerar prova</span>
              </button>
            </div>
          </div>
          <div className="hero-tiles">
            <div className="glass-tile">
              <div className="gt-top">
                <div className="gt-icon">
                  <Icon name="clock" size={15} />
                </div>
                <span className="gt-trend">↗ 12%</span>
              </div>
              <div className="gt-label">Esta semana</div>
              <div className="gt-value">14h<small> 32m</small></div>
            </div>
            <div className="glass-tile">
              <div className="gt-top">
                <div className="gt-icon">
                  <Icon name="sparkles" size={15} />
                </div>
                <span className="gt-trend">7 dias</span>
              </div>
              <div className="gt-label">Sequência</div>
              <div className="gt-value">41<small>%</small></div>
            </div>
          </div>
        </div>
      </div>

      {/* Stat grid */}
      <div className="stat-grid">
        {stats.map((s) => (
          <div className="stat-card" key={s.label}>
            <div className="stat-top">
              <div className={`stat-icon ${s.color}`}>
                <Icon name={s.icon} size={18} />
              </div>
              <span className={`stat-trend ${s.trend.dir === 'up' ? 'up' : s.trend.dir === 'down' ? 'down' : 'flat'}`}>
                {s.trend.dir === 'up' && <Icon name="arrowUp" size={11} />}
                {s.trend.dir === 'down' && <Icon name="arrowDown" size={11} />}
                {s.trend.label}
              </span>
            </div>
            <div>
              <div className="stat-label">{s.label}</div>
              <div className="stat-value">{s.value}</div>
              <div className="stat-meta">
                {s.trend.dir === 'up' ? 'Aumento em relação ao mês passado' : s.trend.dir === 'down' ? 'Em análise manual' : 'Transcrições e OCR ativos'}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Chip row */}
      <div className="chip-row">
        <button className="chip-select" type="button">
          <span>Este mês</span>
          <Icon name="chevronDown" size={11} />
        </button>
        <div style={{ width: 1, height: 18, background: 'var(--line)', margin: '0 4px' }} />
        <button className="chip" type="button">
          <strong>84%</strong><span>acerto médio</span><span className="arr">→</span>
        </button>
        <button className="chip" type="button">
          <strong>2.140</strong><span>flashcards revisados</span><span className="arr">→</span>
        </button>
        <button className="chip" type="button">
          <strong>18h</strong><span>transcritas este mês</span><span className="arr">→</span>
        </button>
        <div style={{ flex: 1 }} />
        <button className="chip-select" type="button">
          <span>Comparar com mês anterior</span>
          <Icon name="arrowDown" size={11} />
        </button>
      </div>

      {/* Main grid: chart + right column */}
      <div className="grid">
        <ActivityChart />
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <RemindersCard />
          <ProgressRingCard progress={41} />
        </div>
      </div>

      <div className="divider" />

      {/* Team collaboration */}
      <TeamTable />
    </AppShell>
  )
}
