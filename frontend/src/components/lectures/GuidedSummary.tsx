import { Fragment, useMemo, useState } from 'react'
import ReactMarkdown from 'react-markdown'

import type { GuidedCitation, GuidedCitationExcerpt } from '../../types/lecture'
import { Icon } from '../ui/icon'

type GuidedSummaryProps = {
  citations: GuidedCitation[]
  markdown: string
}

const CITATION = /\[\[(\d+)\]\]/g

export function GuidedSummary({ citations, markdown }: GuidedSummaryProps) {
  const [open, setOpen] = useState<GuidedCitationExcerpt | null>(null)

  const byNumber = useMemo(() => {
    const index = new Map<number, GuidedCitationExcerpt>()
    for (const citation of citations) {
      for (const excerpt of citation.excerpts) index.set(excerpt.n, excerpt)
    }
    return index
  }, [citations])

  const blocks = useMemo(() => markdown.split(CITATION), [markdown])

  return (
    <div className="guided">
      <div className="guided__body">
        {blocks.map((block, index) =>
          index % 2 === 1 ? (
            <CitationBadge
              excerpt={byNumber.get(Number(block))}
              key={`c${index}`}
              number={Number(block)}
              onOpen={setOpen}
            />
          ) : (
            <Fragment key={`t${index}`}>
              <ReactMarkdown>{block}</ReactMarkdown>
            </Fragment>
          ),
        )}
      </div>

      {open ? (
        <aside className="guided__panel">
          <div className="guided__panel-head">
            <span className="guided__panel-badge">{open.n}</span>
            <div>
              <p className="guided__panel-path">{open.heading_path}</p>
              {open.page_start ? (
                <p className="guided__panel-page">página {open.page_start}</p>
              ) : null}
            </div>
            <button
              aria-label="Fechar"
              className="guided__panel-close"
              onClick={() => setOpen(null)}
              type="button"
            >
              <Icon name="x" size={14} />
            </button>
          </div>
          <p className="guided__panel-text">{open.text}</p>
        </aside>
      ) : null}
    </div>
  )
}

type CitationBadgeProps = {
  excerpt: GuidedCitationExcerpt | undefined
  number: number
  onOpen: (excerpt: GuidedCitationExcerpt) => void
}

function CitationBadge({ excerpt, number, onOpen }: CitationBadgeProps) {
  if (!excerpt) return null

  return (
    <button
      className="guided__cite"
      onClick={() => onOpen(excerpt)}
      title={excerpt.heading_path}
      type="button"
    >
      {number}
    </button>
  )
}
