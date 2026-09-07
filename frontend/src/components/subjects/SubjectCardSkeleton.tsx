import type { Ref } from 'react'
import { motion } from 'motion/react'

import { cardReveal, SKELETON_STAGGER, skeletonEnter } from '../../lib/motion'

const TILE_COUNT = 3

export function SubjectCardSkeleton({
  index,
  ref,
}: {
  index: number
  ref?: Ref<HTMLDivElement>
}) {
  return (
    <motion.div
      animate={skeletonEnter.animate}
      aria-hidden="true"
      className="subject-card subject-skeleton"
      ref={ref}
      exit={cardReveal.exit}
      initial={skeletonEnter.initial}
      transition={{ duration: 0.28, delay: index * SKELETON_STAGGER, ease: [0.2, 0, 0, 1] }}
    >
      <div className="subject-card__head">
        <span className="skeleton skeleton--avatar" />
        <span className="skeleton skeleton--title" />
        <span className="skeleton skeleton--count" />
      </div>

      <div className="subject-card__panel-inner">
        <span className="skeleton skeleton--label" />

        <div className="subject-strip">
          {Array.from({ length: TILE_COUNT }, (_, tile) => (
            <span className="skeleton skeleton--tile" key={tile} />
          ))}
        </div>

        <div className="subject-card__actions">
          <span className="skeleton skeleton--button" />
          <span className="skeleton skeleton--button" />
        </div>
      </div>
    </motion.div>
  )
}

export function PaginationSkeleton() {
  return (
    <div aria-hidden="true" className="pagination">
      <span className="skeleton skeleton--summary" />
      <div className="pagination__pages">
        {Array.from({ length: 5 }, (_, index) => (
          <span className="skeleton skeleton--page" key={index} />
        ))}
      </div>
    </div>
  )
}
