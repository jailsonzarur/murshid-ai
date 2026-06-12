import { useEffect, useMemo, useState } from 'react'
import ReactMarkdown from 'react-markdown'

import { Mindmap } from '../components/lectures/Mindmap'
import { TranscriptModal } from '../components/lectures/TranscriptModal'
import { AppShell } from '../components/layout/app-shell'
import { Button } from '../components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { EmptyState } from '../components/ui/empty-state'
import { Icon } from '../components/ui/icon'
import { getLecture } from '../lib/api'
import { getAccessToken } from '../lib/auth'
import { navigateTo } from '../lib/navigation'
import type { LectureDetail } from '../types/lecture'

function getLectureIdFromPath() {
  const [, resource, lectureId] = window.location.pathname.split('/')
  return resource === 'lectures' ? lectureId : ''
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

function ActionButton({
  disabled,
  icon,
  label,
  onClick,
  primary,
}: {
  disabled?: boolean
  icon: 'fileText' | 'bookOpen' | 'layers'
  label: string
  onClick?: () => void
  primary?: boolean
}) {
  return (
    <div style={{ position: 'relative' }} title={disabled ? 'Em breve' : undefined}>
      <button
        className={`btn ${primary ? 'btn-primary' : 'btn-ghost'}`}
        disabled={disabled}
        onClick={disabled ? undefined : onClick}
        style={disabled ? { opacity: 0.5, cursor: 'not-allowed' } : undefined}
        type="button"
      >
        <Icon name={icon} size={14} />
        <span>{label}</span>
      </button>
    </div>
  )
}

export function LectureViewerPage() {
  const [lecture, setLecture] = useState<LectureDetail | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [transcriptOpen, setTranscriptOpen] = useState(false)

  useEffect(() => {
    if (!getAccessToken()) {
      navigateTo('/login', { replace: true })
      return
    }
    const lectureId = getLectureIdFromPath()
    if (!lectureId) {
      navigateTo('/lectures', { replace: true })
      return
    }
    async function loadLecture() {
      setIsLoading(true)
      try {
        const data = await getLecture(lectureId)
        setLecture(data)
      } catch {
        setLecture(null)
      } finally {
        setIsLoading(false)
      }
    }
    void loadLecture()
  }, [])

  const counts = useMemo(() => {
    if (!lecture) return { topics: 0, alerts: 0 }
    return {
      topics: lecture.events.filter((e) => e.type === 'TOPIC').length,
      alerts: lecture.events.filter((e) => e.type === 'ALERT').length,
    }
  }, [lecture])

  return (
    <AppShell
      actions={
        <Button icon="arrowLeft" onClick={() => navigateTo('/lectures')} variant="outline">
          Voltar às aulas
        </Button>
      }
      activeItem="lectures"
      title="Resultado da aula"
    >
      {isLoading ? (
        <EmptyState description="Buscando a transcrição e o mapa mental." title="Carregando aula..." />
      ) : !lecture ? (
        <EmptyState
          description="A aula que você tentou abrir não existe ou foi removida."
          title="Aula não encontrada."
        />
      ) : (
        <>
          {/* Hero compact */}
          <div className="hero compact" style={{ marginBottom: 20 }}>
            <div className="hero-grain" />
            <span className="hero-orb h1" />
            <div className="hero-content">
              <div className="hero-left">
                <div className="hero-eyebrow">
                  <span className="eyebrow-dot" />
                  {lecture.category?.name ?? 'Sem matéria'}
                </div>
                <h2 className="hero-title">{lecture.title ?? 'Aula sem título'}</h2>
                <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginTop: 14 }}>
                  <span className="pill pill-mute">
                    <Icon name="clock" size={12} />
                    <span>
                      Duração <strong style={{ marginLeft: 4 }}>{formatDuration(lecture.duration_seconds)}</strong>
                    </span>
                  </span>
                  <span className="pill pill-accent">
                    <Icon name="listChecks" size={12} />
                    <span>
                      <strong style={{ marginRight: 4 }}>{counts.topics}</strong>tópicos
                    </span>
                  </span>
                  <span className="pill pill-warn">
                    <Icon name="alertTriangle" size={12} />
                    <span>
                      <strong style={{ marginRight: 4 }}>{counts.alerts}</strong>alertas
                    </span>
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Summary + Mindmap grid */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'minmax(0, 1fr) minmax(0, 1.2fr)',
              gap: 18,
              marginBottom: 18,
            }}
          >
            <Card>
              <CardHeader>
                <div>
                  <CardTitle>Resumo da aula</CardTitle>
                  <div className="card-sub">Gerado por IA a partir da transcrição</div>
                </div>
                <span className="tag accent">
                  <Icon name="sparkles" size={11} /> IA
                </span>
              </CardHeader>
              <CardContent>
                {lecture.summary ? (
                  <div style={{ fontSize: 14, lineHeight: 1.6, color: 'var(--ink-2)' }}>
                    <ReactMarkdown>{lecture.summary}</ReactMarkdown>
                  </div>
                ) : (
                  <p style={{ fontSize: 13.5, color: 'var(--ink-4)' }}>
                    O resumo ainda está sendo gerado em segundo plano.
                  </p>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <div>
                  <CardTitle>Mapa de tópicos</CardTitle>
                  <div className="card-sub">Estrutura hierárquica da aula</div>
                </div>
              </CardHeader>
              <CardContent style={{ padding: 0 }}>
                {lecture.mindmap_markdown ? (
                  <Mindmap markdown={lecture.mindmap_markdown} />
                ) : (
                  <div style={{ padding: 22 }}>
                    <p style={{ fontSize: 13.5, color: 'var(--ink-4)' }}>
                      O mapa mental ainda está sendo gerado.
                    </p>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Actions */}
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
            <ActionButton
              icon="fileText"
              label="Ver transcrição completa"
              onClick={() => setTranscriptOpen(true)}
              primary
            />
            <ActionButton disabled icon="bookOpen" label="Gerar flashcards" />
            <ActionButton disabled icon="layers" label="Gerar prova" />
          </div>

          {transcriptOpen ? (
            <TranscriptModal
              events={lecture.events}
              lectureTitle={lecture.title}
              onClose={() => setTranscriptOpen(false)}
              segments={lecture.segments}
              subjectName={lecture.category?.name ?? null}
            />
          ) : null}
        </>
      )}
    </AppShell>
  )
}
