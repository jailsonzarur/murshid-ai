import { useEffect, useRef, useState, type HTMLAttributes } from 'react'

import { cn } from '../../lib/cn'
import { Icon } from './icon'

export type TopbarProps = HTMLAttributes<HTMLElement> & {
  onLogout?: () => void | Promise<void>
  onMenuClick?: () => void
  searchPlaceholder?: string
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
  className,
  onMenuClick,
  onLogout,
  searchPlaceholder = 'Buscar provas, usuários e análises...',
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
    <header className={cn('topbar', className)} {...props}>
      <button
        aria-label="Abrir menu"
        className="icon-btn"
        onClick={onMenuClick}
        type="button"
      >
        <Icon name="menu" size={18} />
      </button>

      <label className="search">
        <span className="sr-only">Buscar</span>
        <Icon name="search" size={15} />
        <input aria-label="Buscar" placeholder={searchPlaceholder} type="search" />
        <kbd className="kbd">Ctrl F</kbd>
      </label>

      <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '6px' }}>
        <button aria-label="Mensagens" className="icon-btn" type="button">
          <Icon name="mail" size={17} />
        </button>
        <button aria-label="Alertas" className="icon-btn" type="button">
          <Icon name="bell" size={17} />
          <span className="dot" />
        </button>

        <div ref={userMenuRef} style={{ position: 'relative' }}>
          <button
            aria-expanded={isUserMenuOpen}
            aria-haspopup="menu"
            className="topbar-user"
            onClick={() => setIsUserMenuOpen((current) => !current)}
            type="button"
          >
            <span className="avatar">{getInitials(userName)}</span>
            <div className="meta">
              <strong>{userName}</strong>
              <span>{userEmail}</span>
            </div>
          </button>

          {isUserMenuOpen ? (
            <div className="topbar-popover" role="menu">
              <button onClick={handleLogoutClick} role="menuitem" type="button">
                <Icon name="logOut" size={16} />
                Sair
              </button>
            </div>
          ) : null}
        </div>
      </div>
    </header>
  )
}
