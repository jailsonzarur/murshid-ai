import { useState } from 'react'

import type { ExamAnswers, Question, QuestionAnswer } from '../../types/exam'
import { Button } from '../ui/button'
import { EmptyState } from '../ui/empty-state'
import { Icon } from '../ui/icon'
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

  if (!questions.length) {
    return (
      <section className="exam-viewer exam-viewer-empty">
        <EmptyState
          description="Quando o processamento terminar, as questões estruturadas aparecerão aqui."
          title="Nenhuma questão disponível para esta prova."
        />
      </section>
    )
  }

  return (
    <section className="exam-viewer">
      <header className="exam-viewer-header">
        <div>
          <p className="progress-indicator">
            Questão {currentIndex + 1} de {questions.length}
          </p>
          <h2>{currentQuestion.type === 'OBJECTIVE' ? 'Questão objetiva' : 'Questão discursiva'}</h2>
        </div>
        <div className="answered-pill">
          <Icon name="checkCircle" size={15} />
          {answeredCount} respondidas
        </div>
      </header>

      <div className="exam-progress" aria-hidden="true">
        <span style={{ width: `${progress}%` }} />
      </div>

      <nav className="question-jump-list" aria-label="Ir para questão">
        {questions.map((question, index) => (
          <button
            aria-label={`Ir para questão ${index + 1}`}
            className={index === currentIndex ? 'is-active' : undefined}
            key={question.id}
            onClick={() => setCurrentIndex(index)}
            type="button"
          >
            {index + 1}
            {hasAnswer(answers[question.id]) ? <span /> : null}
          </button>
        ))}
      </nav>

      <main className="exam-viewer-body">
        <QuestionCard
          currentAnswer={answers[currentQuestion.id]}
          onAnswerChange={handleAnswerChange}
          question={currentQuestion}
        />
      </main>

      <footer className="exam-viewer-footer">
        {submissionMessage ? <p className="inline-alert inline-alert--success">{submissionMessage}</p> : null}
        <nav className="navigation-buttons" aria-label="Navegação entre questões">
          <Button
            disabled={isFirstQuestion}
            icon="arrowLeft"
            onClick={goToPreviousQuestion}
            type="button"
            variant="secondary"
          >
            Anterior
          </Button>

          {isLastQuestion ? (
            <Button icon="checkCircle" onClick={submitExam} type="button" variant="dark">
              Finalizar
            </Button>
          ) : (
            <Button icon="arrowRight" onClick={goToNextQuestion} type="button">
              Próxima
            </Button>
          )}
        </nav>
      </footer>
    </section>
  )
}
