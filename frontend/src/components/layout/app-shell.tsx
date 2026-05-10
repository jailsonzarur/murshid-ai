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
  searchPlaceholder?: string
  title: string
  userEmail?: string
  userName?: string
}

function createNavigationSections(activeItem: AppShellActiveItem, onLogout: () => void): SidebarSection[] {
  return [
    {
      label: 'Menu',
      items: [
        {
          active: activeItem === 'dashboard',
          icon: 'home',
          label: 'Dashboard',
          onSelect: () => navigateTo('/dashboard'),
        },
        {
          active: activeItem === 'exams',
          badge: 124,
          icon: 'layers',
          label: 'Provas',
          onSelect: () => navigateTo('/exams'),
        },
        {
          disabled: true,
          icon: 'calendar',
          label: 'Calendar',
        },
        {
          active: activeItem === 'analytics',
          disabled: true,
          icon: 'chart',
          label: 'Analytics',
        },
        {
          active: activeItem === 'users',
          disabled: true,
          icon: 'users',
          label: 'Team',
        },
      ],
    },
    {
      label: 'General',
      items: [
        {
          active: activeItem === 'settings',
          disabled: true,
          icon: 'settings',
          label: 'Settings',
        },
        {
          disabled: true,
          icon: 'helpCircle',
          label: 'Help',
        },
        {
          icon: 'logOut',
          label: 'Logout',
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
  searchPlaceholder,
  title,
  userEmail,
  userName,
}: AppShellProps) {
  const profile = getAuthProfile()
  const resolvedUserName = userName ?? profile?.name ?? 'Usuário'
  const resolvedUserEmail = userEmail ?? profile?.email ?? 'Sessão ativa'

  function handleLogout() {
    clearAuthSession()
    navigateTo('/login', { replace: true })
  }

  return (
    <main className="app-shell">
      <Sidebar
        brandLabel="IAsmim"
        brandSubtitle="OCR médico"
        sections={createNavigationSections(activeItem, handleLogout)}
      />

      <section className="app-main">
        <Topbar
          actions={actions}
          description={description}
          onLogout={handleLogout}
          searchPlaceholder={searchPlaceholder}
          title={title}
          userEmail={resolvedUserEmail}
          userName={resolvedUserName}
        />

        <div className={cn('app-content', contentClassName)}>{children}</div>
      </section>
    </main>
  )
}
