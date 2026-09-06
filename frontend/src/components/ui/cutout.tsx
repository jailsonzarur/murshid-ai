import type { SVGProps } from 'react'

import { cn } from '../../lib/cn'

const CORNER_PATH = 'M0 200C155.996 199.961 200.029 156.308 200 0V200H0Z'

type CutoutCornerProps = SVGProps<SVGSVGElement> & {
  size?: number
}

/**
 * Quarto de círculo côncavo. Preenchido com a cor do card e posicionado ao lado
 * de um recorte retangular, cria a ilusão de que o recorte foi vazado na peça.
 */
export function CutoutCorner({ className, size = 24, ...props }: CutoutCornerProps) {
  return (
    <svg
      aria-hidden="true"
      className={cn('cutout-corner', className)}
      height={size}
      viewBox="0 0 200 200"
      width={size}
      xmlns="http://www.w3.org/2000/svg"
      {...props}
    >
      <path d={CORNER_PATH} fill="currentColor" />
    </svg>
  )
}
