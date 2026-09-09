import { useEffect, useId, useLayoutEffect, useRef, useState, type ReactNode } from 'react'
import { createPortal } from 'react-dom'

import { cn } from '../../lib/cn'
import { Icon } from './icon'

export type SelectOption = {
  id: string
  name: string
}

export type OptionPage = {
  options: SelectOption[]
  hasMore: boolean
}

type SearchableSelectProps = {
  disabled?: boolean
  emptyMessage?: ReactNode
  error?: boolean
  fetchOptions: (search: string, page: number) => Promise<OptionPage>
  label: ReactNode
  onChange: (option: SelectOption | null) => void
  placeholder?: string
  value: SelectOption | null
}

const SEARCH_DEBOUNCE_MS = 250
const MENU_GAP = 4
const MENU_MIN_HEIGHT = 160
const VIEWPORT_MARGIN = 8

export function SearchableSelect({
  disabled,
  emptyMessage = 'Nada encontrado.',
  error,
  fetchOptions,
  label,
  onChange,
  placeholder = 'Selecione...',
  value,
}: SearchableSelectProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [search, setSearch] = useState('')
  const [options, setOptions] = useState<SelectOption[]>([])
  const [page, setPage] = useState(1)
  const [hasMore, setHasMore] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [highlighted, setHighlighted] = useState(0)

  const isFetchingRef = useRef(false)
  const rootRef = useRef<HTMLDivElement>(null)
  const controlRef = useRef<HTMLButtonElement>(null)
  const menuRef = useRef<HTMLDivElement>(null)
  const searchRef = useRef<HTMLInputElement>(null)
  const listRef = useRef<HTMLUListElement>(null)
  const listboxId = useId()

  useEffect(() => {
    if (!isOpen) return

    function onPointerDown(event: PointerEvent) {
      const target = event.target as Node
      if (rootRef.current?.contains(target) || menuRef.current?.contains(target)) return
      setIsOpen(false)
    }

    document.addEventListener('pointerdown', onPointerDown)
    return () => document.removeEventListener('pointerdown', onPointerDown)
  }, [isOpen])

  useEffect(() => {
    if (!isOpen) return
    searchRef.current?.focus()
  }, [isOpen])

  useEffect(() => {
    if (!isOpen) return

    let active = true

    const timer = setTimeout(() => {
      setIsLoading(true)
      isFetchingRef.current = true
      fetchOptions(search, 1)
        .then((result) => {
          if (!active) return
          setOptions(result.options)
          setHasMore(result.hasMore)
          setPage(1)
          setHighlighted(0)
        })
        .catch(() => {
          if (!active) return
          setOptions([])
          setHasMore(false)
        })
        .finally(() => {
          isFetchingRef.current = false
          if (active) setIsLoading(false)
        })
    }, SEARCH_DEBOUNCE_MS)

    return () => {
      active = false
      clearTimeout(timer)
    }
  }, [fetchOptions, isOpen, search])

  function loadMore() {
    if (isFetchingRef.current || !hasMore) return

    isFetchingRef.current = true
    setIsLoading(true)
    fetchOptions(search, page + 1)
      .then((result) => {
        setOptions((previous) => {
          const seen = new Set(previous.map((option) => option.id))
          return [...previous, ...result.options.filter((option) => !seen.has(option.id))]
        })
        setHasMore(result.hasMore)
        setPage((previous) => previous + 1)
      })
      .catch(() => setHasMore(false))
      .finally(() => {
        isFetchingRef.current = false
        setIsLoading(false)
      })
  }

  function select(option: SelectOption) {
    onChange(option)
    setIsOpen(false)
    setSearch('')
  }

  function onKeyDown(event: React.KeyboardEvent) {
    if (event.key === 'Escape') {
      setIsOpen(false)
      return
    }
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault()
      if (!isOpen) {
        setIsLoading(true)
        setIsOpen(true)
        return
      }
      const step = event.key === 'ArrowDown' ? 1 : -1
      setHighlighted((previous) => {
        const next = previous + step
        if (next < 0) return options.length - 1
        if (next >= options.length) return 0
        return next
      })
      return
    }
    if (event.key === 'Enter' && isOpen) {
      event.preventDefault()
      const option = options[highlighted]
      if (option) select(option)
    }
  }

  useLayoutEffect(() => {
    if (!isOpen) return

    const control = controlRef.current
    const menu = menuRef.current
    if (!control || !menu) return

    function place() {
      menu!.style.maxHeight = ''
      const desired = menu!.offsetHeight

      const rect = control!.getBoundingClientRect()
      const below = window.innerHeight - rect.bottom - MENU_GAP - VIEWPORT_MARGIN
      const above = rect.top - MENU_GAP - VIEWPORT_MARGIN
      const openUp = desired > below && above > below
      const available = Math.max(MENU_MIN_HEIGHT, openUp ? above : below)

      menu!.style.maxHeight = `${Math.min(desired, available)}px`
      menu!.style.left = `${rect.left}px`
      menu!.style.width = `${rect.width}px`
      menu!.style.top = openUp ? '' : `${rect.bottom + MENU_GAP}px`
      menu!.style.bottom = openUp ? `${window.innerHeight - rect.top + MENU_GAP}px` : ''
    }

    place()
    window.addEventListener('scroll', place, true)
    window.addEventListener('resize', place)
    return () => {
      window.removeEventListener('scroll', place, true)
      window.removeEventListener('resize', place)
    }
  }, [isLoading, isOpen, options.length])

  useEffect(() => {
    if (!isOpen) return
    listRef.current
      ?.querySelector<HTMLElement>('[data-highlighted="true"]')
      ?.scrollIntoView({ block: 'nearest' })
  }, [highlighted, isOpen])

  return (
    <div className="ui-field" ref={rootRef}>
      <span className="ui-field__label-row">
        <span className="ui-field__label">{label}</span>
      </span>

      <div className="select">
        <button
          aria-controls={isOpen ? listboxId : undefined}
          aria-expanded={isOpen}
          aria-haspopup="listbox"
          className={cn('select__control', error && 'select__control--invalid')}
          disabled={disabled}
          onClick={() => {
            setIsLoading(!isOpen)
            setIsOpen((previous) => !previous)
          }}
          onKeyDown={onKeyDown}
          ref={controlRef}
          type="button"
        >
          <span className={cn('select__value', !value && 'select__value--empty')}>
            {value ? value.name : placeholder}
          </span>
          {value ? (
            <span
              aria-label="Limpar seleção"
              className="select__clear"
              onClick={(event) => {
                event.stopPropagation()
                onChange(null)
              }}
              role="button"
            >
              <Icon name="x" size={13} />
            </span>
          ) : null}
          <Icon className="select__caret" name="chevronDown" size={15} />
        </button>

        {isOpen
          ? createPortal(
              <div className="select__menu" ref={menuRef}>
            <div className="select__search">
              <Icon aria-hidden="true" className="select__search-icon" name="search" size={14} />
              <input
                className="select__search-input"
                onChange={(event) => setSearch(event.target.value)}
                onKeyDown={onKeyDown}
                placeholder="Buscar..."
                ref={searchRef}
                value={search}
              />
            </div>

            <ul
              className="select__list"
              id={listboxId}
              onScroll={(event) => {
                const list = event.currentTarget
                if (list.scrollTop + list.clientHeight >= list.scrollHeight - 24) loadMore()
              }}
              ref={listRef}
              role="listbox"
            >
              {options.map((option, index) => (
                <li key={option.id}>
                  <button
                    aria-selected={option.id === value?.id}
                    className={cn(
                      'select__option',
                      option.id === value?.id && 'select__option--selected',
                    )}
                    data-highlighted={index === highlighted}
                    onClick={() => select(option)}
                    onPointerMove={() => setHighlighted(index)}
                    role="option"
                    type="button"
                  >
                    <span>{option.name}</span>
                    {option.id === value?.id ? <Icon name="check" size={14} /> : null}
                  </button>
                </li>
              ))}

              {isLoading ? <li className="select__status">Buscando...</li> : null}
              {!isLoading && options.length === 0 ? (
                <li className="select__status">{emptyMessage}</li>
              ) : null}
            </ul>
              </div>,
              document.body,
            )
          : null}
      </div>
    </div>
  )
}
