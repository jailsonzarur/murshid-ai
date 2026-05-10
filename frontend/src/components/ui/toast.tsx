import { useEffect, useState } from 'react'

import { TOAST_EVENT, type ToastPayload } from '../../lib/toast'
import { Icon } from './icon'

type ToastItem = ToastPayload & {
  id: number
}

const toastDuration = 5200

export function ToastViewport() {
  const [toasts, setToasts] = useState<ToastItem[]>([])

  useEffect(() => {
    function handleToast(event: Event) {
      const payload = (event as CustomEvent<ToastPayload>).detail
      const id = Date.now() + Math.random()

      setToasts((current) => [...current, { ...payload, id }])
      window.setTimeout(() => {
        setToasts((current) => current.filter((toast) => toast.id !== id))
      }, toastDuration)
    }

    window.addEventListener(TOAST_EVENT, handleToast)

    return () => {
      window.removeEventListener(TOAST_EVENT, handleToast)
    }
  }, [])

  function dismissToast(id: number) {
    setToasts((current) => current.filter((toast) => toast.id !== id))
  }

  return (
    <div className="toast-viewport" aria-live="polite" aria-relevant="additions">
      {toasts.map((toast) => (
        <div className={`toast-card toast-card--${toast.tone}`} key={toast.id} role="status">
          <div className="toast-card__icon">
            <Icon name={toast.tone === 'error' ? 'x' : 'alertTriangle'} size={16} />
          </div>
          <div className="toast-card__content">
            <strong>{toast.title}</strong>
            <p>{toast.message}</p>
          </div>
          <button
            aria-label="Fechar aviso"
            className="toast-card__close"
            onClick={() => dismissToast(toast.id)}
            type="button"
          >
            <Icon name="x" size={14} />
          </button>
        </div>
      ))}
    </div>
  )
}
