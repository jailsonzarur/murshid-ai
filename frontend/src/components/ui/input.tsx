import type { InputHTMLAttributes, ReactNode } from 'react'

import { cn } from '../../lib/cn'
import { Icon, type IconName } from './icon'

export type FieldProps = {
  children: ReactNode
  className?: string
  error?: ReactNode
  hint?: ReactNode
  icon?: IconName
  label: ReactNode
}

export function Field({ children, className, error, hint, icon, label }: FieldProps) {
  return (
    <label className={cn('ui-field', className)}>
      <span className="ui-field__label-row">
        <span className="ui-field__label">{label}</span>
        {hint ? <span className="ui-field__hint">{hint}</span> : null}
      </span>
      <span className="ui-field__control">
        {icon ? (
          <span aria-hidden="true" className="ui-field__icon">
            <Icon name={icon} size={16} strokeWidth={2.35} />
          </span>
        ) : null}
        {children}
      </span>
      {error ? (
        <span className="ui-field__error" role="alert">
          {error}
        </span>
      ) : null}
    </label>
  )
}

export type InputProps = InputHTMLAttributes<HTMLInputElement> & {
  error?: ReactNode
  hint?: ReactNode
  icon?: IconName
  label?: ReactNode
}

export function Input({
  className,
  error,
  hint,
  icon,
  label,
  placeholder,
  ...props
}: InputProps) {
  return (
    <Field error={error} hint={hint} icon={icon} label={label ?? placeholder ?? 'Input'}>
      <input
        className={cn(
          'ui-input',
          icon && 'ui-input--with-icon',
          Boolean(error) && 'ui-input--invalid',
          className,
        )}
        placeholder={placeholder}
        {...props}
      />
    </Field>
  )
}
