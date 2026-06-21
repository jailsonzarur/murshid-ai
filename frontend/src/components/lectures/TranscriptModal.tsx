import { useMemo } from 'react'

import type { LectureSegment } from '../../types/lecture'
import { Card, CardContent } from '../ui/card'
import { Icon } from '../ui/icon'

type TranscriptModalProps = {
  lectureTitle: string | null
  onClose: () => void
  segments: LectureSegment[]
  subjectName: string | null
}

function formatOffset(totalSeconds: number) {
  const hours = Math.floor(totalSeconds / 3600)
  const minutes = Math.floor((totalSeconds % 3600) / 60)
  const seconds = Math.floor(totalSeconds % 60)
  if (hours > 0) {
    return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
  }
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
}

function buildTxtExport(segments: LectureSegment[], lectureTitle: string | null, subjectName: string | null) {
  const header = [
    lectureTitle ?? 'Aula sem título',
    subjectName ? `Matéria: ${subjectName}` : null,
    '',
  ]
    .filter((line) => line !== null)
    .join('\n')

  const body = segments
    .map((segment) => `[${formatOffset(segment.offset_seconds)}] ${segment.transcript}`)
    .join('\n\n')

  return `${header}\n${body}\n`
}

function downloadTxt(content: string, filename: string) {
  const blob = new Blob([content], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  document.body.appendChild(anchor)
  anchor.click()
  document.body.removeChild(anchor)
  URL.revokeObjectURL(url)
}

export function TranscriptModal({ lectureTitle, onClose, segments, subjectName }: TranscriptModalProps) {
  const orderedSegments = useMemo(() => {
    return [...segments].sort((a, b) => a.offset_seconds - b.offset_seconds)
  }, [segments])

  function handleExport() {
    const filename = `${(lectureTitle ?? 'aula').replace(/[^a-z0-9-_]+/gi, '-').toLowerCase()}.txt`
    downloadTxt(buildTxtExport(orderedSegments, lectureTitle, subjectName), filename)
  }

  return (
    <div className="modal-backdrop" role="presentation">
      <Card style={{ maxWidth: 640, width: '100%', maxHeight: '85vh', display: 'flex', flexDirection: 'column' }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'flex-start',
            justifyContent: 'space-between',
            gap: 12,
            padding: '20px 22px 12px',
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
              <h2 style={{ margin: 0, fontSize: 16, fontWeight: 700 }}>Transcrição completa</h2>
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

        <CardContent style={{ overflowY: 'auto', padding: '12px 22px 18px', flex: 1 }}>
          {orderedSegments.length === 0 ? (
            <p style={{ fontSize: 13.5, color: 'var(--ink-4)' }}>
              Esta aula ainda não tem segmentos transcritos.
            </p>
          ) : (
            <div>
              {orderedSegments.map((segment, index) => (
                <div
                  key={`seg-${segment.id}`}
                  style={{
                    display: 'grid',
                    gridTemplateColumns: '64px 1fr',
                    gap: 12,
                    padding: '10px 0',
                    borderBottom: index === orderedSegments.length - 1 ? 'none' : '1px dashed var(--line)',
                  }}
                >
                  <span style={{ fontFamily: 'var(--mono)', fontSize: 12, fontWeight: 600, color: 'var(--ink-4)' }}>
                    {formatOffset(segment.offset_seconds)}
                  </span>
                  <span style={{ fontSize: 13.5, color: 'var(--ink-2)', lineHeight: 1.5 }}>
                    {segment.transcript}
                  </span>
                </div>
              ))}
            </div>
          )}
        </CardContent>

        <div
          style={{
            display: 'flex',
            justifyContent: 'flex-end',
            gap: 8,
            padding: '12px 22px 18px',
            borderTop: '1px solid var(--line)',
          }}
        >
          <button className="btn btn-ghost" onClick={onClose} type="button">
            Fechar
          </button>
          <button
            className="btn btn-primary"
            disabled={orderedSegments.length === 0}
            onClick={handleExport}
            type="button"
          >
            <Icon name="upload" size={14} />
            <span>Exportar .txt</span>
          </button>
        </div>
      </Card>
    </div>
  )
}
