import type { ReactNode } from 'react'

import { clearAuthSession, getAuthProfile } from '../../lib/auth'
import { cn } from '../../lib/cn'
import { navigateTo } from '../../lib/navigation'
import { Sidebar } from '../ui/sidebar'
import { Topbar } from '../ui/topbar'

export type AppShellActiveItem =
  | 'analytics'
  | 'categories'
  | 'dashboard'
  | 'exams'
  | 'lectures'
  | 'security'
  | 'settings'
  | 'users'

export type AppShellProps = {
  actions?: ReactNode
  activeItem: AppShellActiveItem
  children: ReactNode
  contentClassName?: string
  description?: string
  onBeforeLeave?: () => void | Promise<void>
  searchPlaceholder?: string
  title?: string
  userEmail?: string
  userName?: string
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
        activeItem={activeItem}
        onNavigate={handleNavigate}
        onLogout={handleLogout}
        userEmail={resolvedUserEmail}
        userName={resolvedUserName}
      />

      <main className="main">
        <Topbar
          onGenerateExam={() => handleNavigate('/exams')}
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
