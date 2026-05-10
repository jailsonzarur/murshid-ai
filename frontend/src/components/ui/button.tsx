import type { ButtonHTMLAttributes } from 'react'

import { cn } from '../../lib/cn'
import { Icon, type IconName } from './icon'

export type ButtonVariant = 'default' | 'destructive' | 'ghost' | 'link' | 'outline' | 'primary' | 'secondary' | 'dark'
export type ButtonSize = 'default' | 'icon' | 'lg' | 'md' | 'sm'

export type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  icon?: IconName
  size?: ButtonSize
  variant?: ButtonVariant
}

function normalizeVariant(variant: ButtonVariant) {
  if (variant === 'primary') {
    return 'default'
  }

  if (variant === 'dark') {
    return 'foreground'
  }

  return variant
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
        'ui-button',
        `ui-button--${normalizeVariant(variant)}`,
        `ui-button--${size}`,
        className,
      )}
      type={type}
      {...props}
    >
      {icon ? <Icon name={icon} size={16} strokeWidth={2.25} /> : null}
      {children}
    </button>
  )
}
