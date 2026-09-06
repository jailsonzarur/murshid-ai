import { useEffect, useState } from 'react'
import { motion } from 'motion/react'

import { ApiError, deleteSubjectDocument, listSubjectDocuments } from '../../lib/api'
import { layoutTransition } from '../../lib/motion'
import type { Subject, SubjectDocument } from '../../types/lecture'
import { ExpandableScreen, ExpandableScreenTrigger } from '../ui/expandable-screen'
import { Icon } from '../ui/icon'
import { SubjectDocumentsScreen } from './SubjectDocumentsScreen'

type SubjectCardProps = {
  onDelete: () => void
  subject: Subject
}

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export function SubjectCard({ onDelete, subject }: SubjectCardProps) {
  const [documents, setDocuments] = useState<SubjectDocument[]>([])
  const [isLoadingDocuments, setIsLoadingDocuments] = useState(true)
  const [documentsError, setDocumentsError] = useState<string | undefined>()
  const [removingId, setRemovingId] = useState<string | null>(null)
  const [isScreenOpen, setIsScreenOpen] = useState(false)

  useEffect(() => {
    let active = true

    async function loadDocuments() {
      setIsLoadingDocuments(true)
      setDocumentsError(undefined)
      try {
        const data = await listSubjectDocuments(subject.id)
        if (active) setDocuments(data)
      } catch (error) {
        if (!active) return
        setDocuments([])
        if (error instanceof ApiError) setDocumentsError(error.message)
      } finally {
        if (active) setIsLoadingDocuments(false)
      }
    }

    void loadDocuments()
    return () => {
      active = false
    }
  }, [subject.id])

  async function handleRemoveDocument(documentId: string) {
    setRemovingId(documentId)
    try {
      await deleteSubjectDocument(documentId)
      setDocuments((prev) => prev.filter((document) => document.id !== documentId))
    } catch (error) {
      if (error instanceof ApiError) setDocumentsError(error.message)
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
        <span className="subject-card__title">{subject.name}</span>
        <span className="subject-card__count">
          <Icon name="fileText" size={11} />
          {documents.length}
        </span>
      </div>

      <div className="subject-card__panel-inner">
        <div className="subject-card__section-label">Bibliografia</div>

        {isLoadingDocuments ? (
          <p className="subject-card__hint">Buscando documentos...</p>
        ) : documents.length > 0 ? (
          <ul className="subject-card__docs">
            {documents.map((document) => (
              <li className="subject-card__doc" key={document.id}>
                <span aria-hidden="true" className="subject-card__doc-icon">
                  <Icon name="fileText" size={13} />
                </span>
                <span className="subject-card__doc-info">
                  <span className="subject-card__doc-name" title={document.original_name}>
                    {document.original_name}
                  </span>
                  <span className="subject-card__doc-size">{formatBytes(document.size_bytes)}</span>
                </span>
                <button
                  aria-label={`Remover ${document.original_name}`}
                  className="icon-btn danger"
                  disabled={removingId === document.id}
                  onClick={() => void handleRemoveDocument(document.id)}
                  type="button"
                >
                  <Icon name="trash" size={13} />
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <p className="subject-card__hint">
            Nenhum documento anexado. Os resumos guiados usam essa bibliografia.
          </p>
        )}

        {documentsError ? <p className="subject-card__error">{documentsError}</p> : null}

        <div className="subject-card__actions">
          <ExpandableScreenTrigger isOpen={isScreenOpen} layoutId={`subject-docs-${subject.id}`}>
            <button
              className="btn btn-primary btn-sm"
              onClick={() => setIsScreenOpen(true)}
              type="button"
            >
              <Icon name="layers" size={12} />
              <span>Gerenciar documentos</span>
            </button>
          </ExpandableScreenTrigger>
          <button className="btn btn-ghost btn-sm danger" onClick={onDelete} type="button">
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
          isLoading={isLoadingDocuments}
          onRemove={(documentId) => void handleRemoveDocument(documentId)}
          removingId={removingId}
        />
      </ExpandableScreen>
    </motion.div>
  )
}
