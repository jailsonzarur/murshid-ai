import { useEffect, useState } from 'react'

import './App.css'
import { ToastViewport } from './components/ui/toast'
import { clearAuthSession, getAccessToken, isTokenExpired } from './lib/auth'
import { NAVIGATION_EVENT, navigateTo } from './lib/navigation'
import { SubjectsPage } from './pages/subjects'
import { DashboardPage } from './pages/dashboard'
import { LectureRecordPage } from './pages/lecture-record'
import { LecturesPage } from './pages/lectures'
import { LectureViewerPage } from './pages/lecture-viewer'
import { LoginPage } from './pages/login'

const routes = {
  '/': LoginPage,
  '/login': LoginPage,
  '/dashboard': DashboardPage,
  '/lectures': LecturesPage,
  '/subjects': SubjectsPage,
}

const protectedRoutes = new Set(['/dashboard', '/lectures', '/subjects'])

function normalizePathname(pathname: string) {
  if (pathname.length > 1 && pathname.endsWith('/')) {
    return pathname.slice(0, -1)
  }

  return pathname
}

function isProtectedPath(pathname: string) {
  const normalizedPathname = normalizePathname(pathname)
  return (
    protectedRoutes.has(normalizedPathname) ||
    /^\/lectures\/[^/]+(\/record)?$/.test(normalizedPathname)
  )
}

function resolvePath(pathname: string) {
  const normalizedPathname = normalizePathname(pathname)
  const token = getAccessToken()
  const hasSession = Boolean(token) && !isTokenExpired()

  if (token && !hasSession) {
    clearAuthSession()
  }

  if (hasSession) {
    return isProtectedPath(normalizedPathname) ? normalizedPathname : '/dashboard'
  }

  if (isProtectedPath(normalizedPathname)) {
    return '/login'
  }

  return '/login'
}

function App() {
  const [pathname, setPathname] = useState(() => resolvePath(window.location.pathname))

  useEffect(() => {
    function syncPath() {
      const nextPath = resolvePath(window.location.pathname)

      if (window.location.pathname !== nextPath) {
        navigateTo(nextPath, { replace: true })
        return
      }

      setPathname(nextPath)
    }

    syncPath()
    window.addEventListener('popstate', syncPath)
    window.addEventListener(NAVIGATION_EVENT, syncPath)

    return () => {
      window.removeEventListener('popstate', syncPath)
      window.removeEventListener(NAVIGATION_EVENT, syncPath)
    }
  }, [])

  const normalizedPathname = normalizePathname(pathname)
  const Page = /^\/lectures\/[^/]+\/record$/.test(normalizedPathname)
    ? LectureRecordPage
    : /^\/lectures\/[^/]+$/.test(normalizedPathname)
      ? LectureViewerPage
      : routes[pathname as keyof typeof routes] ?? LoginPage

  return (
    <>
      <Page />
      <ToastViewport />
    </>
  )
}

export default App
