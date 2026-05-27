import { Card } from '../ui/card'

export type AnalyticsPoint = {
  day: string
  label: string
  value: number
}

export function ProjectAnalytics({ data }: { data: AnalyticsPoint[] }) {
  const maxValue = Math.max(...data.map((point) => point.value))
  const average = Math.round(data.reduce((sum, point) => sum + point.value, 0) / data.length)

  return (
    <Card className="widget-card">
      <div className="widget-heading">
        <h2>Análise de provas</h2>
        <div className="widget-legend">
          <span />
          Atividade semanal
        </div>
      </div>

      <div className="widget-bars" aria-label="Atividade semanal">
        {data.map((point) => (
          <div className="widget-bars__item" key={`${point.day}-${point.label}`}>
            <div className="widget-bars__bar">
              <span style={{ height: `${point.value}%` }} />
            </div>
            <strong>{point.day}</strong>
          </div>
        ))}
      </div>

      <div className="widget-bars__summary">
        <p>
          <span>Média: </span>
          <strong>{average}%</strong>
        </p>
        <p>
          <span>Pico: </span>
          <strong>{maxValue}%</strong>
        </p>
      </div>
    </Card>
  )
}
