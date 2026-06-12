import { useEffect, useMemo, useState } from 'react'

import { AppShell } from '../components/layout/app-shell'
import { Badge } from '../components/ui/badge'
import { EmptyState } from '../components/ui/empty-state'
import { Icon } from '../components/ui/icon'
import { getAccessToken } from '../lib/auth'
import { listLectures } from '../lib/api'
import { navigateTo } from '../lib/navigation'
import type { LectureStatus, LectureSummary } from '../types/lecture'

type StatusFilter = 'ALL' | LectureStatus

const statusFilters: Array<{ label: string; value: StatusFilter }> = [
  { label: 'Todas', value: 'ALL' },
  { label: 'Em andamento', value: 'ACTIVE' },
  { label: 'Pausadas', value: 'PAUSED' },
  { label: 'Concluídas', value: 'COMPLETED' },
]

function formatDate(date: string) {
  return new Intl.DateTimeFormat('pt-BR').format(new Date(date))
}

function formatDuration(totalSeconds: number) {
  if (!totalSeconds || totalSeconds <= 0) return '—'
  const hours = Math.floor(totalSeconds / 3600)
  const minutes = Math.floor((totalSeconds % 3600) / 60)
  if (hours > 0) {
    return `${hours}h ${String(minutes).padStart(2, '0')}min`
  }
  const seconds = Math.floor(totalSeconds % 60)
  return `${minutes}min ${String(seconds).padStart(2, '0')}s`
}

function isInProgress(status: LectureStatus) {
  return status === 'ACTIVE' || status === 'PAUSED'
}

export function LecturesPage() {
  const [lectures, setLectures] = useState<LectureSummary[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('ALL')

  useEffect(() => {
    if (!getAccessToken()) {
      navigateTo('/login', { replace: true })
      return
    }
    async function loadLectures() {
      setIsLoading(true)
      try {
        const data = await listLectures()
        setLectures(data)
      } catch {
        setLectures([])
      } finally {
        setIsLoading(false)
      }
    }
    void loadLectures()
  }, [])

  const counts = useMemo(() => {
    const base: Record<StatusFilter, number> = {
      ALL: lectures.length,
      ACTIVE: 0,
      PAUSED: 0,
      COMPLETED: 0,
      FAILED: 0,
    }
    lectures.forEach((l) => {
      base[l.status] += 1
    })
    return base
  }, [lectures])

  const filteredLectures = useMemo(() => {
    return statusFilter === 'ALL'
      ? lectures
      : lectures.filter((l) => l.status === statusFilter)
  }, [lectures, statusFilter])

  function handleOpen(lecture: LectureSummary) {
    if (lecture.status === 'COMPLETED') {
      navigateTo(`/lectures/${lecture.id}`)
    }
  }

  return (
    <AppShell
      activeItem="lectures"
      actions={
        <button
          className="btn btn-primary"
          disabled
          style={{ opacity: 0.5, cursor: 'not-allowed' }}
          title="Disponível em breve"
          type="button"
        >
          <Icon name="video" size={14} />
          <span>Nova aula</span>
        </button>
      }
      description="Grave suas aulas ao vivo e deixe o Murshid transcrever, detectar tópicos e marcar o que cai na prova — em tempo real."
      title="Aulas transcritas"
    >
      <section aria-label="Banco de aulas">
        <div className="tabs" aria-label="Filtrar por status">
          {statusFilters.map((filter) => (
            <button
              className={filter.value === statusFilter ? 'tab active' : 'tab'}
              key={filter.value}
              onClick={() => setStatusFilter(filter.value)}
              type="button"
            >
              {filter.label}
              <span className="tab-count">{counts[filter.value]}</span>
            </button>
          ))}
        </div>

        {isLoading ? (
          <EmptyState
            description="Estamos buscando suas aulas e o status atual."
            title="Carregando aulas..."
          />
        ) : filteredLectures.length ? (
          <div className="prova-list">
            {filteredLectures.map((lecture) => {
              const live = isInProgress(lecture.status)
              return (
                <div className="prova-row" key={lecture.id}>
                  <div
                    aria-hidden="true"
                    className={`avatar ${live ? 'avatar-orange' : 'avatar-blue'}`}
                    style={{ width: 44, height: 44, borderRadius: 12, fontSize: 16, flexShrink: 0 }}
                  >
                    <Icon name={live ? 'video' : 'fileText'} size={20} />
                  </div>
                  <div style={{ minWidth: 0 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 2 }}>
                      <span style={{ fontSize: 11.5, color: 'var(--ink-4)', fontWeight: 500 }}>
                        {formatDate(lecture.created_at)}
                      </span>
                    </div>
                    <button
                      className="prova-title"
                      disabled={live}
                      onClick={() => handleOpen(lecture)}
                      style={{
                        background: 'none',
                        border: 'none',
                        cursor: live ? 'default' : 'pointer',
                        padding: 0,
                        font: 'inherit',
                        textAlign: 'left',
                        display: 'block',
                      }}
                      type="button"
                    >
                      {lecture.title ?? 'Aula sem título'}
                    </button>
                    <div className="prova-sub">
                      <span>
                        <Icon name="tag" size={11} />
                        {lecture.category?.name ?? 'Sem matéria'}
                      </span>
                      <span>
                        <Icon name="clock" size={11} />
                        {formatDuration(lecture.duration_seconds)}
                      </span>
                    </div>
                  </div>
                  <div>
                    <div className="cell-label">Tópicos</div>
                    <div className="cell-value mono">{lecture.topics_count}</div>
                  </div>
                  <div>
                    <div className="cell-label">Alertas</div>
                    <div className="cell-value mono">{lecture.alerts_count}</div>
                  </div>
                  <div>
                    <div className="cell-label">Status</div>
                    {live ? (
                      <Badge tone="destructive">
                        {lecture.status === 'PAUSED' ? 'Pausada' : 'Em andamento'}
                      </Badge>
                    ) : lecture.status === 'COMPLETED' ? (
                      <Badge tone="green">Concluída</Badge>
                    ) : (
                      <Badge tone="orange">Falhou</Badge>
                    )}
                  </div>
                  <div className="row-actions">
                    <button
                      aria-label={`Abrir aula ${lecture.title ?? 'sem título'}`}
                      className="icon-btn"
                      disabled={live}
                      onClick={() => handleOpen(lecture)}
                      title={live ? 'Disponível após finalizar' : 'Abrir aula'}
                      type="button"
                    >
                      <Icon name="eye" size={15} />
                    </button>
                  </div>
                </div>
              )
            })}
          </div>
        ) : (
          <EmptyState
            description="Crie sua primeira aula clicando no botão Nova aula (em breve)."
            title="Nenhuma aula transcrita ainda."
          />
        )}
      </section>
    </AppShell>
  )
}
