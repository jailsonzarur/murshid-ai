import { memo, useRef, useState } from 'react'
import { motion } from 'motion/react'

import { useFittingCount } from '../../hooks/useFittingCount'
import { ApiError, deleteSubjectDocument } from '../../lib/api'
import { layoutTransition } from '../../lib/motion'
import type { SubjectDetail, SubjectDocument } from '../../types/lecture'
import { ExpandableScreen, ExpandableScreenTrigger } from '../ui/expandable-screen'
import { Icon } from '../ui/icon'
import { SubjectDocumentsScreen } from './SubjectDocumentsScreen'

const TILE_WIDTH = 40
const TILE_GAP = 8

type SubjectCardProps = {
  onDelete: (subject: SubjectDetail) => void
  onDocumentRemoved: (documentId: string) => void
  subject: SubjectDetail
}

function isBusy(document: SubjectDocument) {
  return document.status === 'PENDING' || document.status === 'PROCESSING'
}

function tooltipFor(document: SubjectDocument) {
  if (document.status === 'FAILED') return `${document.title} — falhou`
  if (isBusy(document)) return `${document.title} — processando`
  return document.page_count ? `${document.title} · ${document.page_count} pág.` : document.title
}

function SubjectTile({ document }: { document: SubjectDocument }) {
  const [imageFailed, setImageFailed] = useState(false)
  const source = document.icon_url ?? document.thumbnail_url

  return (
    <span className="subject-tile" data-status={document.status} data-tooltip={tooltipFor(document)}>
      {source && !imageFailed ? (
        <img
          alt=""
          className="subject-tile__img"
          loading="lazy"
          onError={() => setImageFailed(true)}
          src={source}
        />
      ) : (
        <Icon name="fileText" size={15} />
      )}
      {isBusy(document) ? <span className="subject-tile__busy" /> : null}
    </span>
  )
}

export const SubjectCard = memo(function SubjectCard({
  onDelete,
  onDocumentRemoved,
  subject,
}: SubjectCardProps) {
  const [isScreenOpen, setIsScreenOpen] = useState(false)
  const [removingId, setRemovingId] = useState<string | null>(null)
  const stripRef = useRef<HTMLDivElement>(null)

  const documents = subject.documents
  const visibleCount = useFittingCount(stripRef, {
    itemWidth: TILE_WIDTH,
    gap: TILE_GAP,
    total: documents.length,
  })
  const visible = documents.slice(0, visibleCount)
  const overflow = documents.length - visible.length

  async function handleRemoveDocument(documentId: string) {
    setRemovingId(documentId)
    try {
      await deleteSubjectDocument(documentId)
      onDocumentRemoved(documentId)
    } catch (error) {
      if (!(error instanceof ApiError)) throw error
    } finally {
      setRemovingId(null)
    }
  }

  return (
    <motion.div className="subject-card" layout transition={layoutTransition}>
      <div className="subject-card__head">
        <span aria-hidden="true" className="avatar lg blue">
          <Icon name="tag" size={18} />
        </span>
        <span className="subject-card__title" title={subject.name}>
          {subject.name}
        </span>
        <span className="subject-card__count">
          <Icon name="fileText" size={11} />
          {documents.length}
        </span>
      </div>

      <div className="subject-card__panel-inner">
        <div className="subject-card__section-label">Bibliografia</div>

        <div className="subject-strip" ref={stripRef}>
          {documents.length === 0 ? (
            <p className="subject-card__hint">
              Nenhum documento anexado. Os resumos guiados usam essa bibliografia.
            </p>
          ) : (
            <>
              {visible.map((document) => (
                <SubjectTile document={document} key={document.id} />
              ))}
              {overflow > 0 ? (
                <span className="subject-tile subject-tile--more">+{overflow}</span>
              ) : null}
            </>
          )}
        </div>

        <div className="subject-card__actions">
          <ExpandableScreenTrigger isOpen={isScreenOpen} layoutId={`subject-docs-${subject.id}`}>
            <button
              className="btn btn-primary btn-sm"
              onClick={() => setIsScreenOpen(true)}
              type="button"
            >
              <Icon name="layers" size={12} />
              <span>Documentos</span>
            </button>
          </ExpandableScreenTrigger>
          <button
            className="btn btn-ghost btn-sm danger"
            onClick={() => onDelete(subject)}
            type="button"
          >
            <Icon name="trash" size={12} />
            <span>Excluir</span>
          </button>
        </div>
      </div>

      <ExpandableScreen
        description={`Bibliografia de ${subject.name}. Os documentos alimentam os resumos guiados.`}
        isOpen={isScreenOpen}
        layoutId={`subject-docs-${subject.id}`}
        onClose={() => setIsScreenOpen(false)}
        title="Gerenciar documentos"
      >
        <SubjectDocumentsScreen
          documents={documents}
          isLoading={false}
          onRemove={(documentId) => void handleRemoveDocument(documentId)}
          removingId={removingId}
        />
      </ExpandableScreen>
    </motion.div>
  )
})
