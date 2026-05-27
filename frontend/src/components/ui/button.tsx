import type { ButtonHTMLAttributes } from 'react'

import { cn } from '../../lib/cn'
import { Icon, type IconName } from './icon'

export type ButtonVariant =
  | 'danger'
  | 'dark'
  | 'default'
  | 'destructive'
  | 'ghost'
  | 'link'
  | 'outline'
  | 'primary'
  | 'secondary'

export type ButtonSize = 'default' | 'icon' | 'lg' | 'md' | 'sm'

export type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  icon?: IconName
  size?: ButtonSize
  variant?: ButtonVariant
}

function variantClass(variant: ButtonVariant): string {
  switch (variant) {
    case 'primary':
    case 'default':
      return 'btn-primary'
    case 'ghost':
    case 'outline':
    case 'secondary':
      return 'btn-ghost'
    case 'dark':
      return 'btn-dark'
    case 'danger':
    case 'destructive':
      return 'btn-danger'
    case 'link':
      return 'btn-link'
    default:
      return 'btn-primary'
  }
}

export function Button({
  children,
  className,
  icon,
  size = 'default',
  type = 'button',
  variant = 'default',
  ...props
}: ButtonProps) {
  return (
    <button
      className={cn(
        'btn',
        variantClass(variant),
        size === 'sm' && 'btn-sm',
        size === 'icon' && 'btn-icon',
        className,
      )}
      type={type}
      {...props}
    >
      {icon ? <Icon name={icon} size={14} strokeWidth={2} /> : null}
      {children}
    </button>
  )
}
