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
    <Card className="tasko-card tasko-team-card">
      <div className="tasko-card__heading">
        <h2>Team Collaboration</h2>
        <Button icon="plus" size="sm" variant="outline">
          Add Member
        </Button>
      </div>

      <div className="tasko-team-card__list">
        {items.map((item) => (
          <div className="tasko-team-card__item" key={item.name}>
            <Avatar>
              <AvatarFallback>{item.initials}</AvatarFallback>
            </Avatar>
            <div>
              <p>{item.name}</p>
              <span>
                Working on <strong>{item.task}</strong>
              </span>
            </div>
            <Badge tone={item.tone}>{item.status}</Badge>
          </div>
        ))}
      </div>
    </Card>
  )
}
