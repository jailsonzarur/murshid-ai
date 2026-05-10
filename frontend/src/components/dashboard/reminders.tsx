import { Button } from '../ui/button'
import { Card } from '../ui/card'

export function Reminders() {
  return (
    <Card className="tasko-card tasko-reminder-card">
      <h2>Reminders</h2>
      <div className="tasko-reminder-card__box">
        <h3>Revisar fila OCR</h3>
        <p>Time : 02.00 pm - 04.00 pm</p>
        <Button className="tasko-reminder-card__button" icon="video">
          Start Meeting
        </Button>
      </div>
    </Card>
  )
}
