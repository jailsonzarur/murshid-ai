import { useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'

import { GuidedSummary } from '../components/lectures/GuidedSummary'
import { SubjectPicker } from '../components/lectures/SubjectPicker'
import { SummaryModal } from '../components/lectures/SummaryModal'
import { SummaryPdfButton } from '../components/lectures/SummaryPdfButton'
import { TranscriptModal } from '../components/lectures/TranscriptModal'
import { TreeViewer } from '../components/lectures/TreeViewer'
import { AppShell } from '../components/layout/app-shell'
import { Button } from '../components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { EmptyState } from '../components/ui/empty-state'
import { Icon } from '../components/ui/icon'
import {
  ApiError,
  generateLectureGuidedSummary,
  generateLectureMindmap,
  getLecture,
  listLectureGuidedCitations,
  updateLectureSubject,
} from '../lib/api'
import { getAccessToken } from '../lib/auth'
import { navigateTo } from '../lib/navigation'
import type { GuidedCitation, LectureDetail, Subject } from '../types/lecture'

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
  title,
}: {
  disabled?: boolean
  icon: 'fileText' | 'bookOpen' | 'layers' | 'sparkles'
  label: string
  onClick?: () => void
  primary?: boolean
  title?: string
}) {
  return (
    <div style={{ position: 'relative' }} title={title}>
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
  const [mindmapError, setMindmapError] = useState<string | undefined>()
  const [pickerOpen, setPickerOpen] = useState(false)
  const [isSavingSubject, setIsSavingSubject] = useState(false)
  const subjectButtonRef = useRef<HTMLButtonElement>(null)
  const [guidedError, setGuidedError] = useState<string | undefined>()
  const [citations, setCitations] = useState<GuidedCitation[]>([])

  const isBuildingGuided =
    lecture?.guided_status === 'REQUESTED' || lecture?.guided_status === 'PROCESSING'

  async function handleGenerateGuided() {
    const lectureId = getLectureIdFromPath()
    if (!lectureId) return

    setGuidedError(undefined)
    setLecture((current) => (current ? { ...current, guided_status: 'REQUESTED' } : current))
    try {
      await generateLectureGuidedSummary(lectureId)
    } catch (error) {
      setLecture((current) => (current ? { ...current, guided_status: 'NONE' } : current))
      setGuidedError(
        error instanceof ApiError ? error.message : 'Não foi possível gerar o resumo guiado.',
      )
    }
  }

  async function handleChangeSubject(subject: Subject | null) {
    const lectureId = getLectureIdFromPath()
    if (!lectureId) return

    setIsSavingSubject(true)
    try {
      setLecture(await updateLectureSubject(lectureId, subject?.id ?? null))
      setPickerOpen(false)
    } catch {
      // o toast global ja reporta
    } finally {
      setIsSavingSubject(false)
    }
  }

  const isBuildingMindmap = lecture?.mindmap_status === 'REQUESTED'

  async function handleGenerateMindmap() {
    const lectureId = getLectureIdFromPath()
    if (!lectureId) return

    setMindmapError(undefined)
    setLecture((current) =>
      current ? { ...current, mindmap_status: 'REQUESTED' } : current,
    )
    try {
      await generateLectureMindmap(lectureId)
    } catch (error) {
      setLecture((current) => (current ? { ...current, mindmap_status: 'NONE' } : current))
      setMindmapError(
        error instanceof ApiError ? error.message : 'Não foi possível gerar o mapa mental.',
      )
    }
  }

  useEffect(() => {
    if (!isBuildingGuided) return

    const lectureId = getLectureIdFromPath()
    if (!lectureId) return

    const intervalId = window.setInterval(() => {
      void getLecture(lectureId)
        .then((data) => {
          if (data.guided_status === 'REQUESTED' || data.guided_status === 'PROCESSING') return
          setLecture(data)
          if (data.guided_status === 'FAILED') {
            setGuidedError('Não foi possível gerar o resumo guiado. Tente novamente.')
          }
        })
        .catch(() => undefined)
    }, 3000)

    return () => window.clearInterval(intervalId)
  }, [isBuildingGuided])

  useEffect(() => {
    if (!lecture?.guided_summary) return

    const lectureId = getLectureIdFromPath()
    if (!lectureId) return

    void listLectureGuidedCitations(lectureId)
      .then(setCitations)
      .catch(() => undefined)
  }, [lecture?.guided_summary])

  useEffect(() => {
    if (!isBuildingMindmap) return

    const lectureId = getLectureIdFromPath()
    if (!lectureId) return

    const intervalId = window.setInterval(() => {
      void getLecture(lectureId)
        .then((data) => {
          if (data.mindmap_status === 'REQUESTED') return
          setLecture(data)
          if (data.mindmap_status === 'FAILED') {
            setMindmapError('Não foi possível gerar o mapa mental. Tente novamente.')
          }
        })
        .catch(() => undefined)
    }, 3000)

    return () => window.clearInterval(intervalId)
  }, [isBuildingMindmap])

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
          const showTree = lecture.nodes.length > 0 || isProcessing || isBuildingMindmap
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
                  {lecture.subject?.name ?? 'Sem matéria'}
                </div>
                <h2 className="hero-title">{lecture.title ?? 'Aula sem título'}</h2>
                <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginTop: 14 }}>
                  <span className="pill pill-mute">
                    <Icon name="clock" size={12} />
                    <span>
                      Duração <strong style={{ marginLeft: 4 }}>{formatDuration(lecture.duration_seconds)}</strong>
                    </span>
                  </span>
                  <button
                    aria-label="Trocar matéria"
                    className="pill pill-mute subject-pill__button"
                    onClick={() => setPickerOpen((open) => !open)}
                    ref={subjectButtonRef}
                    type="button"
                  >
                    <Icon name="pencil" size={12} />
                    <span>{lecture.subject?.name ?? 'Definir matéria'}</span>
                  </button>
                  {pickerOpen ? (
                    <SubjectPicker
                      anchorRef={subjectButtonRef}
                      current={lecture.subject}
                      isSaving={isSavingSubject}
                      onClose={() => setPickerOpen(false)}
                      onConfirm={(subject) => void handleChangeSubject(subject)}
                    />
                  ) : null}
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
              gridTemplateColumns: showTree
                ? 'minmax(0, 1fr) minmax(0, 1.2fr)'
                : 'minmax(0, 1fr)',
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
                {lecture.summary ? (
                  <SummaryPdfButton
                    durationLabel={formatDuration(lecture.duration_seconds)}
                    lectureTitle={lecture.title}
                    subjectName={lecture.subject?.name ?? null}
                    summary={lecture.summary}
                    topicsCount={lecture.nodes.length}
                  />
                ) : (
                  <span className="tag accent">
                    <Icon name="sparkles" size={11} /> IA
                  </span>
                )}
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

            {showTree ? (
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
                  ) : (
                    <ProcessingState label="Construindo mapa mental..." />
                  )}
                </CardContent>
              </Card>
            ) : null}
          </div>

          {/* Actions */}
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
            <ActionButton
              icon="fileText"
              label="Ver transcrição completa"
              onClick={() => setTranscriptOpen(true)}
              primary
            />
            {lecture.guided_summary ? null : (
              <ActionButton
                disabled={!lecture.summary || !lecture.subject || isBuildingGuided}
                icon="bookOpen"
                label={isBuildingGuided ? 'Gerando resumo guiado...' : 'Gerar resumo guiado'}
                onClick={() => void handleGenerateGuided()}
                title={
                  lecture.subject
                    ? lecture.summary
                      ? undefined
                      : 'Disponível quando o resumo ficar pronto'
                    : 'Defina uma matéria com bibliografia anexada'
                }
              />
            )}
            {lecture.nodes.length > 0 ? null : (
              <ActionButton
                disabled={!lecture.summary || isBuildingMindmap}
                icon="sparkles"
                label={isBuildingMindmap ? 'Construindo mapa mental...' : 'Gerar mapa mental'}
                onClick={() => void handleGenerateMindmap()}
                title={lecture.summary ? undefined : 'Disponível quando o resumo ficar pronto'}
              />
            )}
          </div>

          {mindmapError ? (
            <p style={{ marginTop: 10, fontSize: 12, color: 'var(--danger)' }}>{mindmapError}</p>
          ) : null}
          {guidedError ? (
            <p style={{ marginTop: 10, fontSize: 12, color: 'var(--danger)' }}>{guidedError}</p>
          ) : null}

          {lecture.guided_summary || isBuildingGuided ? (
            <Card style={{ marginTop: 18 }}>
              <CardHeader>
                <div>
                  <CardTitle>Resumo guiado</CardTitle>
                  <div className="card-sub">
                    Explicado com a bibliografia de {lecture.subject?.name ?? 'sua matéria'}
                  </div>
                </div>
                <span className="tag accent">
                  <Icon name="bookOpen" size={11} /> {citations.length} tópicos
                </span>
              </CardHeader>
              <CardContent>
                {lecture.guided_summary ? (
                  <GuidedSummary citations={citations} markdown={lecture.guided_summary} />
                ) : (
                  <ProcessingState label="Escrevendo o resumo guiado..." />
                )}
              </CardContent>
            </Card>
          ) : null}

          {transcriptOpen ? (
            <TranscriptModal
              lectureTitle={lecture.title}
              onClose={() => setTranscriptOpen(false)}
              segments={lecture.segments}
              subjectName={lecture.subject?.name ?? null}
            />
          ) : null}

          {summaryOpen && lecture.summary ? (
            <SummaryModal
              lectureTitle={lecture.title}
              onClose={() => setSummaryOpen(false)}
              subjectName={lecture.subject?.name ?? null}
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
