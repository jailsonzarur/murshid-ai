import { motion } from 'motion/react'

import { cardStaggerTransition } from '../../lib/motion'
import type { SubjectDocument } from '../../types/lecture'
import { CutoutCorner } from '../ui/cutout'
import { EmptyState } from '../ui/empty-state'
import { Icon } from '../ui/icon'

type SubjectDocumentsScreenProps = {
  documents: SubjectDocument[]
  isLoading: boolean
  onRemove: (documentId: string) => void
  removingId: string | null
}

const KIND_BY_MIME: Record<string, { label: string; tone: string }> = {
  'application/pdf': { label: 'PDF', tone: 'pdf' },
  'text/plain': { label: 'TXT', tone: 'txt' },
  'text/markdown': { label: 'MD', tone: 'md' },
}

function kindOf(document: SubjectDocument) {
  return KIND_BY_MIME[document.mime_type] ?? { label: 'DOC', tone: 'txt' }
}

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export function SubjectDocumentsScreen({
  documents,
  isLoading,
  onRemove,
  removingId,
}: SubjectDocumentsScreenProps) {
  if (isLoading) {
    return <EmptyState description="Buscando a bibliografia da matéria." title="Carregando..." />
  }

  if (documents.length === 0) {
    return (
      <EmptyState
        description="Os documentos são anexados na criação da matéria e alimentam os resumos guiados."
        title="Nenhum documento anexado."
      />
    )
  }

  return (
    <motion.div
      animate="show"
      className="doc-grid"
      initial="hidden"
      variants={cardStaggerTransition.container}
    >
      {documents.map((document) => {
        const kind = kindOf(document)
        return (
          <motion.article
            className="doc-card"
            data-tone={kind.tone}
            key={document.id}
            variants={cardStaggerTransition.item}
          >
            <div className="doc-card__media">
              {/* placeholder: a capa real vem quando o pipeline de ingestão existir */}
              <span aria-hidden="true" className="doc-card__glyph">
                <Icon name="fileText" size={38} />
              </span>

              <div className="doc-card__kind">
                {kind.label}
                <CutoutCorner className="doc-card__corner doc-card__corner--kind-left" size={20} />
                <CutoutCorner className="doc-card__corner doc-card__corner--kind-bottom" size={20} />
              </div>

              <div className="doc-card__size">
                {formatBytes(document.size_bytes)}
                <CutoutCorner className="doc-card__corner doc-card__corner--size-right" size={20} />
                <CutoutCorner className="doc-card__corner doc-card__corner--size-top" size={20} />
              </div>
            </div>

            <div className="doc-card__body">
              <h3 className="doc-card__title" title={document.original_name}>
                {document.title}
              </h3>
              <p className="doc-card__file" title={document.original_name}>
                {document.original_name}
              </p>
            </div>

            <button
              aria-label={`Remover ${document.original_name}`}
              className="doc-card__remove"
              disabled={removingId === document.id}
              onClick={() => onRemove(document.id)}
              type="button"
            >
              <Icon name="trash" size={14} />
            </button>
          </motion.article>
        )
      })}
    </motion.div>
  )
}
