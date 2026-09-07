import { useEffect, useState, type FormEvent } from 'react'

import { ApiError, listSubjectOptions, startLecture } from '../../lib/api'
import { navigateTo } from '../../lib/navigation'
import type { Subject } from '../../types/lecture'
import { Card, CardContent } from '../ui/card'
import { Icon } from '../ui/icon'
import { Input } from '../ui/input'

type NovaAulaModalProps = {
  onClose: () => void
}

export function NovaAulaModal({ onClose }: NovaAulaModalProps) {
  const [subjects, setSubjects] = useState<Subject[]>([])
  const [isLoadingSubjects, setIsLoadingSubjects] = useState(true)
  const [title, setTitle] = useState('')
  const [subjectId, setSubjectId] = useState<string | null>(null)
  const [titleError, setTitleError] = useState<string | undefined>()
  const [subjectError, setSubjectError] = useState<string | undefined>()
  const [isSubmitting, setIsSubmitting] = useState(false)

  useEffect(() => {
    async function load() {
      try {
        const data = await listSubjectOptions()
        setSubjects(data)
      } catch {
        setSubjects([])
      } finally {
        setIsLoadingSubjects(false)
      }
    }
    void load()
  }, [])

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const trimmedTitle = title.trim()
    const nextErrors: { title?: string; subject?: string } = {}

    if (!trimmedTitle) {
      nextErrors.title = 'Informe um nome para a aula.'
    }
    if (!subjectId) {
      nextErrors.subject = 'Selecione uma matéria.'
    }

    setTitleError(nextErrors.title)
    setSubjectError(nextErrors.subject)
    if (nextErrors.title || nextErrors.subject) return

    setIsSubmitting(true)
    try {
      const lecture = await startLecture({ title: trimmedTitle, subject_id: subjectId })
      navigateTo(`/lectures/${lecture.id}/record`)
    } catch (error) {
      if (error instanceof ApiError && error.kind === 'validation') {
        setTitleError(error.message)
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="modal-backdrop" role="presentation">
      <Card style={{ maxWidth: 520, width: '100%' }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'flex-start',
            justifyContent: 'space-between',
            gap: 12,
            padding: '20px 22px 8px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div
              aria-hidden="true"
              className="avatar avatar-blue"
              style={{ width: 40, height: 40, borderRadius: 10 }}
            >
              <Icon name="video" size={18} />
            </div>
            <div>
              <h2 style={{ margin: 0, fontSize: 16, fontWeight: 700 }}>Nova aula</h2>
              <p style={{ margin: '4px 0 0', fontSize: 12.5, color: 'var(--ink-4)' }}>
                Dê um nome e selecione a matéria. A gravação começa em seguida.
              </p>
            </div>
          </div>
          <button aria-label="Fechar modal" className="icon-btn" onClick={onClose} type="button">
            <Icon name="x" size={16} />
          </button>
        </div>

        <CardContent>
          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <Input
              autoFocus
              error={titleError}
              icon="fileText"
              label="Nome da aula"
              onChange={(event) => {
                setTitle(event.target.value)
                setTitleError(undefined)
              }}
              placeholder="Ex.: Aula 03 — Derivadas"
              value={title}
            />

            <div>
              <span
                style={{
                  display: 'block',
                  fontSize: 12.5,
                  fontWeight: 600,
                  color: 'var(--ink-2)',
                  marginBottom: 6,
                }}
              >
                Matéria
              </span>
              {isLoadingSubjects ? (
                <p style={{ fontSize: 13, color: 'var(--ink-4)' }}>Buscando matérias...</p>
              ) : subjects.length === 0 ? (
                <p style={{ fontSize: 13, color: 'var(--ink-4)' }}>
                  Nenhuma matéria cadastrada. Crie uma em <strong>Matérias</strong> antes de iniciar.
                </p>
              ) : (
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                  {subjects.map((subject) => {
                    const selected = subject.id === subjectId
                    return (
                      <button
                        className={selected ? 'tab active' : 'tab'}
                        key={subject.id}
                        onClick={() => {
                          setSubjectId(subject.id)
                          setSubjectError(undefined)
                        }}
                        style={{ flexShrink: 0 }}
                        type="button"
                      >
                        {subject.name}
                      </button>
                    )
                  })}
                </div>
              )}
              {subjectError ? (
                <span style={{ display: 'block', marginTop: 6, fontSize: 12, color: 'var(--danger)' }}>
                  {subjectError}
                </span>
              ) : null}
            </div>

            <div
              style={{
                display: 'flex',
                justifyContent: 'flex-end',
                gap: 8,
                paddingTop: 8,
                borderTop: '1px solid var(--line)',
              }}
            >
              <button className="btn btn-ghost" disabled={isSubmitting} onClick={onClose} type="button">
                Cancelar
              </button>
              <button
                className="btn btn-primary"
                disabled={isSubmitting || isLoadingSubjects || subjects.length === 0}
                type="submit"
              >
                <Icon name="video" size={14} />
                <span>{isSubmitting ? 'Criando...' : 'Criar e iniciar gravação'}</span>
              </button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
