import { Card } from '../ui/card'
import { Icon, type IconName } from '../ui/icon'

export type DashboardStat = {
  delay?: string
  icon: IconName
  label: string
  subtitle?: string
  tone?: 'primary' | 'card'
  value: string
}

export function StatsCards({ stats }: { stats: DashboardStat[] }) {
  return (
    <div className="tasko-stats-grid">
      {stats.map((stat, index) => (
        <Card
          className={`tasko-stat-card ${stat.tone === 'primary' ? 'tasko-stat-card--primary' : ''}`}
          key={stat.label}
          style={{ animationDelay: stat.delay ?? `${index * 100}ms` }}
        >
          <div className="tasko-stat-card__top">
            <h3>{stat.label}</h3>
            <span>
              <Icon name={stat.icon} size={14} />
            </span>
          </div>
          <p>{stat.value}</p>
          {stat.subtitle ? <small>{stat.subtitle}</small> : null}
        </Card>
      ))}
    </div>
  )
}
