import { useEffect, useRef, useState } from 'react'

import { fetchSubjectOptions } from '../../lib/subject-options'
import type { Subject } from '../../types/lecture'
import { Icon } from '../ui/icon'

type SubjectPickerProps = {
  current: Subject | null
  isSaving: boolean
  onClose: () => void
  onConfirm: (subject: Subject | null) => void
}

const PAGE_SIZE_HINT = 20

export function SubjectPicker({ current, isSaving, onClose, onConfirm }: SubjectPickerProps) {
  const [search, setSearch] = useState('')
  const [options, setOptions] = useState<Subject[]>([])
  const [pending, setPending] = useState<Subject | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  useEffect(() => {
    function handleOutside(event: MouseEvent) {
      if (!containerRef.current?.contains(event.target as Node)) onClose()
    }
    function handleKey(event: KeyboardEvent) {
      if (event.key === 'Escape') onClose()
    }
    document.addEventListener('mousedown', handleOutside)
    document.addEventListener('keydown', handleKey)
    return () => {
      document.removeEventListener('mousedown', handleOutside)
      document.removeEventListener('keydown', handleKey)
    }
  }, [onClose])

  useEffect(() => {
    let active = true
    const timer = window.setTimeout(() => {
      setIsLoading(true)
      void fetchSubjectOptions(search, 1)
        .then((page) => {
          if (active) setOptions(page.options.slice(0, PAGE_SIZE_HINT))
        })
        .catch(() => undefined)
        .finally(() => {
          if (active) setIsLoading(false)
        })
    }, 220)

    return () => {
      active = false
      window.clearTimeout(timer)
    }
  }, [search])

  return (
    <div className="subject-picker" ref={containerRef}>
      <div className="subject-picker__head">
        {pending ? (
          <>
            <span className="subject-picker__pending">{pending.name}</span>
            <button
              className="btn btn-primary subject-picker__ok"
              disabled={isSaving}
              onClick={() => onConfirm(pending)}
              type="button"
            >
              {isSaving ? '...' : 'OK'}
            </button>
            <button
              className="subject-picker__clear"
              onClick={() => setPending(null)}
              type="button"
            >
              <Icon name="x" size={13} />
            </button>
          </>
        ) : (
          <>
            <Icon className="subject-picker__search-icon" name="search" size={13} />
            <input
              className="subject-picker__input"
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Pesquisar matéria..."
              ref={inputRef}
              value={search}
            />
          </>
        )}
      </div>

      <div className="subject-picker__list">
        {isLoading && options.length === 0 ? (
          <p className="subject-picker__empty">Carregando...</p>
        ) : options.length === 0 ? (
          <p className="subject-picker__empty">Nenhuma matéria encontrada.</p>
        ) : (
          options.map((option) => (
            <button
              className={`subject-picker__option${
                option.id === current?.id ? ' is-current' : ''
              }`}
              key={option.id}
              onClick={() => setPending(option)}
              type="button"
            >
              <span>{option.name}</span>
              {option.id === current?.id ? <Icon name="check" size={13} /> : null}
            </button>
          ))
        )}
      </div>

      {current ? (
        <button
          className="subject-picker__remove"
          disabled={isSaving}
          onClick={() => onConfirm(null)}
          type="button"
        >
          Remover matéria
        </button>
      ) : null}
    </div>
  )
}
