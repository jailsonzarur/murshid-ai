import { Card } from '../ui/card'

export function ProjectProgress({ progress = 41 }: { progress?: number }) {
  const circumference = 2 * Math.PI * 70
  const strokeDashoffset = circumference - (progress / 100) * circumference

  return (
    <Card className="tasko-card tasko-progress-card">
      <h2>Project Progress</h2>
      <div className="tasko-progress-card__chart">
        <div className="tasko-progress-card__pattern" />
        <svg viewBox="0 0 160 160" aria-hidden="true">
          <circle cx="80" cy="80" r="70" />
          <circle
            cx="80"
            cy="80"
            r="70"
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
          />
        </svg>
        <div>
          <strong>{progress}%</strong>
          <span>Project Ended</span>
        </div>
      </div>
      <div className="tasko-progress-card__legend">
        <span><i />Completed</span>
        <span><i />In Progress</span>
        <span><i />Pending</span>
      </div>
    </Card>
  )
}
