import { useEffect, type CSSProperties, type ReactNode } from 'react'
import { createPortal } from 'react-dom'
import { AnimatePresence, motion } from 'motion/react'

import { cn } from '../../lib/cn'
import { screenMorphTransition } from '../../lib/motion'
import { Icon } from './icon'

type ExpandableScreenTriggerProps = {
  children: ReactNode
  className?: string
  isOpen: boolean
  layoutId: string
}

export function ExpandableScreenTrigger({
  children,
  className,
  isOpen,
  layoutId,
}: ExpandableScreenTriggerProps) {
  return (
    <span className={cn('screen-trigger', className)}>
      <AnimatePresence initial={false}>
        {isOpen ? null : (
          <motion.span
            className="screen-trigger__bg"
            key="bg"
            layoutId={layoutId}
            transition={screenMorphTransition}
          />
        )}
      </AnimatePresence>
      <motion.span
        animate={{ opacity: isOpen ? 0 : 1 }}
        className="screen-trigger__content"
        transition={{ duration: 0.15 }}
      >
        {children}
      </motion.span>
    </span>
  )
}

function useDismiss(isOpen: boolean, onClose: () => void) {
  useEffect(() => {
    if (!isOpen) return

    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'

    function onKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') onClose()
    }

    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.body.style.overflow = previousOverflow
      document.removeEventListener('keydown', onKeyDown)
    }
  }, [isOpen, onClose])
}

type ExpandableSurfaceProps = {
  children: ReactNode
  isOpen: boolean
  label: string
  layoutId: string
  onClose: () => void
  panelClassName?: string
  panelStyle?: CSSProperties
}

function ExpandableSurface({
  children,
  isOpen,
  label,
  layoutId,
  onClose,
  panelClassName,
  panelStyle,
}: ExpandableSurfaceProps) {
  useDismiss(isOpen, onClose)

  return createPortal(
    <AnimatePresence initial={false}>
      {isOpen ? (
        <div className="screen-layer" key="layer">
          <motion.div
            animate={{ opacity: 1 }}
            className="screen-scrim"
            exit={{ opacity: 0 }}
            initial={{ opacity: 0 }}
            onClick={onClose}
            transition={{ duration: 0.2 }}
          />
          <motion.div
            aria-label={label}
            aria-modal="true"
            className={cn('screen-panel', panelClassName)}
            layoutId={layoutId}
            style={panelStyle}
            role="dialog"
            transition={screenMorphTransition}
          >
            <motion.div
              animate={{ opacity: 1 }}
              className="screen-panel__inner"
              initial={{ opacity: 0 }}
              transition={{ delay: 0.12, duration: 0.25 }}
            >
              {children}
            </motion.div>
          </motion.div>
        </div>
      ) : null}
    </AnimatePresence>,
    document.body,
  )
}

type ExpandableScreenProps = {
  children: ReactNode
  description?: string
  isOpen: boolean
  layoutId: string
  onClose: () => void
  title: string
}

export function ExpandableScreen({
  children,
  description,
  isOpen,
  layoutId,
  onClose,
  title,
}: ExpandableScreenProps) {
  return (
    <ExpandableSurface isOpen={isOpen} label={title} layoutId={layoutId} onClose={onClose}>
      <header className="screen-panel__head">
        <div>
          <h2 className="screen-panel__title">{title}</h2>
          {description ? <p className="screen-panel__sub">{description}</p> : null}
        </div>
        <button aria-label="Fechar" className="icon-btn" onClick={onClose} type="button">
          <Icon name="x" size={18} />
        </button>
      </header>
      <div className="screen-panel__body">{children}</div>
    </ExpandableSurface>
  )
}

type ExpandableModalProps = {
  children: ReactNode
  isOpen: boolean
  label: string
  layoutId: string
  onClose: () => void
  width?: number
}

export function ExpandableModal({
  children,
  isOpen,
  label,
  layoutId,
  onClose,
  width = 640,
}: ExpandableModalProps) {
  return (
    <ExpandableSurface
      isOpen={isOpen}
      label={label}
      layoutId={layoutId}
      onClose={onClose}
      panelClassName="screen-panel--modal"
      panelStyle={{ width: `min(${width}px, 100%)` }}
    >
      {children}
    </ExpandableSurface>
  )
}
