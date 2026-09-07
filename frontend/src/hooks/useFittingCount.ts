import { useEffect, useState, type RefObject } from 'react'

type Options = {
  itemWidth: number
  gap: number
  total: number
}

/**
 * Quantos itens cabem na largura real do container. Reserva um slot para o
 * indicador de excedente quando nem todos couberem.
 */
export function useFittingCount(ref: RefObject<HTMLElement | null>, { itemWidth, gap, total }: Options) {
  const [width, setWidth] = useState(0)

  useEffect(() => {
    const element = ref.current
    if (!element) return

    const observer = new ResizeObserver(([entry]) => setWidth(entry.contentRect.width))
    observer.observe(element)
    return () => observer.disconnect()
  }, [ref])

  if (width === 0) return total

  const capacity = Math.max(0, Math.floor((width + gap) / (itemWidth + gap)))
  if (total <= capacity) return total
  return Math.max(1, capacity - 1)
}
