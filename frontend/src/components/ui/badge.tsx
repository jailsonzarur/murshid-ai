import type { HTMLAttributes } from 'react'

import { cn } from '../../lib/cn'

export type BadgeTone = 'destructive' | 'green' | 'blue' | 'neutral' | 'orange' | 'outline' | 'secondary'

export type BadgeProps = HTMLAttributes<HTMLSpanElement> & {
  tone?: BadgeTone
  variant?: BadgeTone
}

export function Badge({ className, tone, variant, ...props }: BadgeProps) {
  const resolvedTone = variant ?? tone ?? 'secondary'

  return (
    <span
      className={cn('ui-badge', `ui-badge--${resolvedTone}`, className)}
      {...props}
    />
  )
}
