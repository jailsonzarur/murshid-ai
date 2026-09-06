import { useEffect, useState } from 'react'

import { AppShell } from '../components/layout/app-shell'
import { NovaMateriaModal } from '../components/subjects/NovaMateriaModal'
import { SubjectCard } from '../components/subjects/SubjectCard'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { EmptyState } from '../components/ui/empty-state'
import { Icon } from '../components/ui/icon'
import { getAccessToken } from '../lib/auth'
import { deleteSubject, listSubjects } from '../lib/api'
import { navigateTo } from '../lib/navigation'
import type { Subject } from '../types/lecture'

export function SubjectsPage() {
  const [subjects, setSubjects] = useState<Subject[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState<Subject | null>(null)
  const [isDeleting, setIsDeleting] = useState(false)

  useEffect(() => {
    if (!getAccessToken()) {
      navigateTo('/login', { replace: true })
      return
    }

    void loadSubjects()
  }, [])

  async function loadSubjects() {
    setIsLoading(true)
    try {
      const data = await listSubjects()
      setSubjects(data)
    } catch {
      setSubjects([])
    } finally {
      setIsLoading(false)
    }
  }

  async function handleConfirmDelete() {
    if (!confirmDelete) return
    setIsDeleting(true)
    try {
      await deleteSubject(confirmDelete.id)
      setConfirmDelete(null)
      await loadSubjects()
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
      description="Cadastre as matérias que organizarão suas aulas e anexe a bibliografia de cada uma."
      title="Matérias"
    >

      <section aria-label="Lista de matérias">
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
                onDelete={() => setConfirmDelete(subject)}
                subject={subject}
              />
            ))}
          </div>
        )}
      </section>

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
            void loadSubjects()
          }}
        />
      ) : null}
    </AppShell>
  )
}
