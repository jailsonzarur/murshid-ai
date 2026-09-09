import { useState, type FormEvent } from 'react'

import { ApiError, startLecture } from '../../lib/api'
import { navigateTo } from '../../lib/navigation'
import { fetchSubjectOptions } from '../../lib/subject-options'
import type { Subject } from '../../types/lecture'
import { Card, CardContent } from '../ui/card'
import { Icon } from '../ui/icon'
import { Input } from '../ui/input'
import { SearchableSelect } from '../ui/searchable-select'

type NovaAulaModalProps = {
  onClose: () => void
}

export function NovaAulaModal({ onClose }: NovaAulaModalProps) {
  const [title, setTitle] = useState('')
  const [subject, setSubject] = useState<Subject | null>(null)
  const [titleError, setTitleError] = useState<string | undefined>()
  const [subjectError, setSubjectError] = useState<string | undefined>()
  const [isSubmitting, setIsSubmitting] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const trimmedTitle = title.trim()
    const nextErrors: { title?: string; subject?: string } = {}

    if (!trimmedTitle) {
      nextErrors.title = 'Informe um nome para a aula.'
    }
    if (!subject) {
      nextErrors.subject = 'Selecione uma matéria.'
    }

    setTitleError(nextErrors.title)
    setSubjectError(nextErrors.subject)
    if (nextErrors.title || nextErrors.subject || !subject) return

    setIsSubmitting(true)
    try {
      const lecture = await startLecture({ title: trimmedTitle, subject_id: subject.id })
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
              <SearchableSelect
                emptyMessage="Nenhuma matéria encontrada."
                error={Boolean(subjectError)}
                fetchOptions={fetchSubjectOptions}
                label="Matéria"
                onChange={(option) => {
                  setSubject(option)
                  setSubjectError(undefined)
                }}
                placeholder="Selecione a matéria"
                value={subject}
              />
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
                disabled={isSubmitting}
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
