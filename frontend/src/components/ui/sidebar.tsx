import { useEffect, useRef, useState, type HTMLAttributes } from 'react'

import { cn } from '../../lib/cn'
import { Icon, type IconName } from './icon'

export type AppSidebarActiveItem =
  | 'analytics'
  | 'categories'
  | 'dashboard'
  | 'exams'
  | 'lectures'
  | 'security'
  | 'settings'
  | 'users'

export type SidebarProps = HTMLAttributes<HTMLElement> & {
  activeItem?: AppSidebarActiveItem
  onNavigate?: (path: string) => void
  onLogout?: () => void
  userEmail?: string
  userName?: string
}

/* kept for backwards compat with app-shell prop types */
export type SidebarItem = {
  active?: boolean
  badge?: string | number
  disabled?: boolean
  icon: IconName
  label: string
  onSelect?: () => void | Promise<void>
}

export type SidebarSection = {
  items: SidebarItem[]
  label: string
}

function getInitials(name: string) {
  return (
    name
      .trim()
      .split(/\s+/)
      .slice(0, 2)
      .map((p) => p[0])
      .join('')
      .toUpperCase() || 'U'
  )
}

type NavItemDef = {
  id: string
  label: string
  icon: IconName
  count?: string
  chev?: boolean
  disabled?: boolean
  path?: string
  action?: 'logout'
}

const menuItems: NavItemDef[] = [
  { id: 'dashboard', label: 'Painel', icon: 'home', path: '/dashboard' },
  { id: 'exams', label: 'Provas', icon: 'layers', count: '124', path: '/exams' },
  { id: 'flashcards', label: 'Flashcards', icon: 'bookOpen', count: '2.1k', disabled: true },
  { id: 'lectures', label: 'Transcrições', icon: 'clipboard', path: '/lectures' },
  { id: 'categories', label: 'Matérias', icon: 'tag', path: '/categories' },
  { id: 'calendario', label: 'Calendário', icon: 'calendar', disabled: true },
  { id: 'analytics', label: 'Análises', icon: 'chart', chev: true, disabled: true },
]

const workflowItems: NavItemDef[] = [
  { id: 'gerar', label: 'Gerar prova', icon: 'zap', path: '/exams' },
  { id: 'importar', label: 'Importar material', icon: 'upload', path: '/exams' },
  { id: 'anotacoes', label: 'Anotações', icon: 'fileText', disabled: true },
  { id: 'equipe', label: 'Grupos de estudo', icon: 'users', disabled: true },
]

const generalItems: NavItemDef[] = [
  { id: 'settings', label: 'Configurações', icon: 'settings', disabled: true },
  { id: 'ajuda', label: 'Ajuda', icon: 'helpCircle', disabled: true },
  { id: 'sair', label: 'Sair', icon: 'logOut', action: 'logout' },
]

export function Sidebar({
  activeItem,
  className,
  onNavigate,
  onLogout,
  userEmail,
  userName,
  ...props
}: SidebarProps) {
  const [footOpen, setFootOpen] = useState(false)
  const footWrapRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!footOpen) return
    function onPointerDown(e: PointerEvent) {
      if (footWrapRef.current && !footWrapRef.current.contains(e.target as Node)) {
        setFootOpen(false)
      }
    }
    document.addEventListener('pointerdown', onPointerDown)
    return () => document.removeEventListener('pointerdown', onPointerDown)
  }, [footOpen])

  function handleItem(item: NavItemDef) {
    if (item.disabled) return
    if (item.action === 'logout') { setFootOpen(false); onLogout?.(); return }
    if (item.path) { setFootOpen(false); onNavigate?.(item.path) }
  }

  function NavItem({ item }: { item: NavItemDef }) {
    const isActive = item.id === activeItem
    return (
      <button
        className={cn('nav-item', isActive && 'active')}
        disabled={item.disabled}
        onClick={() => handleItem(item)}
        type="button"
      >
        <Icon className="ico" name={item.icon} size={16} strokeWidth={1.65} />
        <span>{item.label}</span>
        {item.count ? <span className="nav-count">{item.count}</span> : null}
        {item.chev ? (
          <Icon
            className="nav-chev"
            name="chevronRight"
            size={13}
            strokeWidth={1.65}
          />
        ) : null}
      </button>
    )
  }

  return (
    <aside className={cn('sidebar', className)} {...props}>
      {/* Brand */}
      <div className="brand">
        <div className="brand-mark" aria-hidden="true">M</div>
        <div style={{ minWidth: 0 }}>
          <div className="brand-name">Murshid</div>
          <div className="brand-sub">Plataforma de estudos</div>
        </div>
        <Icon className="brand-chev" name="chevronDown" size={13} strokeWidth={1.65} />
      </div>

      {/* Scrollable nav */}
      <div className="sidebar-nav">
        <div className="nav-section">
          <div className="nav-section-label">Menu Principal</div>
          {menuItems.map((item) => <NavItem key={item.id} item={item} />)}
        </div>

        <div className="nav-section">
          <div className="nav-section-label">Workflow</div>
          {workflowItems.map((item) => <NavItem key={item.id} item={item} />)}
        </div>
      </div>

      {/* Footer with popover */}
      <div className="sidebar-foot-wrap" ref={footWrapRef}>
        {footOpen && (
          <div className="foot-popover">
            {generalItems.map((item) => <NavItem key={item.id} item={item} />)}
          </div>
        )}
        <button
          className="sidebar-foot"
          onClick={() => setFootOpen((v) => !v)}
          type="button"
        >
          <div className="avatar" aria-hidden="true">
            {getInitials(userName ?? userEmail ?? 'U')}
          </div>
          <div style={{ minWidth: 0, flex: 1 }}>
            {userName ? <div className="user-name">{userName}</div> : null}
            {userEmail ? (
              <div
                className="user-mail"
                style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
              >
                {userEmail}
              </div>
            ) : null}
          </div>
          <Icon
            name={footOpen ? 'chevronDown' : 'chevronRight'}
            size={13}
            strokeWidth={1.65}
            style={{ color: 'var(--ink-4)', flexShrink: 0 }}
          />
        </button>
      </div>
    </aside>
  )
}
