import { useEffect, useMemo, useState, type FormEvent } from 'react'

import { AppShell } from '../components/layout/app-shell'
import { Badge, type BadgeTone } from '../components/ui/badge'
import { Button } from '../components/ui/button'
import { Card } from '../components/ui/card'
import { EmptyState } from '../components/ui/empty-state'
import { FileDropzone } from '../components/ui/file-dropzone'
import { Icon } from '../components/ui/icon'
import { Input } from '../components/ui/input'
import { getAccessToken } from '../lib/auth'
import { ApiError, deleteExam, getExams, uploadExam, type ExamListItem } from '../lib/api'
import { navigateTo } from '../lib/navigation'
import type { OrderedExamUploadFile } from '../types/exam-upload'

type StatusFilter = 'ALL' | ExamListItem['status']

const statusLabels: Record<ExamListItem['status'], string> = {
  PENDING: 'Pendente',
  PROCESSING: 'Processando',
  COMPLETED: 'Concluída',
  FAILED: 'Falhou',
}

const statusTones: Record<ExamListItem['status'], BadgeTone> = {
  PENDING: 'orange',
  PROCESSING: 'blue',
  COMPLETED: 'green',
  FAILED: 'neutral',
}

const statusFilters: Array<{ label: string; value: StatusFilter }> = [
  { label: 'Todas', value: 'ALL' },
  { label: 'Pendentes', value: 'PENDING' },
  { label: 'Processando', value: 'PROCESSING' },
  { label: 'Concluídas', value: 'COMPLETED' },
  { label: 'Falhas', value: 'FAILED' },
]

function getUploadValidationField(message: string) {
  const normalizedMessage = message.toLowerCase()

  if (
    normalizedMessage.includes('arquivo') ||
    normalizedMessage.includes('file') ||
    normalizedMessage.includes('mime') ||
    normalizedMessage.includes('pdf') ||
    normalizedMessage.includes('jpg') ||
    normalizedMessage.includes('png')
  ) {
    return 'files'
  }

  return 'name'
}

function formatDate(date: string) {
  return new Intl.DateTimeFormat('pt-BR').format(new Date(date))
}

function createInitialStatusCounts(): Record<StatusFilter, number> {
  return {
    ALL: 0,
    COMPLETED: 0,
    FAILED: 0,
    PENDING: 0,
    PROCESSING: 0,
  }
}

