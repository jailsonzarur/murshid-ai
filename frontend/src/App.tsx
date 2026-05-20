import { useEffect, useState } from 'react'

import './App.css'
import { ToastViewport } from './components/ui/toast'
import { getAccessToken } from './lib/auth'
import { NAVIGATION_EVENT, navigateTo } from './lib/navigation'
import { DashboardPage } from './pages/dashboard'
import { ExamViewerPage } from './pages/exam-viewer'
import { ExamsPage } from './pages/exams'
import { LoginPage } from './pages/login'
import { ResolutionViewerPage } from './pages/resolution-viewer'

const routes = {
  '/': LoginPage,
  '/login': LoginPage,
  '/dashboard': DashboardPage,
  '/exams': ExamsPage,
}

const protectedRoutes = new Set(['/dashboard', '/exams'])

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
    /^\/exams\/[^/]+$/.test(normalizedPathname) ||
    /^\/resolutions\/[^/]+$/.test(normalizedPathname)
  )
}

function resolvePath(pathname: string) {
  const normalizedPathname = normalizePathname(pathname)
  const hasSession = Boolean(getAccessToken())

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
  const Page = /^\/resolutions\/[^/]+$/.test(normalizedPathname)
    ? ResolutionViewerPage
    : /^\/exams\/[^/]+$/.test(normalizedPathname)
      ? ExamViewerPage
      : routes[pathname as keyof typeof routes] ?? LoginPage

  return (
    <>
      <Page />
      <ToastViewport />
    </>
  )
}

export default App
