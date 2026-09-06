import { useEffect, type ReactNode } from 'react'
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

/** Mantém o botão no fluxo enquanto a tela está aberta; só o fundo com layoutId viaja. */
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

  // fora da árvore do card: um ancestral com transform (o layout do Motion)
  // vira containing block e quebraria o position: fixed
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
            aria-label={title}
            aria-modal="true"
            className="screen-panel"
            layoutId={layoutId}
            role="dialog"
            transition={screenMorphTransition}
          >
            <motion.div
              animate={{ opacity: 1 }}
              className="screen-panel__inner"
              initial={{ opacity: 0 }}
              transition={{ delay: 0.12, duration: 0.25 }}
            >
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
            </motion.div>
          </motion.div>
        </div>
      ) : null}
    </AnimatePresence>,
    document.body,
  )
}
