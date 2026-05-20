import { useEffect, useRef, useState } from 'react'

import { QuestionCard } from '../components/exam-viewer/QuestionCard'
import { AppShell } from '../components/layout/app-shell'
import { Badge } from '../components/ui/badge'
import { Button } from '../components/ui/button'
import { Card } from '../components/ui/card'
import { EmptyState } from '../components/ui/empty-state'
import { Icon } from '../components/ui/icon'
import {
  ApiError,
  evaluateResolution,
  evaluateResolutionQuestion,
  getResolution,
  pauseResolution,
  resumeResolution,
  submitResolution,
  upsertQuestionResponse,
} from '../lib/api'
import { getAccessToken, getAuthorizationHeader } from '../lib/auth'
import { navigateTo } from '../lib/navigation'
import type {
  ExamAnswers,
  Question,
  QuestionAnswer,
  QuestionResponse,
  ResolutionDetail,
  ResolutionQuestionDetail,
  ResolutionStatus,
} from '../types/exam'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8002'

function getResolutionIdFromPath() {
  const [, resource, resolutionId] = window.location.pathname.split('/')
  return resource === 'resolutions' ? resolutionId : ''
}

function hasAnswer(answer: QuestionAnswer | undefined) {
  if (!answer) {
    return false
  }

  if (typeof answer === 'string') {
    return answer.trim().length > 0
  }

  if (Array.isArray(answer)) {
    return answer.length > 0
  }

  return Object.values(answer).some((value) => value.trim().length > 0)
}

function responseToAnswer(question: Question, response?: QuestionResponse | null): QuestionAnswer | undefined {
  if (!response) {
    return undefined
  }

  if (question.type !== 'SUBJECTIVE') {
    return response.items.flatMap((item) => (item.option_id ? [item.option_id] : []))
  }

  if (question.options.length) {
    return Object.fromEntries(
      response.items
        .filter((item) => item.option_id)
        .map((item) => [item.option_id as string, item.text_answer ?? '']),
    )
  }

  return response.items[0]?.text_answer ?? ''
}

function buildAnswers(detail: ResolutionDetail) {
  return Object.fromEntries(
    detail.questions.flatMap((item) => {
      const answer = responseToAnswer(item.question, item.response)
      return answer === undefined ? [] : [[item.question.id, answer]]
    }),
  )
}

function answerToItems(question: Question, answer: QuestionAnswer | undefined) {
  if (question.type !== 'SUBJECTIVE') {
    const optionIds = Array.isArray(answer) ? answer : typeof answer === 'string' && answer ? [answer] : []
    return optionIds.map((optionId) => ({ option_id: optionId }))
  }

  if (question.options.length) {
    const answersByOption = answer && !Array.isArray(answer) && typeof answer !== 'string' ? answer : {}
    return question.options
      .map((option) => ({
        option_id: option.id,
        text_answer: answersByOption[option.id]?.trim(),
      }))
      .filter((item) => item.text_answer)
  }

  return typeof answer === 'string' && answer.trim() ? [{ text_answer: answer.trim() }] : []
}

function formatTimer(totalSeconds: number) {
  const hours = Math.floor(totalSeconds / 3600)
  const minutes = Math.floor((totalSeconds % 3600) / 60)
  const seconds = totalSeconds % 60

  return [hours, minutes, seconds].map((value) => String(value).padStart(2, '0')).join(':')
}

function statusLabel(status: ResolutionStatus) {
  const labels: Record<ResolutionStatus, string> = {
    ERROR: 'Erro',
    GRADED: 'Corrigida',
    IN_PROGRESS: 'Em andamento',
    PAUSED: 'Pausada',
    SUBMITTED: 'Enviada',
  }

  return labels[status]
}

