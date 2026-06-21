import { useEffect, useState } from 'react'
import ReactMarkdown from 'react-markdown'

import { SummaryModal } from '../components/lectures/SummaryModal'
import { TranscriptModal } from '../components/lectures/TranscriptModal'
import { TreeViewer } from '../components/lectures/TreeViewer'
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
  const [summaryOpen, setSummaryOpen] = useState(false)

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

    let cancelled = false
    let intervalId: number | undefined

    async function loadLecture(isFirst: boolean) {
      if (isFirst) setIsLoading(true)
      try {
        const data = await getLecture(lectureId)
        if (cancelled) return
        setLecture(data)
        // se a aula está completed mas summary ainda não foi gerada → continua polling
        const stillProcessing =
          data.status === 'PROCESSING' ||
          (data.status === 'COMPLETED' && data.summary === null && (data.nodes?.length ?? 0) === 0)
        if (!stillProcessing && intervalId !== undefined) {
          window.clearInterval(intervalId)
          intervalId = undefined
        }
        if (stillProcessing && intervalId === undefined) {
          intervalId = window.setInterval(() => {
            void loadLecture(false)
          }, 3000)
        }
      } catch {
        if (!cancelled) setLecture(null)
      } finally {
        if (isFirst && !cancelled) setIsLoading(false)
      }
    }

    void loadLecture(true)

    return () => {
      cancelled = true
      if (intervalId !== undefined) window.clearInterval(intervalId)
    }
  }, [])

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
        (() => {
          const isProcessing =
            lecture.status === 'PROCESSING' ||
            (lecture.status === 'COMPLETED' && lecture.summary === null && lecture.nodes.length === 0)
          return (
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
                      <strong style={{ marginRight: 4 }}>{lecture.nodes.length}</strong>tópicos
                    </span>
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Summary + Tree grid */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'minmax(0, 1fr) minmax(0, 1.2fr)',
              gap: 18,
              marginBottom: 18,
            }}
          >
            <Card style={{ height: 520, display: 'flex', flexDirection: 'column' }}>
              <CardHeader>
                <div>
                  <CardTitle>Resumo da aula</CardTitle>
                  <div className="card-sub">Gerado por IA a partir da transcrição</div>
                </div>
                <span className="tag accent">
                  <Icon name="sparkles" size={11} /> IA
                </span>
              </CardHeader>
              <CardContent
                style={{
                  flex: 1,
                  display: 'flex',
                  flexDirection: 'column',
                  padding: 0,
                  minHeight: 0,
                }}
              >
                {lecture.summary ? (
                  <>
                    <div
                      style={{
                        flex: 1,
                        position: 'relative',
                        overflow: 'hidden',
                        padding: '6px 22px 0',
                        minHeight: 0,
                      }}
                    >
                      <div
                        style={{
                          height: '100%',
                          overflow: 'hidden',
                          fontSize: 14,
                          lineHeight: 1.6,
                          color: 'var(--ink-2)',
                        }}
                      >
                        <ReactMarkdown>{lecture.summary}</ReactMarkdown>
                      </div>
                      <div
                        aria-hidden="true"
                        style={{
                          position: 'absolute',
                          left: 0,
                          right: 0,
                          bottom: 0,
                          height: 80,
                          background:
                            'linear-gradient(to bottom, transparent, var(--card-bg, #fff) 75%)',
                          pointerEvents: 'none',
                        }}
                      />
                    </div>
                    <div
                      style={{
                        padding: '12px 22px 18px',
                        borderTop: '1px solid var(--line)',
                        display: 'flex',
                        justifyContent: 'flex-end',
                      }}
                    >
                      <button
                        className="btn btn-ghost btn-sm"
                        onClick={() => setSummaryOpen(true)}
                        type="button"
                      >
                        <Icon name="fileText" size={12} />
                        <span>Ver resumo completo</span>
                      </button>
                    </div>
                  </>
                ) : isProcessing ? (
                  <ProcessingState label="Gerando resumo da aula..." />
                ) : (
                  <div style={{ padding: 22 }}>
                    <p style={{ fontSize: 13.5, color: 'var(--ink-4)' }}>
                      O resumo ainda está sendo gerado.
                    </p>
                  </div>
                )}
              </CardContent>
            </Card>

            <Card style={{ height: 520, display: 'flex', flexDirection: 'column' }}>
              <CardHeader>
                <div>
                  <CardTitle>Mapa de tópicos</CardTitle>
                  <div className="card-sub">Estrutura hierárquica da aula</div>
                </div>
              </CardHeader>
              <CardContent style={{ padding: 0, flex: 1, minHeight: 0 }}>
                {lecture.nodes.length > 0 ? (
                  <TreeViewer lectureNodes={lecture.nodes} />
                ) : isProcessing ? (
                  <ProcessingState label="Construindo mapa mental..." />
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
              lectureTitle={lecture.title}
              onClose={() => setTranscriptOpen(false)}
              segments={lecture.segments}
              subjectName={lecture.category?.name ?? null}
            />
          ) : null}

          {summaryOpen && lecture.summary ? (
            <SummaryModal
              lectureTitle={lecture.title}
              onClose={() => setSummaryOpen(false)}
              subjectName={lecture.category?.name ?? null}
              summary={lecture.summary}
            />
          ) : null}
        </>
          )
        })()
      )}
    </AppShell>
  )
}

function ProcessingState({ label }: { label: string }) {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 10,
        padding: '32px 20px',
        color: 'var(--ink-4)',
        textAlign: 'center',
        height: '100%',
      }}
    >
      <span
        aria-hidden="true"
        style={{
          width: 22,
          height: 22,
          borderRadius: '50%',
          border: '2.5px solid currentColor',
          borderTopColor: 'transparent',
          animation: 'lv-spin 0.9s linear infinite',
          display: 'inline-block',
        }}
      />
      <p style={{ margin: 0, fontSize: 13, fontWeight: 500 }}>{label}</p>
      <p style={{ margin: 0, fontSize: 12, opacity: 0.7 }}>
        Isso leva ~30 segundos. A página atualiza automaticamente.
      </p>
      <style>{`
        @keyframes lv-spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  )
}
