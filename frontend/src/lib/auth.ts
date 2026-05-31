const AUTH_STORAGE_KEY = 'iasmim.auth'

export type AuthProfile = {
  name: string
  email: string
  role: string
}

export type AuthSession = {
  accessToken: string
  refreshToken: string
  tokenType: string
  profile?: AuthProfile | null
}

function readStorage(storage: Storage) {
  const rawValue = storage.getItem(AUTH_STORAGE_KEY)

  if (!rawValue) {
    return null
  }

  try {
    return JSON.parse(rawValue) as AuthSession
  } catch {
    storage.removeItem(AUTH_STORAGE_KEY)
    return null
  }
}

function getSessionStorage() {
  if (readStorage(window.localStorage)) {
    return window.localStorage
  }

  if (readStorage(window.sessionStorage)) {
    return window.sessionStorage
  }

  return null
}

export function saveAuthSession(session: AuthSession, persist: boolean) {
  const storage = persist ? window.localStorage : window.sessionStorage
  const otherStorage = persist ? window.sessionStorage : window.localStorage

  otherStorage.removeItem(AUTH_STORAGE_KEY)
  storage.setItem(AUTH_STORAGE_KEY, JSON.stringify(session))
}

export function saveAuthProfile(profile: AuthProfile) {
  const storage = getSessionStorage()
  const session = storage ? readStorage(storage) : null

  if (!storage || !session) {
    return
  }

  storage.setItem(
    AUTH_STORAGE_KEY,
    JSON.stringify({
      ...session,
      profile,
    }),
  )
}

export function getAuthSession() {
  return readStorage(window.localStorage) ?? readStorage(window.sessionStorage)
}

export function getAuthProfile() {
  return getAuthSession()?.profile ?? null
}

export function getAccessToken() {
  return getAuthSession()?.accessToken ?? null
}

export function getAuthorizationHeader() {
  const session = getAuthSession()

  if (!session) {
    return null
  }

  return `Bearer ${session.accessToken}`
}

export function clearAuthSession() {
  window.localStorage.removeItem(AUTH_STORAGE_KEY)
  window.sessionStorage.removeItem(AUTH_STORAGE_KEY)
}

export function isTokenExpired(): boolean {
  const token = getAccessToken()
  if (!token) return true

  try {
    const base64 = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')
    const payload = JSON.parse(atob(base64)) as { exp?: number }
    if (!payload.exp) return false
    return Date.now() / 1000 > payload.exp
  } catch {
    return true
  }
}
