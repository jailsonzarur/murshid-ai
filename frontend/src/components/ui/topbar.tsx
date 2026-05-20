import { useEffect, useRef, useState, type HTMLAttributes, type ReactNode } from 'react'

import { cn } from '../../lib/cn'
import { Icon } from './icon'

export type TopbarProps = HTMLAttributes<HTMLDivElement> & {
  actions?: ReactNode
  description?: string
  onLogout?: () => void | Promise<void>
  onMenuClick?: () => void
  searchPlaceholder?: string
  title?: string
  userEmail?: string
  userName?: string
}

function getInitials(name: string) {
  const initials = name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0])
    .join('')
    .toUpperCase()

  return initials || 'IA'
}

export function Topbar({
  actions,
  className,
  description,
  onMenuClick,
  onLogout,
  searchPlaceholder = 'Buscar provas, usuários e análises...',
  title,
  userEmail = 'Sessão ativa',
  userName = 'Usuário',
  ...props
}: TopbarProps) {
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false)
  const userMenuRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handlePointerDown(event: PointerEvent) {
      if (!userMenuRef.current?.contains(event.target as Node)) {
        setIsUserMenuOpen(false)
      }
    }

    window.addEventListener('pointerdown', handlePointerDown)

    return () => {
      window.removeEventListener('pointerdown', handlePointerDown)
    }
  }, [])

  async function handleLogoutClick() {
    setIsUserMenuOpen(false)
    await onLogout?.()
  }

  return (
    <header className={cn('tasko-header', className)} {...props}>
      <div className="tasko-header__toolbar">
        <button
          aria-label="Abrir menu"
          className="tasko-header__icon-button tasko-header__menu-button"
          onClick={onMenuClick}
          type="button"
        >
          <Icon name="menu" size={18} />
        </button>

        <label className="tasko-search">
          <span className="sr-only">Buscar</span>
          <Icon name="search" size={16} />
          <input aria-label="Buscar" placeholder={searchPlaceholder} type="search" />
          <kbd>Ctrl F</kbd>
        </label>

        <div className="tasko-header__tools">
          <button aria-label="Mensagens" className="tasko-header__icon-button" type="button">
            <Icon name="mail" size={17} />
          </button>
          <button aria-label="Alertas" className="tasko-header__icon-button" type="button">
            <Icon name="bell" size={17} />
            <span className="tasko-header__notification" />
          </button>

          <div className="tasko-user-menu" ref={userMenuRef}>
            <button
              aria-expanded={isUserMenuOpen}
              aria-haspopup="menu"
              className="tasko-user-menu__trigger"
              onClick={() => setIsUserMenuOpen((current) => !current)}
              type="button"
            >
              <span className="tasko-avatar">{getInitials(userName)}</span>
              <span className="tasko-user-menu__copy">
                <strong>{userName}</strong>
                <span>{userEmail}</span>
              </span>
            </button>

            {isUserMenuOpen ? (
              <div className="tasko-user-menu__popover" role="menu">
                <button onClick={handleLogoutClick} role="menuitem" type="button">
                  <Icon name="logOut" size={16} />
                  Sair
                </button>
              </div>
            ) : null}
          </div>
        </div>
      </div>

      {title || description || actions ? (
        <div className="tasko-header__heading">
          <div>
            {title ? <h1>{title}</h1> : null}
            {description ? <p>{description}</p> : null}
          </div>
          {actions ? <div className="tasko-header__actions">{actions}</div> : null}
        </div>
      ) : null}
    </header>
  )
}
