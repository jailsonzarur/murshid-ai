import type { ReactNode } from 'react'

import { clearAuthSession, getAuthProfile } from '../../lib/auth'
import { cn } from '../../lib/cn'
import { navigateTo } from '../../lib/navigation'
import { Sidebar, type SidebarSection } from '../ui/sidebar'
import { Topbar } from '../ui/topbar'

export type AppShellActiveItem =
  | 'analytics'
  | 'dashboard'
  | 'exams'
  | 'security'
  | 'settings'
  | 'users'

export type AppShellProps = {
  actions?: ReactNode
  activeItem: AppShellActiveItem
  children: ReactNode
  contentClassName?: string
  description: string
  onBeforeLeave?: () => void | Promise<void>
  searchPlaceholder?: string
  title: string
  userEmail?: string
  userName?: string
}

function createNavigationSections(
  activeItem: AppShellActiveItem,
  onNavigate: (path: string) => Promise<void>,
  onLogout: () => Promise<void>,
): SidebarSection[] {
  return [
    {
      label: 'Menu',
      items: [
        {
          active: activeItem === 'dashboard',
          icon: 'home',
          label: 'Painel',
          onSelect: () => onNavigate('/dashboard'),
        },
        {
          active: activeItem === 'exams',
          badge: 124,
          icon: 'layers',
          label: 'Provas',
          onSelect: () => onNavigate('/exams'),
        },
        {
          disabled: true,
          icon: 'calendar',
          label: 'Calendário',
        },
        {
          active: activeItem === 'analytics',
          disabled: true,
          icon: 'chart',
          label: 'Análises',
        },
        {
          active: activeItem === 'users',
          disabled: true,
          icon: 'users',
          label: 'Equipe',
        },
      ],
    },
    {
      label: 'Geral',
      items: [
        {
          active: activeItem === 'settings',
          disabled: true,
          icon: 'settings',
          label: 'Configurações',
        },
        {
          disabled: true,
          icon: 'helpCircle',
          label: 'Ajuda',
        },
        {
          icon: 'logOut',
          label: 'Sair',
          onSelect: onLogout,
        },
      ],
    },
  ]
}

export function AppShell({
  actions,
  activeItem,
  children,
  contentClassName,
  description,
  onBeforeLeave,
  searchPlaceholder,
  title,
  userEmail,
  userName,
}: AppShellProps) {
  const profile = getAuthProfile()
  const resolvedUserName = userName ?? profile?.name ?? 'Usuário'
  const resolvedUserEmail = userEmail ?? profile?.email ?? 'Sessão ativa'

  async function handleNavigate(path: string) {
    await onBeforeLeave?.()
    navigateTo(path)
  }

  async function handleLogout() {
    await onBeforeLeave?.()
    clearAuthSession()
    navigateTo('/login', { replace: true })
  }

  return (
    <div className="app">
      <Sidebar
        brandLabel="Murshid"
        brandSubtitle="Plataforma de estudo"
        sections={createNavigationSections(activeItem, handleNavigate, handleLogout)}
      />

      <main className="main">
        <Topbar
          onLogout={handleLogout}
          searchPlaceholder={searchPlaceholder}
          userEmail={resolvedUserEmail}
          userName={resolvedUserName}
        />

        <div className={cn('page', contentClassName)}>
          {(title || description || actions) ? (
            <div className="page-head">
              <div>
                {title ? <h1 className="page-title">{title}</h1> : null}
                {description ? <p className="page-sub">{description}</p> : null}
              </div>
              {actions ? <div className="page-actions">{actions}</div> : null}
            </div>
          ) : null}
          {children}
        </div>
      </main>
    </div>
  )
}
