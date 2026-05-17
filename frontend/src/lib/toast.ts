export type ToastTone = 'error' | 'warning'

export type ToastPayload = {
  message: string
  tone: ToastTone
  title?: string
}

export const TOAST_EVENT = 'iasmim:toast'

export function showToast(payload: ToastPayload) {
  window.dispatchEvent(new CustomEvent<ToastPayload>(TOAST_EVENT, { detail: payload }))
}

export function showErrorToast(message: string, title = 'Erro') {
  showToast({ message, title, tone: 'error' })
}

export function showWarningToast(message: string, title = 'Atenção') {
  showToast({ message, title, tone: 'warning' })
}
