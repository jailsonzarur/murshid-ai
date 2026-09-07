import { useCallback, useEffect, useState } from 'react'

import { AppShell } from '../components/layout/app-shell'
import { NovaMateriaModal } from '../components/subjects/NovaMateriaModal'
import { SubjectCard } from '../components/subjects/SubjectCard'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { EmptyState } from '../components/ui/empty-state'
import { Icon } from '../components/ui/icon'
import { Pagination } from '../components/ui/pagination'
import { getAccessToken } from '../lib/auth'
import { deleteSubject, listSubjects, pollSubjects } from '../lib/api'
import { navigateTo } from '../lib/navigation'
import type { PaginationMeta, Subject, SubjectDetail, SubjectDocument } from '../types/lecture'

function isDocumentBusy(document: SubjectDocument) {
  return document.status === 'PENDING' || document.status === 'PROCESSING'
}

/** Ignora as URLs assinadas, que mudam a cada poll; só a transição de estado importa. */
function statusSignature(subject: SubjectDetail) {
  return subject.documents.map((document) => `${document.id}:${document.status}`).join('|')
}

export function SubjectsPage() {
  const [subjects, setSubjects] = useState<SubjectDetail[]>([])
  const [meta, setMeta] = useState<PaginationMeta | null>(null)
  const [page, setPage] = useState(1)
  const [isLoading, setIsLoading] = useState(true)
  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState<Subject | null>(null)
  const [isDeleting, setIsDeleting] = useState(false)
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

        // apagar o último item de uma página deixa ela vazia; recua
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

  // só as matérias com documento pendente entram no poll, e só os cards
  // delas trocam de identidade — o resto do grid não re-renderiza
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

  const handleDelete = useCallback((subject: SubjectDetail) => setConfirmDelete(subject), [])

  const handleDocumentRemoved = useCallback((documentId: string) => {
    setSubjects((prev) =>
      prev.map((subject) =>
        subject.documents.some((document) => document.id === documentId)
          ? { ...subject, documents: subject.documents.filter((d) => d.id !== documentId) }
          : subject,
      ),
    )
  }, [])


  async function handleConfirmDelete() {
    if (!confirmDelete) return
    setIsDeleting(true)
    try {
      await deleteSubject(confirmDelete.id)
      setConfirmDelete(null)
      setReloadToken((value) => value + 1)
    } catch {
      return
    } finally {
      setIsDeleting(false)
    }
  }

  return (
    <AppShell
      actions={
        <button className="btn btn-primary" onClick={() => setIsCreateOpen(true)} type="button">
          <Icon name="plus" size={14} />
          <span>Nova matéria</span>
        </button>
      }
      activeItem="subjects"
      contentClassName="page--fixed"
      description="Cadastre as matérias que organizarão suas aulas e anexe a bibliografia de cada uma."
      title="Matérias"
    >

      <section aria-label="Lista de matérias" className="subjects-list">
        {isLoading ? (
          <EmptyState description="Buscando matérias cadastradas." title="Carregando..." />
        ) : subjects.length === 0 ? (
          <EmptyState
            description="Use o botão Nova matéria para cadastrar a primeira."
            title="Nenhuma matéria cadastrada."
          />
        ) : (
          <div className="subject-grid">
            {subjects.map((subject) => (
              <SubjectCard
                key={subject.id}
                onDelete={handleDelete}
                onDocumentRemoved={handleDocumentRemoved}
                subject={subject}
              />
            ))}
          </div>
        )}
      </section>

      {meta && meta.total_pages > 1 ? (
        <footer className="subjects-foot">
          <Pagination isBusy={isLoading} meta={meta} onPageChange={setPage} />
        </footer>
      ) : null}

      {confirmDelete ? (
        <div className="modal-backdrop" role="presentation">
          <Card style={{ maxWidth: 440, width: '100%' }}>
            <CardHeader>
              <CardTitle>Excluir matéria</CardTitle>
            </CardHeader>
            <CardContent>
              <p style={{ fontSize: 14, color: 'var(--ink-2)', lineHeight: 1.5 }}>
                Tem certeza que deseja excluir <strong>{confirmDelete.name}</strong>? Aulas
                vinculadas a essa matéria continuarão existindo, mas perderão o vínculo.
              </p>
              <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 18 }}>
                <button
                  className="btn btn-ghost"
                  disabled={isDeleting}
                  onClick={() => setConfirmDelete(null)}
                  type="button"
                >
                  Cancelar
                </button>
                <button
                  className="btn btn-danger"
                  disabled={isDeleting}
                  onClick={handleConfirmDelete}
                  type="button"
                >
                  <Icon name="trash" size={14} />
                  <span>{isDeleting ? 'Excluindo...' : 'Excluir'}</span>
                </button>
              </div>
            </CardContent>
          </Card>
        </div>
      ) : null}

      {isCreateOpen ? (
        <NovaMateriaModal
          onClose={() => setIsCreateOpen(false)}
          onCreated={() => {
            setIsCreateOpen(false)
            setReloadToken((value) => value + 1)
          }}
        />
      ) : null}
    </AppShell>
  )
}
