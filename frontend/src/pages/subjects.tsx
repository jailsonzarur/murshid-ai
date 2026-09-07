import { useCallback, useEffect, useState } from 'react'
import { AnimatePresence } from 'motion/react'

import { AppShell } from '../components/layout/app-shell'
import {
  NOVA_MATERIA_LAYOUT_ID,
  NovaMateriaModal,
} from '../components/subjects/NovaMateriaModal'
import { SubjectCard } from '../components/subjects/SubjectCard'
import {
  PaginationSkeleton,
  SubjectCardSkeleton,
} from '../components/subjects/SubjectCardSkeleton'
import { ExpandableScreenTrigger } from '../components/ui/expandable-screen'
import { EmptyState } from '../components/ui/empty-state'
import { Icon } from '../components/ui/icon'
import { Pagination } from '../components/ui/pagination'
import { getAccessToken } from '../lib/auth'
import { deleteSubject, listSubjects, pollSubjects } from '../lib/api'
import { navigateTo } from '../lib/navigation'
import type { PaginationMeta, SubjectDetail, SubjectDocument } from '../types/lecture'

const SKELETON_COUNT = 12

function isDocumentBusy(document: SubjectDocument) {
  return document.status === 'PENDING' || document.status === 'PROCESSING'
}

function statusSignature(subject: SubjectDetail) {
  return subject.documents.map((document) => `${document.id}:${document.status}`).join('|')
}

export function SubjectsPage() {
  const [subjects, setSubjects] = useState<SubjectDetail[]>([])
  const [meta, setMeta] = useState<PaginationMeta | null>(null)
  const [page, setPage] = useState(1)
  const [isLoading, setIsLoading] = useState(true)
  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [reloadToken, setReloadToken] = useState(0)


  useEffect(() => {
    if (!getAccessToken()) navigateTo('/login', { replace: true })
  }, [])

  useEffect(() => {
    if (!getAccessToken()) return
    let active = true

    async function loadSubjects() {
      setIsLoading(true)
      try {
        const data = await listSubjects(page)
        if (!active) return
        setSubjects(data.subjects)
        setMeta(data.meta)

        if (data.subjects.length === 0 && data.meta.total_pages > 0) {
          setPage(Math.min(page, data.meta.total_pages))
        }
      } catch {
        if (!active) return
        setSubjects([])
        setMeta(null)
      } finally {
        if (active) setIsLoading(false)
      }
    }

    void loadSubjects()
    return () => {
      active = false
    }
  }, [page, reloadToken])

  useEffect(() => {
    const pendingIds = subjects
      .filter((subject) => subject.documents.some(isDocumentBusy))
      .map((subject) => subject.id)

    if (pendingIds.length === 0) return

    const timer = setTimeout(async () => {
      let fresh: SubjectDetail[]
      try {
        fresh = await pollSubjects(pendingIds)
      } catch {
        return
      }

      setSubjects((prev) =>
        prev.map((subject) => {
          const updated = fresh.find((candidate) => candidate.id === subject.id)
          if (!updated) return subject
          return statusSignature(updated) === statusSignature(subject) ? subject : updated
        }),
      )
    }, 3000)

    return () => clearTimeout(timer)
  }, [subjects])

  const handleDelete = useCallback(async (subject: SubjectDetail) => {
    await deleteSubject(subject.id)
    setReloadToken((value) => value + 1)
  }, [])

  const handleDocumentRemoved = useCallback((documentId: string) => {
    setSubjects((prev) =>
      prev.map((subject) =>
        subject.documents.some((document) => document.id === documentId)
          ? { ...subject, documents: subject.documents.filter((d) => d.id !== documentId) }
          : subject,
      ),
    )
  }, [])

  return (
    <AppShell
      actions={
        <ExpandableScreenTrigger isOpen={isCreateOpen} layoutId={NOVA_MATERIA_LAYOUT_ID}>
          <button className="btn btn-primary" onClick={() => setIsCreateOpen(true)} type="button">
            <Icon name="plus" size={14} />
            <span>Nova matéria</span>
          </button>
        </ExpandableScreenTrigger>
      }
      activeItem="subjects"
      contentClassName="page--fixed"
      description="Cadastre as matérias que organizarão suas aulas e anexe a bibliografia de cada uma."
      title="Matérias"
    >

      <section aria-label="Lista de matérias" className="subjects-list">
        {!isLoading && subjects.length === 0 ? (
          <EmptyState
            description="Use o botão Nova matéria para cadastrar a primeira."
            title="Nenhuma matéria cadastrada."
          />
        ) : (
          <div className="subject-grid">
            <AnimatePresence mode="popLayout">
              {isLoading
                ? Array.from({ length: meta?.items_per_page ?? SKELETON_COUNT }, (_, index) => (
                    <SubjectCardSkeleton index={index} key={`skeleton-${index}`} />
                  ))
                : subjects.map((subject) => (
                    <SubjectCard
                      key={subject.id}
                      onDelete={handleDelete}
                      onDocumentRemoved={handleDocumentRemoved}
                      subject={subject}
                    />
                  ))}
            </AnimatePresence>
          </div>
        )}
      </section>

      {isLoading || (meta && meta.total_pages > 1) ? (
        <footer className="subjects-foot">
          {meta && !isLoading ? (
            <Pagination isBusy={isLoading} meta={meta} onPageChange={setPage} />
          ) : (
            <PaginationSkeleton />
          )}
        </footer>
      ) : null}


      <NovaMateriaModal
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
        onCreated={() => {
          setIsCreateOpen(false)
          setReloadToken((value) => value + 1)
        }}
      />
    </AppShell>
  )
}
