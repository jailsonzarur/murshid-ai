import type { ReactNode, SelectHTMLAttributes } from 'react'

import { cn } from '../../lib/cn'
import { Icon } from './icon'

export type SelectBoxOption = {
  disabled?: boolean
  label: string
  value: string
}

export type SelectBoxProps = Omit<SelectHTMLAttributes<HTMLSelectElement>, 'children'> & {
  error?: ReactNode
  hint?: ReactNode
  label?: ReactNode
  options: SelectBoxOption[]
}

export function SelectBox({
  className,
  error,
  hint,
  label = 'Select',
  options,
  ...props
}: SelectBoxProps) {
  return (
    <label className="ui-field">
      <span className="ui-field__label-row">
        <span className="ui-field__label">{label}</span>
        {hint ? <span className="ui-field__hint">{hint}</span> : null}
      </span>
      <span className="ui-field__control">
        <select
          className={cn('ui-input ui-select', Boolean(error) && 'ui-input--invalid', className)}
          {...props}
        >
          {options.map((option) => (
            <option disabled={option.disabled} key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        <Icon className="ui-select__chevron" name="chevronDown" size={16} />
      </span>
      {error ? (
        <span className="ui-field__error" role="alert">
          {error}
        </span>
      ) : null}
    </label>
  )
}
