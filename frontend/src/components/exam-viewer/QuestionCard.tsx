import type { Question, QuestionAnswer } from '../../types/exam'

type QuestionCardProps = {
  currentAnswer?: QuestionAnswer
  onAnswerChange: (answer: QuestionAnswer) => void
  question: Question
}

function getMultiItemAnswers(currentAnswer?: QuestionAnswer) {
  if (!currentAnswer || typeof currentAnswer === 'string') {
    return {}
  }

  return currentAnswer
}

export function QuestionCard({ currentAnswer, onAnswerChange, question }: QuestionCardProps) {
  const isObjective = question.type === 'OBJECTIVE'
  const hasOptions = question.options.length > 0
  const multiItemAnswers = getMultiItemAnswers(currentAnswer)

  function handleMultiItemAnswerChange(optionId: string, answer: string) {
    onAnswerChange({
      ...multiItemAnswers,
      [optionId]: answer,
    })
  }

  return (
    <article className="question-card">
      <header className="question-header">
        <span>{question.type === 'OBJECTIVE' ? 'Múltipla escolha' : 'Resposta aberta'}</span>
        <h3 className="question-statement">{question.statement}</h3>
      </header>

      {question.image_url ? (
        <img alt="Imagem relacionada à questão" className="question-image" src={question.image_url} />
      ) : null}

      <section className="question-interaction" aria-label="Área de resposta">
        {isObjective && hasOptions ? (
          <fieldset className="answer-options">
            <legend className="answer-options-title">Selecione uma resposta</legend>
            {question.options.map((option) => (
              <label className="option-row" key={option.id}>
                <input
                  checked={currentAnswer === option.id}
                  className="option-radio"
                  name={`question-${question.id}`}
                  onChange={() => onAnswerChange(option.id)}
                  type="radio"
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
                  onChange={(event) => handleMultiItemAnswerChange(option.id, event.target.value)}
                  type="text"
                  value={multiItemAnswers[option.id] ?? ''}
                />
              </label>
            ))}
          </div>
        ) : null}
      </section>
    </article>
  )
}
