import { Button } from '../ui/button'
import { Card } from '../ui/card'

export type ProjectListItem = {
  date: string
  icon: string
  name: string
  tone: 'blue' | 'cyan' | 'emerald' | 'amber' | 'purple'
}

export function ProjectList({ items }: { items: ProjectListItem[] }) {
  return (
    <Card className="tasko-card tasko-project-list">
      <div className="tasko-card__heading">
        <h2>Project</h2>
        <Button icon="plus" size="sm" variant="outline">
          New
        </Button>
      </div>

      <div className="tasko-project-list__items">
        {items.map((item) => (
          <div className="tasko-project-list__item" key={item.name}>
            <span className={`tasko-project-list__icon tasko-project-list__icon--${item.tone}`}>
              {item.icon}
            </span>
            <div>
              <p>{item.name}</p>
              <span>Due date: {item.date}</span>
            </div>
          </div>
        ))}
      </div>
    </Card>
  )
}