export function ExamsPage() {
  const [exams, setExams] = useState<ExamListItem[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [name, setName] = useState('')
  const [generalSubject, setGeneralSubject] = useState('')
  const [files, setFiles] = useState<OrderedExamUploadFile[]>([])
  const [formErrors, setFormErrors] = useState<{
    files?: string
    name?: string
  }>({})
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [examToDelete, setExamToDelete] = useState<ExamListItem | null>(null)
  const [isDeleting, setIsDeleting] = useState(false)
  const [query, setQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('ALL')

  useEffect(() => {
    if (!getAccessToken()) {
      navigateTo('/login', { replace: true })
      return
    }

    void loadExams()
  }, [])

  const statusCounts = useMemo(() => {
    const nextCounts = createInitialStatusCounts()

    exams.forEach((exam) => {
      nextCounts.ALL += 1
      nextCounts[exam.status] += 1
    })

    return nextCounts
  }, [exams])

  const filteredExams = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase()

    return exams.filter((exam) => {
      const matchesStatus = statusFilter === 'ALL' || exam.status === statusFilter
      const matchesQuery =
        !normalizedQuery ||
        exam.name.toLowerCase().includes(normalizedQuery) ||
        (exam.general_subject ?? '').toLowerCase().includes(normalizedQuery)

      return matchesStatus && matchesQuery
    })
  }, [exams, query, statusFilter])

  async function loadExams() {
    setIsLoading(true)

    try {
      const nextExams = await getExams()
      setExams(nextExams)
    } catch {
      setExams([])
    } finally {
      setIsLoading(false)
    }
  }

  function closeModal() {
    setIsModalOpen(false)
    setName('')
    setGeneralSubject('')
    setFiles([])
    setFormErrors({})
  }

  function closeDeleteModal() {
    if (isDeleting) {
      return
    }

    setExamToDelete(null)
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    const nextFormErrors = {
      name: !name.trim() ? 'Informe o nome da prova.' : undefined,
      files: !files.length ? 'Anexe pelo menos um arquivo.' : undefined,
    }

    if (nextFormErrors.name || nextFormErrors.files) {
      setFormErrors(nextFormErrors)
      return
    }

    setIsSubmitting(true)
    setFormErrors({})

    try {
      await uploadExam(name.trim(), generalSubject, files)
      closeModal()
      await loadExams()
    } catch (error) {
      if (error instanceof ApiError && error.kind === 'validation') {
        setFormErrors({ [getUploadValidationField(error.message)]: error.message })
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  async function handleDeleteExam() {
    if (!examToDelete) {
      return
    }

    setIsDeleting(true)

    try {
      await deleteExam(examToDelete.id)
      setExamToDelete(null)
      await loadExams()
    } catch {
      return
    } finally {
      setIsDeleting(false)
    }
  }

  function handleOpenExam(examId: string) {
    navigateTo(`/exams/${examId}`)
  }

  return (
    <AppShell
      actions={
        <Button icon="plus" onClick={() => setIsModalOpen(true)}>
          Gerar prova
        </Button>
      }
      activeItem="exams"
      description="Envie arquivos, monitore status e abra provas processadas."
      searchPlaceholder="Buscar provas..."
      title="Provas"
    >
      <section className="tasko-tasks-content" aria-label="Banco de provas">
        <div className="tasko-tasks-toolbar">
          <div className="tasko-tasks-search">
            <Input
              aria-label="Buscar prova"
              icon="search"
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Buscar por nome ou assunto"
              value={query}
            />
          </div>
          <div className="tasko-tasks-toolbar__actions">
            <Button icon="filter" variant="outline">
              Filter
            </Button>
            <Button icon="calendar" variant="outline">
              Date
            </Button>
          </div>
        </div>

        <div className="tasko-filter-buttons" aria-label="Filtrar por status">
          {statusFilters.map((filter) => (
            <button
              className={filter.value === statusFilter ? 'is-active' : undefined}
              key={filter.value}
              onClick={() => setStatusFilter(filter.value)}
              type="button"
            >
              {filter.label}
              <span>{statusCounts[filter.value]}</span>
            </button>
          ))}
        </div>

        <div className="tasko-task-list">
          {isLoading ? (
            <EmptyState
              description="Estamos buscando suas provas e status de processamento."
              title="Carregando provas..."
            />
          ) : filteredExams.length ? (
            filteredExams.map((exam) => (
              <Card className="tasko-task-card" key={exam.id}>
                <div className="tasko-task-card__check" aria-hidden="true">
                  <span />
                </div>
                <div className="tasko-task-card__content">
                  <div className="tasko-task-card__header">
                    <button
                      className="exam-title-button"
                      onClick={() => handleOpenExam(exam.id)}
                      type="button"
                    >
                      {exam.name}
                    </button>
                    <Badge tone={statusTones[exam.status]}>{statusLabels[exam.status]}</Badge>
                  </div>
                  <div className="tasko-task-card__meta">
                    <span>
                      <Icon name="tag" size={15} />
                      {exam.general_subject ?? 'Sem assunto'}
                    </span>
                    <span>
                      <Icon name="calendar" size={15} />
                      {formatDate(exam.created_at)}
                    </span>
                    <span>
                      <Icon name="fileText" size={15} />
                      {exam.documents_count} arquivos
                    </span>
                  </div>
                  <div className="tasko-task-card__footer">
                    <div className="tasko-task-card__tags">
                      <Badge tone="outline">OCR</Badge>
                      <Badge tone="outline">Prova</Badge>
                    </div>
                    <div className="exam-actions">
                      <a
                        aria-label={`Abrir prova ${exam.name}`}
                        className="exam-action-button exam-open-button"
                        href={`/exams/${exam.id}`}
                        onClick={(event) => {
                          if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
                            return
                          }

                          event.preventDefault()
                          handleOpenExam(exam.id)
                        }}
                        title="Abrir prova"
                      >
                        <Icon name="eye" size={16} />
                      </a>
                      <button
                        aria-label={`Excluir prova ${exam.name}`}
                        className="exam-action-button exam-delete-button"
                        onClick={() => setExamToDelete(exam)}
                        title="Excluir prova"
                        type="button"
                      >
                        <Icon name="trash" size={16} />
                      </button>
                    </div>
                  </div>
                </div>
              </Card>
            ))
          ) : (
            <EmptyState
              description="Quando houver provas cadastradas, elas aparecerão nesta lista."
              title="Nenhuma prova encontrada."
            />
          )}
        </div>
      </section>

      {isModalOpen ? (
        <div className="modal-backdrop" role="presentation">
          <Card className="exam-modal">
            <form onSubmit={handleSubmit}>
              <div className="exam-modal__heading">
                <div>
                  <Badge tone="green">Upload</Badge>
                  <h2>Gerar prova</h2>
                  <p>
                    Envie PDF, JPG ou PNG para iniciar o processamento. Para melhores resultados,
                    envie apenas uma prova por geração e mantenha as páginas na ordem correta.
                  </p>
                </div>
                <button aria-label="Fechar modal" onClick={closeModal} type="button">
                  <Icon name="x" size={16} />
                </button>
              </div>

              <div className="exam-modal__form">
                <Input
                  label="Nome"
                  error={formErrors.name}
                  onChange={(event) => {
                    setName(event.target.value)
                    setFormErrors((current) => ({ ...current, name: undefined }))
                  }}
                  placeholder="Ex: Prova de Clínica Médica"
                  value={name}
                />
                <Input
                  label="Assunto geral"
                  onChange={(event) => setGeneralSubject(event.target.value)}
                  placeholder="Ex: Cardiologia"
                  value={generalSubject}
                />
                <FileDropzone
                  error={formErrors.files}
                  files={files}
                  onFilesChange={(nextFiles) => {
                    setFiles(nextFiles)
                    setFormErrors((current) => ({ ...current, files: undefined }))
                  }}
                />
              </div>

              <div className="exam-modal__actions">
                <Button onClick={closeModal} type="button" variant="secondary">
                  Cancelar
                </Button>
                <Button disabled={isSubmitting} icon="upload" type="submit">
                  {isSubmitting ? 'Enviando...' : 'Confirmar'}
                </Button>
              </div>
            </form>
          </Card>
        </div>
      ) : null}

      {examToDelete ? (
        <div className="modal-backdrop" role="presentation">
          <Card className="exam-modal exam-delete-modal">
            <div className="exam-delete-modal__icon" aria-hidden="true">
              <Icon name="trash" size={24} />
            </div>
            <div className="exam-delete-modal__content">
              <h2>Excluir prova?</h2>
              <p>
                Tem certeza que deseja excluir <strong>{examToDelete.name}</strong>? Essa
                ação remove a prova e os arquivos associados.
              </p>
            </div>
            <div className="exam-modal__actions">
              <Button disabled={isDeleting} onClick={closeDeleteModal} type="button" variant="secondary">
                Cancelar
              </Button>
              <Button
                disabled={isDeleting}
                icon="trash"
                onClick={handleDeleteExam}
                style={{
                  background: '#b42318',
                  borderColor: 'rgba(180, 35, 24, 0.5)',
                  boxShadow: '0 16px 34px rgba(180, 35, 24, 0.18)',
                  color: '#fff',
                }}
                type="button"
              >
                {isDeleting ? 'Excluindo...' : 'Excluir'}
              </Button>
            </div>
          </Card>
        </div>
      ) : null}
    </AppShell>
  )
}
