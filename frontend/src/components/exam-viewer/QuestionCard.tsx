import ReactMarkdown from 'react-markdown'

import { Icon } from '../ui/icon'
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
    <>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16, flexWrap: 'wrap' }}>
        <span className="q-type">
          {isObjectiveMulti
            ? 'Múltipla seleção'
            : isObjective
              ? 'Múltipla escolha'
              : 'Resposta aberta'}
        </span>
      </div>

      <h3 className="q-stem">{question.statement}</h3>

      {question.image_url ? (
        <img alt="Imagem relacionada à questão" className="question-image" src={question.image_url} />
      ) : null}

      {isObjective && hasOptions ? (
        <div
          className="options"
          role={isObjectiveMulti ? 'group' : 'radiogroup'}
          aria-label={isObjectiveMulti ? 'Selecione uma ou mais respostas' : 'Selecione uma resposta'}
        >
          {question.options.map((option, optionIndex) => {
            const isSelected = objectiveAnswers.includes(option.id)
            return (
              <button
                aria-checked={isSelected}
                className={`option${isSelected ? ' selected' : ''}`}
                disabled={isReadOnly}
                key={option.id}
                onClick={() => handleObjectiveAnswerChange(option.id, !isSelected)}
                role={isObjectiveMulti ? 'checkbox' : 'radio'}
                type="button"
              >
                <span className="option-letter">
                  {option.letter ?? String.fromCharCode(65 + optionIndex)}
                </span>
                <span className="option-text">{option.text}</span>
                <span aria-hidden="true" className="option-radio" />
              </button>
            )
          })}
        </div>
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

      {showEvaluation && evaluation ? (
        <section
          aria-label="Correção da questão"
          className={`question-evaluation${isLowScore ? ' question-evaluation--negative' : ''}`}
        >
          <div className="question-evaluation__header">
            <div className="question-evaluation__label">
              <Icon name="sparkles" size={12} />
              Comentário pedagógico
            </div>
            {shouldShowScore ? (
              <div className="question-evaluation__score-chip">
                {Math.round(evaluation.score * 100)}%
              </div>
            ) : null}
          </div>
          {evaluation.feedback ? (
            <div className="question-evaluation__feedback">
              <ReactMarkdown>{evaluation.feedback}</ReactMarkdown>
            </div>
          ) : null}
        </section>
      ) : null}
    </>
  )
}
