import { Button } from '../ui/button'
import { Card } from '../ui/card'

export type ProjectListItem = {
  date: string
  icon: string
  name: string
  tone: 'blue' | 'cyan' | 'emerald' | 'amber' | 'purple'
}

const toneToClass: Record<ProjectListItem['tone'], string> = {
  blue: 'blue',
  cyan: 'blue',
  emerald: 'purple',
  amber: 'orange',
  purple: 'purple',
}

export function ProjectList({ items }: { items: ProjectListItem[] }) {
  return (
    <Card className="widget-card">
      <div className="widget-heading">
        <h2>Provas</h2>
        <Button icon="plus" size="sm" variant="outline">
          Nova
        </Button>
      </div>

      <div className="widget-project-list">
        {items.map((item) => (
          <div className="widget-project-item" key={item.name}>
            <span className={`widget-project-icon ${toneToClass[item.tone]}`}>
              {item.icon}
            </span>
            <div>
              <p>{item.name}</p>
              <span>Prazo: {item.date}</span>
            </div>
          </div>
        ))}
      </div>
    </Card>
  )
}
