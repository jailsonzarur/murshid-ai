import ReactMarkdown from 'react-markdown'

import type { Question, QuestionAnswer, QuestionResponseEvaluation } from '../../types/exam'

type QuestionCardProps = {
  currentAnswer?: QuestionAnswer
  evaluation?: QuestionResponseEvaluation | null
  isReadOnly?: boolean
  onAnswerChange: (answer: QuestionAnswer) => void
  question: Question
  showEvaluation?: boolean
}

function getMultiItemAnswers(currentAnswer?: QuestionAnswer) {
  if (!currentAnswer || typeof currentAnswer === 'string' || Array.isArray(currentAnswer)) {
    return {}
  }

  return currentAnswer
}

function getObjectiveAnswers(currentAnswer?: QuestionAnswer) {
  if (Array.isArray(currentAnswer)) {
    return currentAnswer
  }

  if (typeof currentAnswer === 'string' && currentAnswer) {
    return [currentAnswer]
  }

  return []
}

export function QuestionCard({
  currentAnswer,
  evaluation,
  isReadOnly = false,
  onAnswerChange,
  question,
  showEvaluation = false,
}: QuestionCardProps) {
  const isObjective = question.type !== 'SUBJECTIVE'
  const isObjectiveMulti = question.type === 'OBJECTIVE_MULTI'
  const hasOptions = question.options.length > 0
  const multiItemAnswers = getMultiItemAnswers(currentAnswer)
  const objectiveAnswers = getObjectiveAnswers(currentAnswer)
  const shouldShowScore = question.type === 'SUBJECTIVE' || question.type === 'OBJECTIVE_MULTI'
  const isLowScore = evaluation ? evaluation.score < 0.5 : false

  function handleMultiItemAnswerChange(optionId: string, answer: string) {
    if (isReadOnly) {
      return
    }

    onAnswerChange({
      ...multiItemAnswers,
      [optionId]: answer,
    })
  }

  function handleObjectiveAnswerChange(optionId: string, checked: boolean) {
    if (isReadOnly) {
      return
    }

    if (!isObjectiveMulti) {
      onAnswerChange(optionId)
      return
    }

    if (checked) {
      onAnswerChange([...objectiveAnswers, optionId])
      return
    }

    onAnswerChange(objectiveAnswers.filter((currentOptionId) => currentOptionId !== optionId))
  }

  return (
    <article className="question-card">
      <header className="question-header">
        <span>
          {isObjectiveMulti
            ? 'Múltipla seleção'
            : isObjective
              ? 'Múltipla escolha'
              : 'Resposta aberta'}
        </span>
        <h3 className="question-statement">{question.statement}</h3>
      </header>

      {question.image_url ? (
        <img alt="Imagem relacionada à questão" className="question-image" src={question.image_url} />
      ) : null}

      <section className="question-interaction" aria-label="Área de resposta">
        {isObjective && hasOptions ? (
          <fieldset className="answer-options">
            <legend className="answer-options-title">
              {isObjectiveMulti ? 'Selecione uma ou mais respostas' : 'Selecione uma resposta'}
            </legend>
            {question.options.map((option) => (
              <label className="option-row" key={option.id}>
                <input
                  checked={objectiveAnswers.includes(option.id)}
                  className="option-radio"
                  name={`question-${question.id}`}
                  disabled={isReadOnly}
                  onChange={(event) => handleObjectiveAnswerChange(option.id, event.target.checked)}
                  type={isObjectiveMulti ? 'checkbox' : 'radio'}
                  value={option.id}
                />
                <span className="option-content">
                  {option.letter ? <strong className="option-letter">{option.letter}</strong> : null}
                  <span className="option-text">{option.text}</span>
                </span>
              </label>
            ))}
          </fieldset>
        ) : null}

        {!isObjective && !hasOptions ? (
          <label className="essay-answer">
            <span className="essay-answer-label">Sua resposta</span>
            <textarea
              className="essay-answer-textarea"
              disabled={isReadOnly}
              onChange={(event) => onAnswerChange(event.target.value)}
              rows={8}
              value={typeof currentAnswer === 'string' ? currentAnswer : ''}
            />
          </label>
        ) : null}

        {!isObjective && hasOptions ? (
          <div className="multi-item-answers">
            {question.options.map((option) => (
              <label className="multi-item-row" key={option.id}>
                <span className="multi-item-prompt">
                  {option.letter ? <strong className="option-letter">{option.letter}</strong> : null}
                  <span className="option-text">{option.text}</span>
                </span>
                <input
                  className="multi-item-input"
                  disabled={isReadOnly}
                  onChange={(event) => handleMultiItemAnswerChange(option.id, event.target.value)}
                  type="text"
                  value={multiItemAnswers[option.id] ?? ''}
                />
              </label>
            ))}
          </div>
        ) : null}
      </section>

      {showEvaluation && evaluation ? (
        <section
          className={`question-evaluation${isLowScore ? ' question-evaluation--negative' : ''}`}
          aria-label="Correção da questão"
        >
          {shouldShowScore ? (
            <div className="question-evaluation__score">
              <span>Score</span>
              <strong>{Math.round(evaluation.score * 100)}%</strong>
            </div>
          ) : null}
          {evaluation.feedback ? (
            <div className="question-evaluation__feedback">
              <ReactMarkdown>{evaluation.feedback}</ReactMarkdown>
            </div>
          ) : null}
        </section>
      ) : null}
    </article>
  )
}
