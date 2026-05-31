import { useEffect, useState } from 'react'

import { TOAST_EVENT, type ToastPayload } from '../../lib/toast'
import { Icon } from './icon'

type ToastItem = ToastPayload & {
  id: number
  isExiting: boolean
}

const toastDuration = 5000
const exitDuration = 300

export function ToastViewport() {
  const [toasts, setToasts] = useState<ToastItem[]>([])

  function startExiting(id: number) {
    setToasts((current) =>
      current.map((t) => (t.id === id ? { ...t, isExiting: true } : t)),
    )
    window.setTimeout(() => {
      setToasts((current) => current.filter((t) => t.id !== id))
    }, exitDuration)
  }

  useEffect(() => {
    function handleToast(event: Event) {
      const payload = (event as CustomEvent<ToastPayload>).detail
      const id = Date.now() + Math.random()

      setToasts((current) => [...current, { ...payload, id, isExiting: false }])
      window.setTimeout(() => startExiting(id), toastDuration)
    }

    window.addEventListener(TOAST_EVENT, handleToast)
    return () => window.removeEventListener(TOAST_EVENT, handleToast)
  }, [])

  return (
    <div aria-live="polite" aria-relevant="additions" className="toast-viewport">
      {toasts.map((toast) => (
        <div
          className={`toast-card toast-card--${toast.tone}${toast.isExiting ? ' toast-card--exiting' : ''}`}
          key={toast.id}
          role="status"
        >
          <div className="toast-card__icon">
            <Icon name={toast.tone === 'error' ? 'x' : 'alertTriangle'} size={15} />
          </div>
          <div className="toast-card__content">
            <strong>{toast.title}</strong>
            <p>{toast.message}</p>
          </div>
          <button
            aria-label="Fechar aviso"
            className="toast-card__close"
            onClick={() => startExiting(toast.id)}
            type="button"
          >
            <Icon name="x" size={13} />
          </button>
        </div>
      ))}
    </div>
  )
}
