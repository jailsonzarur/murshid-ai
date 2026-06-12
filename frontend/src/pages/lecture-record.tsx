import { useCallback, useEffect, useRef, useState } from 'react'

import { ExitConfirmModal } from '../components/lectures/ExitConfirmModal'
import { LiveTopicsPanel } from '../components/lectures/LiveTopicsPanel'
import { RecordingOrb } from '../components/lectures/RecordingOrb'
import { AppShell } from '../components/layout/app-shell'
import { Button } from '../components/ui/button'
import { Card, CardContent } from '../components/ui/card'
import { EmptyState } from '../components/ui/empty-state'
import { Icon } from '../components/ui/icon'
import { useLectureRecorder } from '../hooks/useLectureRecorder'
import {
  deleteLecture,
  finishLecture,
  getApiBaseUrl,
  getLecture,
  pauseLecture,
  resumeLecture,
} from '../lib/api'
import { getAccessToken, getAuthorizationHeader } from '../lib/auth'
import { navigateTo } from '../lib/navigation'
import type { LectureDetail } from '../types/lecture'

type Stage =
  | 'loading'
  | 'requesting-mic'
  | 'mic-denied'
  | 'recording'
  | 'paused'
  | 'finishing'
  | 'error'

function getLectureIdFromPath() {
  const [, resource, lectureId] = window.location.pathname.split('/')
  return resource === 'lectures' ? lectureId : ''
}

