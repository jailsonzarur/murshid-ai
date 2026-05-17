import { Button } from '../ui/button'
import { Card } from '../ui/card'

export function Reminders() {
  return (
    <Card className="tasko-card tasko-reminder-card">
      <h2>Lembretes</h2>
      <div className="tasko-reminder-card__box">
        <h3>Revisar fila OCR</h3>
        <p>Horário: 14h às 16h.</p>
        <Button className="tasko-reminder-card__button" icon="video">
          Iniciar reunião
        </Button>
      </div>
    </Card>
  )
}
