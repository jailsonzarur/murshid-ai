import type { ReactNode } from 'react'
import { FileSearch } from 'lucide-react'

import { cn } from '../../lib/cn'

type EmptyStateProps = {
  action?: ReactNode
  className?: string
  description?: ReactNode
  icon?: ReactNode
  title: ReactNode
}

export function EmptyState({
  action,
  className,
  description,
  icon = <FileSearch size={42} strokeWidth={1.8} />,
  title,
}: EmptyStateProps) {
  return (
    <div className={cn('empty-state', className)}>
      <div className="empty-state__art" aria-hidden="true">
        <div className="empty-state__icon">{icon}</div>
      </div>
      <div className="empty-state__copy">
        <h3>{title}</h3>
        {description ? <p>{description}</p> : null}
      </div>
      {action ? <div className="empty-state__action">{action}</div> : null}
    </div>
  )
}
