import { Icon, type IconName } from '../ui/icon'

export type DashboardStat = {
  delay?: string
  icon: IconName
  label: string
  subtitle?: string
  tone?: 'primary' | 'card'
  value: string
}

const iconColors = ['purple', 'blue', 'orange', 'pink'] as const

export function StatsCards({ stats }: { stats: DashboardStat[] }) {
  return (
    <div className="stat-grid">
      {stats.map((stat, index) => (
        <div
          className="stat-card"
          key={stat.label}
          style={{ animationDelay: stat.delay ?? `${index * 100}ms` }}
        >
          <div className="stat-top">
            <span className={`stat-icon ${iconColors[index % iconColors.length]}`}>
              <Icon name={stat.icon} size={18} />
            </span>
          </div>
          <p className="stat-label">{stat.label}</p>
          <p className="stat-value">{stat.value}</p>
          {stat.subtitle ? <p className="stat-meta">{stat.subtitle}</p> : null}
        </div>
      ))}
    </div>
  )
}
