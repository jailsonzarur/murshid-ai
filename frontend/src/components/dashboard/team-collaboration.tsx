import { Avatar, AvatarFallback } from '../ui/avatar'
import { Badge, type BadgeTone } from '../ui/badge'
import { Button } from '../ui/button'
import { Card } from '../ui/card'

export type CollaborationItem = {
  initials: string
  name: string
  status: string
  task: string
  tone: BadgeTone
}

export function TeamCollaboration({ items }: { items: CollaborationItem[] }) {
  return (
    <Card className="widget-card">
      <div className="widget-heading">
        <h2>Colaboração da equipe</h2>
        <Button icon="plus" size="sm" variant="outline">
          Adicionar membro
        </Button>
      </div>

      <div className="widget-team-list">
        {items.map((item) => (
          <div className="widget-team-item" key={item.name}>
            <Avatar>
              <AvatarFallback>{item.initials}</AvatarFallback>
            </Avatar>
            <div>
              <p>{item.name}</p>
              <span>
                Trabalhando em <strong>{item.task}</strong>
              </span>
            </div>
            <Badge tone={item.tone}>{item.status}</Badge>
          </div>
        ))}
      </div>
    </Card>
  )
}
