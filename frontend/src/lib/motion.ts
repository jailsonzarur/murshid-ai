import type { Transition, Variants } from 'motion/react'

const spring = { type: 'spring', stiffness: 300, damping: 32, mass: 0.9 } as const

export const layoutTransition: Transition = spring

export const screenMorphTransition: Transition = {
  type: 'spring',
  stiffness: 260,
  damping: 30,
  mass: 0.9,
}

export const cardStaggerTransition: { container: Variants; item: Variants } = {
  container: {
    hidden: {},
    show: { transition: { staggerChildren: 0.045 } },
  },
  item: {
    hidden: { opacity: 0, y: 12 },
    show: { opacity: 1, y: 0, transition: { duration: 0.28, ease: [0.2, 0, 0, 1] } },
  },
}
