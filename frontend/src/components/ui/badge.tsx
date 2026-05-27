import type { HTMLAttributes } from 'react'

import { cn } from '../../lib/cn'

export type BadgeTone =
  | 'blue'
  | 'destructive'
  | 'green'
  | 'neutral'
  | 'orange'
  | 'outline'
  | 'secondary'

export type BadgeProps = HTMLAttributes<HTMLSpanElement> & {
  tone?: BadgeTone
  variant?: BadgeTone
}

function toneClass(tone: BadgeTone): string {
  switch (tone) {
    case 'green':
      return 'pill pill-ok'
    case 'blue':
      return 'pill pill-accent'
    case 'orange':
      return 'pill pill-warn'
    case 'destructive':
      return 'pill pill-danger'
    case 'secondary':
    case 'neutral':
    case 'outline':
    default:
      return 'tag'
  }
}

export function Badge({ className, tone, variant, ...props }: BadgeProps) {
  const resolvedTone = variant ?? tone ?? 'secondary'

  return (
    <span className={cn(toneClass(resolvedTone), className)} {...props} />
  )
}
