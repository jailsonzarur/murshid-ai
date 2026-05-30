import { useEffect, useMemo, useState, type FormEvent } from 'react'

import { AppShell } from '../components/layout/app-shell'
import { Badge } from '../components/ui/badge'
import { Button } from '../components/ui/button'
import { Card } from '../components/ui/card'
import { EmptyState } from '../components/ui/empty-state'
import { FileDropzone } from '../components/ui/file-dropzone'
import { Icon } from '../components/ui/icon'
import { Input } from '../components/ui/input'
import { getAccessToken } from '../lib/auth'
import {
  ApiError,
  createExamResolution,
  deleteExam,
  getActiveExamResolution,
  getExamResolutions,
  getExams,
  uploadExam,
  type ExamListItem,
} from '../lib/api'
import { navigateTo } from '../lib/navigation'
import type { ResolutionMode, ResolutionSummary } from '../types/exam'
import type { OrderedExamUploadFile } from '../types/exam-upload'

type StatusFilter = 'ALL' | ExamListItem['status']

const statusLabels: Record<ExamListItem['status'], string> = {
  PENDING: 'Pendente',
  PROCESSING: 'Processando',
  COMPLETED: 'Concluída',
  FAILED: 'Falhou',
}

const statusFilters: Array<{ label: string; value: StatusFilter }> = [
  { label: 'Todas', value: 'ALL' },
  { label: 'Pendentes', value: 'PENDING' },
  { label: 'Processando', value: 'PROCESSING' },
  { label: 'Concluídas', value: 'COMPLETED' },
  { label: 'Falhas', value: 'FAILED' },
]

const resolutionModeLabels: Record<ResolutionMode, string> = {
  EXAM: 'Modo exame',
  STUDY: 'Modo estudo',
}

