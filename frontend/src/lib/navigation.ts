export const NAVIGATION_EVENT = 'iasmim:navigate'

type NavigateOptions = {
  replace?: boolean
}

export function navigateTo(path: string, options: NavigateOptions = {}) {
  if (options.replace) {
    window.history.replaceState({}, '', path)
  } else {
    window.history.pushState({}, '', path)
  }

  window.dispatchEvent(new Event(NAVIGATION_EVENT))
}