export function LectureRecordPage() {
  const [lecture, setLecture] = useState<LectureDetail | null>(null)
  const [stage, setStage] = useState<Stage>('loading')
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [timerSeconds, setTimerSeconds] = useState(0)
  const [exitOpen, setExitOpen] = useState(false)
  const [isBusy, setIsBusy] = useState(false)

  const recorder = useLectureRecorder({
    lectureId: lecture?.id ?? '',
    initialEvents: lecture?.events ?? [],
    initialMindmap: lecture?.mindmap_markdown ?? null,
  })

  const lectureIdRef = useRef<string>('')

  useEffect(() => {
    if (lecture) {
      lectureIdRef.current = lecture.id
    }
  }, [lecture])

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

    async function load() {
      try {
        const data = await getLecture(lectureId)
        setLecture(data)
        setTimerSeconds(data.duration_seconds)
        if (data.status === 'COMPLETED' || data.status === 'FAILED') {
          navigateTo(`/lectures/${lectureId}`, { replace: true })
          return
        }
        setStage('requesting-mic')
      } catch {
        setStage('error')
        setErrorMessage('Não foi possível carregar a aula.')
      }
    }

    void load()
  }, [])

  // request mic + start
  useEffect(() => {
    if (stage !== 'requesting-mic' || !lecture) return

    async function bootstrap() {
      try {
        if (lecture && lecture.status === 'PAUSED') {
          await resumeLecture(lecture.id)
        }
        await recorder.start()
        setStage('recording')
      } catch (error) {
        if (error instanceof DOMException && (error.name === 'NotAllowedError' || error.name === 'SecurityError')) {
          setStage('mic-denied')
        } else {
          setStage('error')
          setErrorMessage('Não foi possível iniciar a gravação.')
        }
      }
    }

    void bootstrap()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stage, lecture?.id])

  // timer
  useEffect(() => {
    if (stage !== 'recording') return
    const id = window.setInterval(() => {
      setTimerSeconds((value) => value + 1)
    }, 1000)
    return () => window.clearInterval(id)
  }, [stage])

  // auto-pause on tab close
  useEffect(() => {
    function handlePageHide() {
      const id = lectureIdRef.current
      if (!id) return
      if (stage !== 'recording' && stage !== 'paused') return
      const authorization = getAuthorizationHeader()
      if (!authorization) return
      try {
        fetch(`${getApiBaseUrl()}/lectures/${id}/pause`, {
          method: 'POST',
          headers: { Authorization: authorization },
          keepalive: true,
        })
      } catch {
        // swallow — browser is closing
      }
    }
    window.addEventListener('pagehide', handlePageHide)
    return () => window.removeEventListener('pagehide', handlePageHide)
  }, [stage])

  const handlePause = useCallback(async () => {
    if (!lecture) return
    setIsBusy(true)
    try {
      recorder.pause()
      await pauseLecture(lecture.id)
      setStage('paused')
    } finally {
      setIsBusy(false)
    }
  }, [lecture, recorder])

  const handleResume = useCallback(async () => {
    if (!lecture) return
    setIsBusy(true)
    try {
      await resumeLecture(lecture.id)
      recorder.resume()
      setStage('recording')
    } finally {
      setIsBusy(false)
    }
  }, [lecture, recorder])

  const handleFinish = useCallback(async () => {
    if (!lecture) return
    setIsBusy(true)
    setStage('finishing')
    try {
      await recorder.stop()
      await finishLecture(lecture.id)
      navigateTo(`/lectures/${lecture.id}`)
    } catch {
      setStage('error')
      setErrorMessage('Não foi possível finalizar a aula.')
    } finally {
      setIsBusy(false)
    }
  }, [lecture, recorder])

  const handlePauseAndExit = useCallback(async () => {
    if (!lecture) return
    setIsBusy(true)
    try {
      await recorder.stop()
      if (stage === 'recording') {
        await pauseLecture(lecture.id)
      }
      navigateTo('/lectures')
    } catch {
      setIsBusy(false)
    }
  }, [lecture, recorder, stage])

  const handleDiscard = useCallback(async () => {
    if (!lecture) return
    setIsBusy(true)
    try {
      await recorder.stop()
      await deleteLecture(lecture.id)
      navigateTo('/lectures')
    } catch {
      setIsBusy(false)
    }
  }, [lecture, recorder])

  const handleRetryMic = useCallback(() => {
    setStage('requesting-mic')
  }, [])

  return (
    <AppShell
      actions={
        <Button
          icon="arrowLeft"
          disabled={isBusy || stage === 'finishing' || stage === 'loading'}
          onClick={() => setExitOpen(true)}
          variant="outline"
        >
          Sair
        </Button>
      }
      activeItem="lectures"
      title="Transcrevendo aula"
    >
      {stage === 'loading' ? (
        <EmptyState description="Carregando a aula..." title="Carregando..." />
      ) : stage === 'error' ? (
        <EmptyState
          action={
            <Button onClick={() => navigateTo('/lectures')} variant="outline">
              Voltar
            </Button>
          }
          description={errorMessage ?? 'Algo deu errado.'}
          title="Não foi possível continuar."
        />
      ) : stage === 'mic-denied' ? (
        <EmptyState
          action={
            <Button icon="video" onClick={handleRetryMic}>
              Tentar novamente
            </Button>
          }
          description="Permita o uso do microfone no navegador para iniciar a gravação."
          title="Microfone bloqueado"
        />
      ) : !lecture ? null : (
        <>
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'minmax(0, 1.05fr) minmax(0, 1fr)',
              gap: 18,
              alignItems: 'stretch',
            }}
          >
            <Card>
              <CardContent style={{ padding: 28 }}>
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'flex-start',
                    marginBottom: 20,
                  }}
                >
                  <div>
                    <div className="eyebrow">
                      <span className="eyebrow-dot" />
                      Gravação ao vivo
                    </div>
                    <h2 style={{ margin: '4px 0 6px', fontSize: 20, fontWeight: 700 }}>
                      {lecture.title ?? 'Aula sem título'}
                    </h2>
                    <div style={{ fontSize: 12.5, color: 'var(--ink-4)', display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                      <Icon name="tag" size={12} />
                      {lecture.category?.name ?? 'Sem matéria'}
                    </div>
                  </div>
                  <span
                    className={stage === 'paused' ? 'pill pill-warn' : 'pill pill-danger'}
                  >
                    <span
                      aria-hidden="true"
                      style={{
                        width: 7,
                        height: 7,
                        borderRadius: '50%',
                        background: 'currentColor',
                        marginRight: 6,
                        animation: stage === 'recording' ? 'pulse 1.4s ease-in-out infinite' : 'none',
                      }}
                    />
                    {stage === 'paused' ? 'Pausado' : stage === 'finishing' ? 'Finalizando' : 'Gravando'}
                  </span>
                </div>

                <RecordingOrb
                  isPaused={stage === 'paused'}
                  isProcessing={recorder.isProcessing}
                  timerSeconds={timerSeconds}
                />

                <div style={{ display: 'flex', gap: 10, justifyContent: 'center', marginTop: 28 }}>
                  {stage === 'paused' ? (
                    <button
                      className="btn btn-primary"
                      disabled={isBusy}
                      onClick={handleResume}
                      type="button"
                    >
                      <Icon name="video" size={14} />
                      <span>Retomar</span>
                    </button>
                  ) : (
                    <button
                      className="btn btn-ghost"
                      disabled={isBusy || stage !== 'recording'}
                      onClick={handlePause}
                      type="button"
                    >
                      <Icon name="pause" size={14} />
                      <span>Pausar</span>
                    </button>
                  )}
                  <button
                    className="btn btn-danger"
                    disabled={isBusy || stage === 'finishing'}
                    onClick={handleFinish}
                    type="button"
                  >
                    <Icon name="square" size={14} />
                    <span>{stage === 'finishing' ? 'Finalizando...' : 'Finalizar'}</span>
                  </button>
                </div>
              </CardContent>
            </Card>

            <LiveTopicsPanel events={recorder.events} isProcessing={recorder.isProcessing} />
          </div>

          {exitOpen ? (
            <ExitConfirmModal
              isBusy={isBusy}
              onCancel={() => setExitOpen(false)}
              onDiscard={handleDiscard}
              onPauseAndExit={handlePauseAndExit}
            />
          ) : null}
        </>
      )}

      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.35; }
        }
      `}</style>
    </AppShell>
  )
}
