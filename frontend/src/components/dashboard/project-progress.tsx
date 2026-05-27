import { Card } from '../ui/card'

export function ProjectProgress({ progress = 41 }: { progress?: number }) {
  const circumference = 2 * Math.PI * 70
  const strokeDashoffset = circumference - (progress / 100) * circumference

  return (
    <Card className="widget-card">
      <div className="widget-heading">
        <h2>Progresso das provas</h2>
      </div>
      <div className="widget-progress-chart">
        <svg viewBox="0 0 160 160" aria-hidden="true">
          <circle cx="80" cy="80" r="70" />
          <circle
            cx="80"
            cy="80"
            r="70"
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
          />
        </svg>
        <div className="widget-progress-center">
          <strong>{progress}%</strong>
          <span>Concluída</span>
        </div>
      </div>
      <div style={{ display: 'flex', gap: '14px', justifyContent: 'center', flexWrap: 'wrap', fontSize: '12px', color: 'var(--ink-3)', marginTop: '8px' }}>
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
          <i style={{ display: 'inline-block', width: '8px', height: '8px', borderRadius: '50%', background: 'var(--accent)' }} />
          Concluída
        </span>
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
          <i style={{ display: 'inline-block', width: '8px', height: '8px', borderRadius: '50%', background: 'var(--warn)' }} />
          Em andamento
        </span>
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
          <i style={{ display: 'inline-block', width: '8px', height: '8px', borderRadius: '50%', background: 'var(--bg-sunken)' }} />
          Pendente
        </span>
      </div>
    </Card>
  )
}
