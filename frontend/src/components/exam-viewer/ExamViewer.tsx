import { useState } from 'react'

import type { ExamAnswers, Question, QuestionAnswer } from '../../types/exam'
import { Button } from '../ui/button'
import { QuestionCard } from './QuestionCard'

type ExamViewerProps = {
  questions: Question[]
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

export function ExamViewer({ questions }: ExamViewerProps) {
  const [currentIndex, setCurrentIndex] = useState(0)
  const [answers, setAnswers] = useState<ExamAnswers>({})
  const [submissionMessage, setSubmissionMessage] = useState<string | null>(null)

  const currentQuestion = questions[currentIndex]
  const isFirstQuestion = currentIndex === 0
  const isLastQuestion = currentIndex === questions.length - 1
  const answeredCount = questions.filter((question) => hasAnswer(answers[question.id])).length
  const progress = questions.length ? ((currentIndex + 1) / questions.length) * 100 : 0

  function handleAnswerChange(answer: QuestionAnswer) {
    if (!currentQuestion) {
      return
    }

    setSubmissionMessage(null)
    setAnswers((currentAnswers) => ({
      ...currentAnswers,
      [currentQuestion.id]: answer,
    }))
  }

  function goToPreviousQuestion() {
    setCurrentIndex((index) => Math.max(index - 1, 0))
  }

  function goToNextQuestion() {
    setCurrentIndex((index) => Math.min(index + 1, questions.length - 1))
  }

  function submitExam() {
    console.info('Exam submitted', answers)
    setSubmissionMessage('Respostas registradas localmente para esta sessão.')
  }

  return (
    <div className="quiz-main">
      <div className="quiz-head">
        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="q-num">
            Questão {String(currentIndex + 1).padStart(2, '0')} de {questions.length}
          </div>
          <h2>
            {currentQuestion.type !== 'SUBJECTIVE' ? 'Questão objetiva' : 'Questão discursiva'}
          </h2>
          <div className="q-progress">
            <i style={{ width: `${progress}%` }} />
          </div>
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              marginTop: 6,
              fontSize: 11.5,
              color: 'var(--ink-4)',
              fontWeight: 500,
            }}
          >
            <span>{answeredCount} de {questions.length} respondidas</span>
            <span>{Math.round(progress)}% completo</span>
          </div>
        </div>
      </div>

      <div className="q-bullets">
        {questions.map((question, index) => {
          const answered = hasAnswer(answers[question.id])
          const cls = ['q-bullet', answered ? 'answered' : '', index === currentIndex ? 'current' : '']
            .filter(Boolean)
            .join(' ')
          return (
            <button
              aria-label={`Ir para questão ${index + 1}`}
              className={cls}
              key={question.id}
              onClick={() => setCurrentIndex(index)}
              type="button"
            >
              {index + 1}
            </button>
          )
        })}
      </div>

      <div className="q-body">
        <QuestionCard
          currentAnswer={answers[currentQuestion.id]}
          onAnswerChange={handleAnswerChange}
          question={currentQuestion}
        />
      </div>

      {submissionMessage ? (
        <div style={{ padding: '0 26px' }}>
          <p className="inline-alert inline-alert--success">{submissionMessage}</p>
        </div>
      ) : null}

      <div className="q-foot">
        <div className="q-foot-meta">
          <strong>{answeredCount}</strong> de {questions.length} respondidas
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <Button
            disabled={isFirstQuestion}
            icon="arrowLeft"
            onClick={goToPreviousQuestion}
            size="sm"
            type="button"
            variant="secondary"
          >
            Anterior
          </Button>
          {isLastQuestion ? (
            <Button icon="checkCircle" onClick={submitExam} size="sm" type="button" variant="dark">
              Finalizar
            </Button>
          ) : (
            <Button icon="arrowRight" onClick={goToNextQuestion} size="sm" type="button">
              Próxima questão
            </Button>
          )}
        </div>
      </div>
    </div>
  )
}
