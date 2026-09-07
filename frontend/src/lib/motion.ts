import type { Transition, Variants } from 'motion/react'

const spring = { type: 'spring', stiffness: 300, damping: 32, mass: 0.9 } as const

export const layoutTransition: Transition = spring

export const screenMorphTransition: Transition = {
  type: 'spring',
  stiffness: 260,
  damping: 30,
  mass: 0.9,
}

export const navPillTransition: Transition = {
  type: 'spring',
  bounce: 0.19,
  duration: 0.4,
}

const revealEase = [0.2, 0, 0, 1] as const

export const cardReveal = {
  initial: { opacity: 0, scale: 0.92 },
  animate: {
    opacity: 1,
    scale: 1,
    transition: { duration: 0.45, ease: revealEase },
  },
  exit: {
    opacity: 0,
    scale: 0.92,
    transition: { duration: 0.3, ease: revealEase },
  },
}

export const skeletonEnter = {
  initial: { opacity: 0, y: -12 },
  animate: { opacity: 1, y: 0 },
}

export const SKELETON_STAGGER = 0.045

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
