import { Button } from '../ui/button'
import { Card } from '../ui/card'

export function Reminders() {
  return (
    <Card className="widget-card">
      <div className="widget-heading">
        <h2>Lembretes</h2>
      </div>
      <div className="widget-reminder-box">
        <h3>Revisar fila OCR</h3>
        <p>Horário: 14h às 16h.</p>
        <Button icon="video" size="sm">
          Iniciar reunião
        </Button>
      </div>
    </Card>
  )
}