export function ResolutionViewerPage() {
  const [detail, setDetail] = useState<ResolutionDetail | null>(null)
  const [answers, setAnswers] = useState<ExamAnswers>({})
  const [currentIndex, setCurrentIndex] = useState(0)
  const [elapsedSeconds, setElapsedSeconds] = useState(0)
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isEvaluatingQuestion, setIsEvaluatingQuestion] = useState(false)
  const [isEvaluatingResolution, setIsEvaluatingResolution] = useState(false)
  const [correctionError, setCorrectionError] = useState<string | null>(null)
  const [showResolutionOverview, setShowResolutionOverview] = useState(false)
  const detailRef = useRef<ResolutionDetail | null>(null)
  const pauseRequestedRef = useRef(false)

  const resolutionId = getResolutionIdFromPath()
  const currentQuestionDetail = detail?.questions[currentIndex]
  const currentQuestion = currentQuestionDetail?.question
  const resolutionStatus = detail?.resolution.status
  const pollingResolutionId = detail?.resolution.id
  const isReadOnly = detail ? detail.resolution.status !== 'IN_PROGRESS' : true
  const isLastQuestion = detail ? currentIndex === detail.questions.length - 1 : false
  const isStudyMode = detail?.resolution.mode === 'STUDY'
  const currentQuestionHasAnswer = currentQuestion ? hasAnswer(answers[currentQuestion.id]) : false
  const currentQuestionHasEvaluation = Boolean(currentQuestionDetail?.response?.evaluation)
  const shouldEvaluateCurrentQuestion = Boolean(
    isStudyMode && currentQuestionHasAnswer && !currentQuestionHasEvaluation && !isReadOnly,
  )
  const isCorrectionPending = Boolean(
    detail && (isEvaluatingResolution || detail.resolution.status === 'SUBMITTED'),
  )
  const answeredCount = detail?.questions.filter((item) => hasAnswer(answers[item.question.id])).length ?? 0
  const evaluatedCount = detail?.questions.filter((item) => item.response?.evaluation).length ?? 0
  const fullScoreCount =
    detail?.questions.filter((item) => (item.response?.evaluation?.score ?? 0) >= 1).length ?? 0
  const partialScoreCount =
    detail?.questions.filter((item) => {
      const score = item.response?.evaluation?.score
      return score !== undefined && score > 0 && score < 1
    }).length ?? 0
  const zeroScoreCount =
    detail?.questions.filter((item) => item.response?.evaluation && item.response.evaluation.score <= 0).length ?? 0
  const progress = detail?.questions.length ? ((currentIndex + 1) / detail.questions.length) * 100 : 0

  const summaryText =
    detail?.resolution.score || detail?.resolution.score === 0
      ? `${Math.round(detail.resolution.score * 100)}%`
      : null
  const resultText =
    detail?.resolution.result === 'PASSED'
      ? 'Aprovado'
      : detail?.resolution.result === 'FAILED'
        ? 'Reprovado'
        : null

  useEffect(() => {
    detailRef.current = detail
  }, [detail])

  useEffect(() => {
    if (!getAccessToken()) {
      navigateTo('/login', { replace: true })
      return
    }

    if (!resolutionId) {
      navigateTo('/exams', { replace: true })
      return
    }

    async function loadResolution() {
      setIsLoading(true)

      try {
        let nextDetail = await getResolution(resolutionId)

        if (nextDetail.resolution.status === 'PAUSED') {
          await resumeResolution(resolutionId)
          nextDetail = await getResolution(resolutionId)
        }

        setDetail(nextDetail)
        detailRef.current = nextDetail
        pauseRequestedRef.current = false
        setAnswers(buildAnswers(nextDetail))
        setElapsedSeconds(nextDetail.resolution.time_spent_seconds)
        setIsEvaluatingResolution(nextDetail.resolution.status === 'SUBMITTED')
        setShowResolutionOverview(nextDetail.resolution.status === 'GRADED')
      } catch {
        setDetail(null)
      } finally {
        setIsLoading(false)
      }
    }

    void loadResolution()
  }, [resolutionId])

  useEffect(() => {
    if (!detail || detail.resolution.status !== 'IN_PROGRESS') {
      return
    }

    const intervalId = window.setInterval(() => {
      setElapsedSeconds((current) => current + 1)
    }, 1000)

    return () => window.clearInterval(intervalId)
  }, [detail])

  useEffect(() => {
    if (!pollingResolutionId || resolutionStatus !== 'SUBMITTED') {
      return
    }

    let shouldIgnore = false
    const activePollingResolutionId = pollingResolutionId

    async function pollCorrection() {
      try {
        const nextDetail = await getResolution(activePollingResolutionId)

        if (shouldIgnore) {
          return
        }

        setDetail(nextDetail)
        detailRef.current = nextDetail
        setAnswers(buildAnswers(nextDetail))

        if (nextDetail.resolution.status === 'GRADED') {
          setCurrentIndex(0)
          setIsEvaluatingResolution(false)
          setCorrectionError(null)
          setShowResolutionOverview(true)
        }

        if (nextDetail.resolution.status === 'ERROR') {
          setIsEvaluatingResolution(false)
          setCorrectionError('Não foi possível concluir a correção desta resolução.')
        }
      } catch {
        if (!shouldIgnore) {
          setCorrectionError('Não foi possível consultar o status da correção.')
        }
      }
    }

    void pollCorrection()
    const intervalId = window.setInterval(() => {
      void pollCorrection()
    }, 3000)

    return () => {
      shouldIgnore = true
      window.clearInterval(intervalId)
    }
  }, [pollingResolutionId, resolutionStatus])

  useEffect(() => {
    function pauseBeforeUnload() {
      const currentDetail = detailRef.current

      if (
        !currentDetail ||
        currentDetail.resolution.status !== 'IN_PROGRESS' ||
        pauseRequestedRef.current
      ) {
        return
      }

      const authorization = getAuthorizationHeader()

      if (!authorization) {
        return
      }

      pauseRequestedRef.current = true
      void fetch(`${API_BASE_URL}/resolutions/${currentDetail.resolution.id}/pause`, {
        method: 'POST',
        headers: {
          Authorization: authorization,
        },
        keepalive: true,
      })
    }

    window.addEventListener('pagehide', pauseBeforeUnload)
    window.addEventListener('beforeunload', pauseBeforeUnload)
    window.addEventListener('popstate', pauseBeforeUnload)

    return () => {
      window.removeEventListener('pagehide', pauseBeforeUnload)
      window.removeEventListener('beforeunload', pauseBeforeUnload)
      window.removeEventListener('popstate', pauseBeforeUnload)
    }
  }, [])

  function handleAnswerChange(answer: QuestionAnswer) {
    if (!currentQuestion) {
      return
    }

    setAnswers((currentAnswers) => ({
      ...currentAnswers,
      [currentQuestion.id]: answer,
    }))

    setDetail((currentDetail) => {
      if (!currentDetail) {
        return currentDetail
      }

      const nextDetail = {
        ...currentDetail,
        questions: currentDetail.questions.map((item) =>
          item.question.id === currentQuestion.id && item.response
            ? { ...item, response: { ...item.response, evaluation: null } }
            : item,
        ),
      }
      detailRef.current = nextDetail
      return nextDetail
    })
  }

  async function saveCurrentAnswer() {
    if (!detail || !currentQuestion || isReadOnly) {
      return undefined
    }

    if (currentQuestionDetail?.response) {
      return currentQuestionDetail.response
    }

    const items = answerToItems(currentQuestion, answers[currentQuestion.id])
    if (!items.length) {
      return undefined
    }

    setIsSaving(true)

    try {
      const response = await saveAnswerItems(detail.resolution.id, currentQuestion.id, items)
      setDetail((currentDetail) => {
        if (!currentDetail) {
          return currentDetail
        }

        const nextDetail = {
          ...currentDetail,
          questions: currentDetail.questions.map((item) =>
            item.question.id === currentQuestion.id ? { ...item, response } : item,
          ),
        }
        detailRef.current = nextDetail
        return nextDetail
      })
      return response
    } finally {
      setIsSaving(false)
    }
  }

  async function saveAnswerItems(
    resolutionId: string,
    questionId: string,
    items: ReturnType<typeof answerToItems>,
  ) {
    try {
      return await upsertQuestionResponse(resolutionId, questionId, items)
    } catch (error) {
      if (!(error instanceof ApiError) || !error.message.includes('não está em andamento')) {
        throw error
      }

      const latestDetail = await getResolution(resolutionId)
      if (latestDetail.resolution.status !== 'PAUSED') {
        setDetail(latestDetail)
        detailRef.current = latestDetail
        throw error
      }

      await resumeResolution(resolutionId)
      const resumedDetail = await getResolution(resolutionId)
      setDetail(resumedDetail)
      detailRef.current = resumedDetail
      pauseRequestedRef.current = false

      return upsertQuestionResponse(resolutionId, questionId, items)
    }
  }

  async function goToPreviousQuestion() {
    await saveCurrentAnswer()
    setCurrentIndex((index) => Math.max(index - 1, 0))
  }

  async function goToNextQuestion() {
    if (shouldEvaluateCurrentQuestion) {
      await evaluateCurrentQuestion()
      return
    }

    await saveCurrentAnswer()
    setCurrentIndex((index) => Math.min(index + 1, (detail?.questions.length ?? 1) - 1))
  }

  async function evaluateCurrentQuestion() {
    if (!detail || !currentQuestion || !currentQuestionHasAnswer || isReadOnly) {
      return
    }

    if (currentQuestionDetail?.response?.evaluation) {
      return
    }

    setIsEvaluatingQuestion(true)

    try {
      await saveCurrentAnswer()
      const response = await evaluateResolutionQuestion(detail.resolution.id, currentQuestion.id)
      setDetail((currentDetail) => {
        if (!currentDetail) {
          return currentDetail
        }

        const nextDetail = {
          ...currentDetail,
          questions: currentDetail.questions.map((item) =>
            item.question.id === currentQuestion.id ? { ...item, response } : item,
          ),
        }
        detailRef.current = nextDetail
        return nextDetail
      })
    } finally {
      setIsEvaluatingQuestion(false)
    }
  }

  async function handlePauseAndExit() {
    await pauseActiveResolution()
    navigateTo('/exams')
  }

  async function pauseActiveResolution() {
    if (!detail) {
      return
    }

    await saveCurrentAnswer()

    if (detail.resolution.status === 'IN_PROGRESS' && !pauseRequestedRef.current) {
      pauseRequestedRef.current = true
      const pausedResolution = await pauseResolution(detail.resolution.id)

      setDetail((currentDetail) => {
        if (!currentDetail) {
          return currentDetail
        }

        const nextDetail = { ...currentDetail, resolution: pausedResolution }
        detailRef.current = nextDetail
        return nextDetail
      })
    }
  }

  async function handleSubmitResolution() {
    if (!detail) {
      return
    }

    setIsSubmitting(true)

    try {
      let evaluatedCurrentQuestion = false
      if (shouldEvaluateCurrentQuestion) {
        await evaluateCurrentQuestion()
        evaluatedCurrentQuestion = true
      }

      if (!evaluatedCurrentQuestion) {
        await saveCurrentAnswer()
      }

      const result = await submitResolution(detail.resolution.id)
      pauseRequestedRef.current = true

      if (detail.resolution.mode === 'STUDY') {
        const nextDetail = await getResolution(detail.resolution.id)
        setDetail(nextDetail)
        detailRef.current = nextDetail
        setAnswers(buildAnswers(nextDetail))
        setShowResolutionOverview(true)
        setCorrectionError(null)
        return
      }

      const evaluationTask = await evaluateResolution(detail.resolution.id)
      const nextResolution = evaluationTask.resolution ?? result.resolution

      setIsEvaluatingResolution(nextResolution.status === 'SUBMITTED')
      setShowResolutionOverview(nextResolution.status === 'GRADED')
      setCorrectionError(null)
      setDetail((currentDetail) => {
        if (!currentDetail) {
          return currentDetail
        }

        const nextDetail = {
          ...currentDetail,
          resolution: nextResolution,
        }
        detailRef.current = nextDetail
        return nextDetail
      })
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <AppShell
      actions={
        <Button icon="arrowLeft" onClick={handlePauseAndExit} variant="outline">
          Voltar para provas
        </Button>
      }
      activeItem="exams"
      description="Resolva a prova, pause quando necessário e acompanhe o resultado da tentativa."
      onBeforeLeave={pauseActiveResolution}
      searchPlaceholder="Buscar questões..."
      title="Resolução da prova"
    >
      <Card className="tasko-card exam-viewer-panel">
        {isLoading ? (
          <div className="loading-state">
            <span>
              <Icon name="clock" size={18} />
            </span>
            <p>Carregando resolução...</p>
          </div>
        ) : !detail || !currentQuestionDetail || !currentQuestion ? (
          <EmptyState
            description="Não foi possível carregar esta resolução."
            title="Resolução indisponível."
          />
        ) : showResolutionOverview && detail.resolution.status === 'GRADED' ? (
          <section className="resolution-overview">
            <div className="resolution-overview__heading">
              <Badge tone={detail.resolution.result === 'PASSED' ? 'green' : 'orange'}>
                {resultText ?? 'Resultado'}
              </Badge>
              <h2>{summaryText ?? '0%'}</h2>
              <p>
                Resumo geral da sua resolução em modo{' '}
                {detail.resolution.mode === 'STUDY' ? 'estudo' : 'exame'}.
              </p>
            </div>

            <div className="resolution-overview__metrics">
              <div>
                <span>Questões</span>
                <strong>{detail.questions.length}</strong>
              </div>
              <div>
                <span>Respondidas</span>
                <strong>{answeredCount}</strong>
              </div>
              <div>
                <span>Corrigidas</span>
                <strong>{evaluatedCount}</strong>
              </div>
              <div>
                <span>Tempo</span>
                <strong>{formatTimer(detail.resolution.time_spent_seconds)}</strong>
              </div>
            </div>

            <div className="resolution-overview__breakdown">
              <span>
                <strong>{fullScoreCount}</strong>
                completas
              </span>
              <span>
                <strong>{partialScoreCount}</strong>
                parciais
              </span>
              <span>
                <strong>{zeroScoreCount}</strong>
                zeradas
              </span>
            </div>

            <div className="resolution-overview__actions">
              <Button icon="listChecks" onClick={() => setShowResolutionOverview(false)}>
                Ver questões corrigidas
              </Button>
              <Button icon="arrowLeft" onClick={() => navigateTo('/exams')} variant="outline">
                Voltar para provas
              </Button>
            </div>
          </section>
        ) : isCorrectionPending ? (
          <section className="resolution-correction-loading">
            <div className="correction-loader" aria-hidden="true">
              <span>
                <Icon name="sparkles" size={24} />
              </span>
            </div>
            <div className="resolution-correction-loading__content">
              <Badge tone="blue">Correção automática</Badge>
              <h2>Corrigindo a resolução</h2>
              <p>
                Estamos analisando suas respostas e preparando o resumo final da prova.
              </p>
            </div>
            <div className="resolution-correction-loading__steps" aria-label="Status da correção">
              <span>
                <Icon name="checkCircle" size={15} />
                Respostas enviadas
              </span>
              <span>
                <Icon name="clock" size={15} />
                Avaliando questões
              </span>
              <span>
                <Icon name="chart" size={15} />
                Montando resultado
              </span>
            </div>
            {correctionError ? <p className="inline-alert inline-alert--danger">{correctionError}</p> : null}
          </section>
        ) : (
          <section className="exam-viewer">
            <header className="exam-viewer-header resolution-viewer-header">
              <div>
                <p className="progress-indicator">
                  Questão {currentIndex + 1} de {detail.questions.length}
                </p>
                <h2>
                  {currentQuestion.type !== 'SUBJECTIVE'
                    ? 'Questão objetiva'
                    : 'Questão discursiva'}
                </h2>
              </div>
              <div className="resolution-toolbar">
                <Badge tone={detail.resolution.mode === 'EXAM' ? 'blue' : 'green'}>
                  {detail.resolution.mode === 'EXAM' ? 'Exame' : 'Estudo'}
                </Badge>
                <div className="resolution-timer">
                  <Icon name="clock" size={15} />
                  {formatTimer(elapsedSeconds)}
                </div>
                <Badge tone="outline">{answeredCount} respondidas</Badge>
                <Badge tone="outline">{statusLabel(detail.resolution.status)}</Badge>
                {summaryText ? <Badge tone="green">{summaryText}</Badge> : null}
                {resultText ? (
                  <Badge tone={detail.resolution.result === 'PASSED' ? 'green' : 'orange'}>
                    {resultText}
                  </Badge>
                ) : null}
                <Button
                  disabled={isSubmitting}
                  icon="pause"
                  onClick={handlePauseAndExit}
                  size="sm"
                  variant="outline"
                >
                  Sair
                </Button>
              </div>
            </header>

            <div className="exam-progress" aria-hidden="true">
              <span style={{ width: `${progress}%` }} />
            </div>

            <nav className="question-jump-list" aria-label="Ir para questão">
              {detail.questions.map((item: ResolutionQuestionDetail, index) => (
                <button
                  aria-label={`Ir para questão ${index + 1}`}
                  className={index === currentIndex ? 'is-active' : undefined}
                  key={item.question.id}
                  onClick={async () => {
                    await saveCurrentAnswer()
                    setCurrentIndex(index)
                  }}
                  type="button"
                >
                  {index + 1}
                  {hasAnswer(answers[item.question.id]) ? <span /> : null}
                </button>
              ))}
            </nav>

            <main className="exam-viewer-body">
              <QuestionCard
                currentAnswer={answers[currentQuestion.id]}
                evaluation={currentQuestionDetail.response?.evaluation}
                isReadOnly={isReadOnly}
                onAnswerChange={handleAnswerChange}
                question={currentQuestion}
                showEvaluation={detail.can_show_evaluations}
              />
            </main>

            {detail.resolution.status === 'GRADED' ? (
              <section className="resolution-result-panel">
                <Badge tone="green">Resultado</Badge>
                <h3>{summaryText ?? 'Correção concluída'}</h3>
                <p>
                  {resultText
                    ? `${resultText}. Veja o score e o feedback de cada questão abaixo do enunciado.`
                    : 'Veja o score e o feedback de cada questão abaixo do enunciado.'}
                </p>
              </section>
            ) : null}

            <footer className="exam-viewer-footer">
              <nav className="navigation-buttons" aria-label="Navegação entre questões">
                <Button
                    disabled={currentIndex === 0 || isSaving || isSubmitting || isEvaluatingQuestion}
                  icon="arrowLeft"
                  onClick={goToPreviousQuestion}
                  type="button"
                  variant="secondary"
                >
                  Anterior
                </Button>

                {isLastQuestion ? (
                  <Button
                    disabled={isSaving || isSubmitting || isReadOnly}
                    icon="checkCircle"
                    onClick={handleSubmitResolution}
                    type="button"
                    variant="dark"
                  >
                    {isSubmitting ? 'Finalizando...' : 'Finalizar'}
                  </Button>
                ) : (
                  <Button
                    disabled={isSaving || isSubmitting || isEvaluatingQuestion}
                    icon={shouldEvaluateCurrentQuestion ? 'checkCircle' : 'arrowRight'}
                    onClick={goToNextQuestion}
                    type="button"
                  >
                    {isEvaluatingQuestion
                      ? 'Corrigindo...'
                      : isSaving
                        ? 'Salvando...'
                        : shouldEvaluateCurrentQuestion
                          ? 'Corrigir'
                          : 'Próxima'}
                  </Button>
                )}
              </nav>
            </footer>
          </section>
        )}
      </Card>
    </AppShell>
  )
}