const resolutionStatusLabels: Record<ResolutionSummary['status'], string> = {
  ERROR: 'Erro',
  GRADED: 'Corrigida',
  IN_PROGRESS: 'Em andamento',
  PAUSED: 'Pausada',
  SUBMITTED: 'Enviada',
}

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
  const [examToStart, setExamToStart] = useState<ExamListItem | null>(null)
  const [historyExam, setHistoryExam] = useState<ExamListItem | null>(null)
  const [resolutionHistory, setResolutionHistory] = useState<ResolutionSummary[]>([])
  const [isCheckingResolution, setIsCheckingResolution] = useState(false)
  const [isStartingResolution, setIsStartingResolution] = useState(false)
  const [isLoadingHistory, setIsLoadingHistory] = useState(false)
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

  async function handleOpenExam(exam: ExamListItem) {
    if (exam.status !== 'COMPLETED') {
      navigateTo(`/exams/${exam.id}`)
      return
    }

    setIsCheckingResolution(true)

    try {
      const activeResolution = await getActiveExamResolution(exam.id)

      if (activeResolution) {
        navigateTo(`/resolutions/${activeResolution.id}`)
        return
      }

      setExamToStart(exam)
    } finally {
      setIsCheckingResolution(false)
    }
  }

  async function handleStartResolution(mode: ResolutionMode) {
    if (!examToStart) {
      return
    }

    setIsStartingResolution(true)

    try {
      const resolution = await createExamResolution(examToStart.id, mode)
      setExamToStart(null)
      navigateTo(`/resolutions/${resolution.id}`)
    } finally {
      setIsStartingResolution(false)
    }
  }

  async function handleOpenHistory(exam: ExamListItem) {
    setHistoryExam(exam)
    setResolutionHistory([])
    setIsLoadingHistory(true)

    try {
      const resolutions = await getExamResolutions(exam.id)
      setResolutionHistory(resolutions)
    } finally {
      setIsLoadingHistory(false)
    }
  }

  const avatarColors = ['purple', 'blue', 'orange', 'pink', 'yellow'] as const

  return (
    <AppShell
      activeItem="exams"
      searchPlaceholder="Buscar por nome, disciplina ou assunto..."
    >
      {/* Compact hero */}
      <div className="hero compact">
        <div className="hero-grain" />
        <span className="hero-orb h1" />
        <div className="hero-content">
          <div className="hero-left">
            <div className="hero-eyebrow">
              <span className="eyebrow-dot" />
              Biblioteca · {statusCounts.ALL} provas
            </div>
            <h1 className="hero-title">Provas</h1>
            <p className="hero-sub">
              Envie materiais, monitore o processamento e abra suas provas.
              Cada uma é uma sessão revisável com flashcards e estatísticas vinculadas.
            </p>
          </div>
          <div className="hero-actions">
            <button className="btn btn-glass" onClick={() => setIsModalOpen(true)} type="button">
              <Icon name="upload" size={14} />
              <span>Importar arquivo</span>
            </button>
            <button className="btn btn-light" onClick={() => setIsModalOpen(true)} type="button">
              <Icon name="plus" size={14} />
              <span>Gerar prova</span>
            </button>
          </div>
        </div>
      </div>

      <section aria-label="Banco de provas">
        <div className="toolbar">
          <div className="search-inline" style={{ flex: 1, maxWidth: 480 }}>
            <Icon name="search" size={16} style={{ color: 'var(--ink-4)', flexShrink: 0 }} />
            <input
              aria-label="Buscar prova"
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Buscar por nome ou assunto..."
              style={{ flex: 1, border: 0, outline: 'none', background: 'transparent', fontSize: 13.5 }}
              value={query}
            />
            <kbd className="kbd">⌘ F</kbd>
          </div>
          <button className="btn btn-ghost" type="button">
            <Icon name="filter" size={14} />
            <span>Filtros</span>
          </button>
          <button className="btn btn-ghost" type="button">
            <Icon name="calendar" size={14} />
            <span>Data</span>
          </button>
        </div>

        <div className="tabs" aria-label="Filtrar por status">
          {statusFilters.map((filter) => (
            <button
              className={filter.value === statusFilter ? 'tab active' : 'tab'}
              key={filter.value}
              onClick={() => setStatusFilter(filter.value)}
              type="button"
            >
              {filter.label}
              <span className="tab-count">{statusCounts[filter.value]}</span>
            </button>
          ))}
          <div style={{ flex: 1 }} />
          <button className="chip-select" type="button">
            <span>Mais recentes</span>
            <Icon name="chevronDown" size={11} />
          </button>
        </div>

        {isLoading ? (
          <EmptyState
            description="Estamos buscando suas provas e status de processamento."
            title="Carregando provas..."
          />
        ) : filteredExams.length ? (
          <div className="prova-list">
            {filteredExams.map((exam, index) => {
              const color = avatarColors[index % avatarColors.length]
              const initial = exam.name.trim().charAt(0).toUpperCase()
              return (
                <div className="prova-row" key={exam.id}>
                  <div
                    className="check"
                    aria-label="Selecionar prova"
                    role="checkbox"
                    aria-checked="false"
                    tabIndex={0}
                  >
                    <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 6 9 17l-5-5" /></svg>
                  </div>
                  <div
                    className={`avatar ${color}`}
                    style={{ width: 44, height: 44, borderRadius: 12, fontSize: 16, flexShrink: 0 }}
                    aria-hidden="true"
                  >
                    {initial}
                  </div>
                  <div style={{ minWidth: 0 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 2 }}>
                      <span className="prova-num">PROVA-{String(index + 1).padStart(3, '0')}</span>
                      <span style={{ fontSize: 10, color: 'var(--ink-5)' }}>·</span>
                      <span style={{ fontSize: 11.5, color: 'var(--ink-4)', fontWeight: 500 }}>
                        {formatDate(exam.created_at)}
                      </span>
                    </div>
                    <button
                      className="prova-title"
                      onClick={() => handleOpenExam(exam)}
                      style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0, font: 'inherit', textAlign: 'left', display: 'block' }}
                      type="button"
                    >
                      {exam.name}
                    </button>
                    <div className="prova-sub">
                      <span>
                        <Icon name="tag" size={11} />
                        {exam.general_subject ?? 'Sem assunto'}
                      </span>
                      <span>
                        <Icon name="fileText" size={11} />
                        {exam.documents_count} {exam.documents_count === 1 ? 'arquivo' : 'arquivos'}
                      </span>
                    </div>
                  </div>
                  <div>
                    <div className="cell-label">Data</div>
                    <div className="cell-value">{formatDate(exam.created_at)}</div>
                  </div>
                  <div>
                    <div className="cell-label">Arquivos</div>
                    <div className="cell-value mono">{exam.documents_count}</div>
                  </div>
                  <div>
                    <div className="cell-label">Status</div>
                    <span className={`pill ${exam.status === 'COMPLETED' ? 'pill-ok' : exam.status === 'PROCESSING' ? 'pill-warn' : exam.status === 'FAILED' ? 'pill-danger' : 'pill-mute'}`}>
                      {statusLabels[exam.status]}
                    </span>
                  </div>
                  <div className="row-actions">
                    <a
                      aria-label={`Abrir prova ${exam.name}`}
                      className="icon-btn"
                      href={exam.status === 'COMPLETED' ? '#' : `/exams/${exam.id}`}
                      onClick={(event) => {
                        if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return
                        event.preventDefault()
                        void handleOpenExam(exam)
                      }}
                      title="Abrir prova"
                    >
                      <Icon name="eye" size={15} />
                    </a>
                    <button
                      aria-label={`Histórico de resoluções de ${exam.name}`}
                      className="icon-btn"
                      disabled={exam.status !== 'COMPLETED'}
                      onClick={() => handleOpenHistory(exam)}
                      title="Histórico de resoluções"
                      type="button"
                    >
                      <Icon name="listChecks" size={15} />
                    </button>
                    <button
                      aria-label={`Excluir prova ${exam.name}`}
                      className="icon-btn danger"
                      onClick={() => setExamToDelete(exam)}
                      title="Excluir prova"
                      type="button"
                    >
                      <Icon name="trash" size={15} />
                    </button>
                  </div>
                </div>
              )
            })}
          </div>
        ) : (
          <EmptyState
            description="Quando houver provas cadastradas, elas aparecerão nesta lista."
            title="Nenhuma prova encontrada."
          />
        )}

        {filteredExams.length > 0 ? (
          <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 14, fontSize: 12, color: 'var(--ink-4)', fontWeight: 500 }}>
            <span>Mostrando {filteredExams.length} de {exams.length} provas</span>
            <span>Atualizado agora</span>
          </div>
        ) : null}
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

      {examToStart ? (
        <div className="modal-backdrop" role="presentation">
          <Card className="exam-modal resolution-mode-modal">
            <div className="exam-modal__heading">
              <div>
                <Badge tone="blue">Resolução</Badge>
                <h2>Como deseja resolver?</h2>
                <p>
                  Escolha o modo para iniciar <strong>{examToStart.name}</strong>. No modo exame,
                  a correção aparece apenas ao finalizar. No modo estudo, as respostas poderão ser
                  corrigidas durante a resolução quando a correção estiver ativa.
                </p>
              </div>
              <button
                aria-label="Fechar modal"
                disabled={isStartingResolution}
                onClick={() => setExamToStart(null)}
                type="button"
              >
                <Icon name="x" size={16} />
              </button>
            </div>
            <div className="resolution-mode-options">
              <button
                disabled={isStartingResolution}
                onClick={() => handleStartResolution('EXAM')}
                type="button"
              >
                <Icon name="clock" size={20} />
                <span>
                  <strong>Modo exame</strong>
                  <small>Cronômetro ativo e feedback somente após finalizar.</small>
                </span>
              </button>
              <button
                disabled={isStartingResolution}
                onClick={() => handleStartResolution('STUDY')}
                type="button"
              >
                <Icon name="sparkles" size={20} />
                <span>
                  <strong>Modo estudo</strong>
                  <small>Fluxo preparado para feedback questão a questão.</small>
                </span>
              </button>
            </div>
          </Card>
        </div>
      ) : null}

      {historyExam ? (
        <div className="modal-backdrop" role="presentation">
          <Card className="exam-modal resolution-history-modal">
            <div className="exam-modal__heading">
              <div>
                <Badge tone="green">Histórico</Badge>
                <h2>Resoluções</h2>
                <p>{historyExam.name}</p>
              </div>
              <button aria-label="Fechar modal" onClick={() => setHistoryExam(null)} type="button">
                <Icon name="x" size={16} />
              </button>
            </div>

            <div className="resolution-history-list">
              {isLoadingHistory ? (
                <p className="resolution-history-empty">Carregando resoluções...</p>
              ) : resolutionHistory.length ? (
                resolutionHistory.map((resolution) => (
                  <button
                    className="resolution-history-item"
                    key={resolution.id}
                    onClick={() => navigateTo(`/resolutions/${resolution.id}`)}
                    type="button"
                  >
                    <span>
                      <strong>{resolutionModeLabels[resolution.mode]}</strong>
                      <small>{formatDate(resolution.created_at)}</small>
                    </span>
                    <span>
                      <Badge tone="outline">{resolutionStatusLabels[resolution.status]}</Badge>
                      {resolution.score === null || resolution.score === undefined ? null : (
                        <strong>{Math.round(resolution.score * 100)}%</strong>
                      )}
                    </span>
                  </button>
                ))
              ) : (
                <EmptyState
                  className="empty-state--compact"
                  description="Quando uma tentativa for iniciada, ela aparecerá neste histórico."
                  title="Nenhuma resolução encontrada."
                />
              )}
            </div>
          </Card>
        </div>
      ) : null}

      {isCheckingResolution ? (
        <div className="modal-backdrop modal-backdrop--transparent" role="presentation">
          <Card className="exam-modal resolution-checking-modal">
            <Icon name="clock" size={20} />
            <p>Verificando resolução em andamento...</p>
          </Card>
        </div>
      ) : null}
    </AppShell>
  )
}
