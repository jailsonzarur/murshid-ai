import { useState } from 'react'
import { createPortal, flushSync } from 'react-dom'
import ReactMarkdown from 'react-markdown'

import { Icon } from '../ui/icon'

function slugify(value: string) {
  const slug = value
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')

  return slug || 'aula'
}

function formatNow() {
  return new Date().toLocaleString('pt-BR', {
    day: '2-digit',
    month: 'long',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

type SummaryPdfButtonProps = {
  durationLabel: string
  lectureTitle: string | null
  subjectName: string | null
  summary: string
  topicsCount: number
}

export function SummaryPdfButton({
  durationLabel,
  lectureTitle,
  subjectName,
  summary,
  topicsCount,
}: SummaryPdfButtonProps) {
  const [generatedAt, setGeneratedAt] = useState(formatNow)
  const title = lectureTitle ?? 'Aula sem título'

  const handleExportPdf = () => {
    const previousTitle = document.title

    flushSync(() => setGeneratedAt(formatNow()))

    const cleanup = () => {
      document.title = previousTitle
      document.body.classList.remove('printing-summary')
      window.removeEventListener('afterprint', cleanup)
    }

    document.title = `${slugify(title)}-resumo`
    document.body.classList.add('printing-summary')
    window.addEventListener('afterprint', cleanup)
    window.setTimeout(cleanup, 60000)
    window.print()
  }

  return (
    <>
      <button
        aria-label="Exportar o resumo da aula em PDF"
        className="btn btn-ghost btn-sm"
        onClick={handleExportPdf}
        title="Exportar o resumo da aula em PDF"
        type="button"
      >
        <Icon name="fileText" size={12} />
        <span>Exportar PDF</span>
      </button>

      {createPortal(
        <article id="summary-print-stage">
          <table className="summary-print-sheet">
            <thead>
              <tr>
                <td>
                  <div className="summary-print-gutter" />
                </td>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>
                  <header className="summary-print-head">
                    {subjectName ? <p className="summary-print-eyebrow">{subjectName}</p> : null}
                    <h1 className="summary-print-title">{title}</h1>
                    <p className="summary-print-meta">
                      <span>Duração {durationLabel}</span>
                      <span aria-hidden="true">·</span>
                      <span>
                        {topicsCount} {topicsCount === 1 ? 'tópico' : 'tópicos'}
                      </span>
                      <span aria-hidden="true">·</span>
                      <span>Exportado em {generatedAt}</span>
                    </p>
                  </header>

                  <div className="summary-print-body">
                    <ReactMarkdown>{summary}</ReactMarkdown>
                  </div>

                  <footer className="summary-print-foot">
                    Resumo gerado por IA a partir da transcrição da aula.
                  </footer>
                </td>
              </tr>
            </tbody>
            <tfoot>
              <tr>
                <td>
                  <div className="summary-print-gutter" />
                </td>
              </tr>
            </tfoot>
          </table>
        </article>,
        document.body,
      )}
    </>
  )
}
