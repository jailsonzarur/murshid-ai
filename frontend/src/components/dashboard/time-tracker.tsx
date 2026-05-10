import { useEffect, useState } from 'react'

import { Button } from '../ui/button'
import { Card } from '../ui/card'

function formatTime(num: number) {
  return String(num).padStart(2, '0')
}

export function TimeTracker() {
  const [seconds, setSeconds] = useState(24 * 3600 + 8)
  const [isRunning, setIsRunning] = useState(true)

  useEffect(() => {
    if (!isRunning) {
      return
    }

    const intervalId = window.setInterval(() => {
      setSeconds((current) => current + 1)
    }, 1000)

    return () => window.clearInterval(intervalId)
  }, [isRunning])

  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const secs = seconds % 60

  return (
    <Card className="tasko-dark-card tasko-time-card">
      <div className="tasko-time-card__waves" aria-hidden="true" />
      <div className="tasko-dark-card__content">
        <h2>Time Tracker</h2>
        <div className="tasko-time-card__value">
          {formatTime(hours)}:{formatTime(minutes)}:{formatTime(secs)}
        </div>
        <div className="tasko-time-card__actions">
          <Button
            icon="pause"
            onClick={() => setIsRunning((current) => !current)}
            size="icon"
            variant="secondary"
          />
          <Button
            icon="square"
            onClick={() => {
              setSeconds(0)
              setIsRunning(false)
            }}
            size="icon"
            variant="destructive"
          />
        </div>
      </div>
    </Card>
  )
}
