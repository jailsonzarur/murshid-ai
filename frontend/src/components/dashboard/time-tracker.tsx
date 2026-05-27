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
    <Card className="widget-dark">
      <div className="widget-dark__wave" aria-hidden="true" />
      <div style={{ padding: '22px', position: 'relative', zIndex: 1 }}>
        <h2>Controle de tempo</h2>
        <div className="widget-dark__value">
          {formatTime(hours)}:{formatTime(minutes)}:{formatTime(secs)}
        </div>
        <div className="widget-dark__actions">
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
