import ReactMarkdown from 'react-markdown'

import { Card, CardContent } from '../ui/card'
import { Icon } from '../ui/icon'

type SummaryModalProps = {
  lectureTitle: string | null
  onClose: () => void
  subjectName: string | null
  summary: string
}

export function SummaryModal({ lectureTitle, onClose, subjectName, summary }: SummaryModalProps) {
  return (
    <div className="modal-backdrop" role="presentation">
      <Card style={{ maxWidth: 760, width: '100%', maxHeight: '88vh', display: 'flex', flexDirection: 'column' }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'flex-start',
            justifyContent: 'space-between',
            gap: 12,
            padding: '20px 24px 12px',
            borderBottom: '1px solid var(--line)',
          }}
        >
          <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
            <div
              aria-hidden="true"
              className="avatar avatar-blue"
              style={{ width: 40, height: 40, borderRadius: 10 }}
            >
              <Icon name="fileText" size={18} />
            </div>
            <div>
              <h2 style={{ margin: 0, fontSize: 16, fontWeight: 700 }}>Resumo da aula</h2>
              <div style={{ fontSize: 12.5, color: 'var(--ink-4)', marginTop: 2 }}>
                {lectureTitle ?? 'Aula sem título'}
                {subjectName ? ` · ${subjectName}` : ''}
              </div>
            </div>
          </div>
          <button aria-label="Fechar modal" className="icon-btn" onClick={onClose} type="button">
            <Icon name="x" size={16} />
          </button>
        </div>

        <CardContent style={{ overflowY: 'auto', padding: '20px 28px 24px', flex: 1 }}>
          <div
            style={{
              fontSize: 14.5,
              lineHeight: 1.7,
              color: 'var(--ink-2)',
            }}
          >
            <ReactMarkdown>{summary}</ReactMarkdown>
          </div>
        </CardContent>

        <div
          style={{
            display: 'flex',
            justifyContent: 'flex-end',
            padding: '12px 24px 18px',
            borderTop: '1px solid var(--line)',
          }}
        >
          <button className="btn btn-ghost" onClick={onClose} type="button">
            Fechar
          </button>
        </div>
      </Card>
    </div>
  )
}
