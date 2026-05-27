import type { HTMLAttributes, ImgHTMLAttributes } from 'react'

import { cn } from '../../lib/cn'

export function Avatar({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('avatar', className)} {...props} />
}

export function AvatarImage({ className, ...props }: ImgHTMLAttributes<HTMLImageElement>) {
  return <img className={cn('avatar-img', className)} {...props} />
}

export function AvatarFallback({ className, ...props }: HTMLAttributes<HTMLSpanElement>) {
  return <span className={cn(className)} {...props} />
}
