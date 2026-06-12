import { useMemo } from 'react'

import { Card, CardContent } from '../ui/card'
import { Icon } from '../ui/icon'
import type { LectureEvent, LectureSegment } from '../../types/lecture'

type TimelineItem =
  | { kind: 'segment'; offset: number; segment: LectureSegment }
  | { kind: 'event'; offset: number; event: LectureEvent }

type TranscriptModalProps = {
  events: LectureEvent[]
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

function buildTxtExport(items: TimelineItem[], lectureTitle: string | null, subjectName: string | null) {
  const header = [
    lectureTitle ?? 'Aula sem título',
    subjectName ? `Matéria: ${subjectName}` : null,
    '',
  ]
    .filter((line) => line !== null)
    .join('\n')

  const body = items
    .map((item) => {
      const t = formatOffset(item.offset)
      if (item.kind === 'segment') {
        return `[${t}] ${item.segment.transcript}`
      }
      const prefix = item.event.type === 'ALERT' ? '⚠️ ' : '• '
      return `[${t}] ${prefix}${item.event.content}`
    })
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

export function TranscriptModal({ events, lectureTitle, onClose, segments, subjectName }: TranscriptModalProps) {
  const timeline = useMemo<TimelineItem[]>(() => {
    const items: TimelineItem[] = [
      ...segments.map<TimelineItem>((segment) => ({
        kind: 'segment',
        offset: segment.offset_seconds,
        segment,
      })),
      ...events.map<TimelineItem>((event) => ({
        kind: 'event',
        offset: event.offset_seconds,
        event,
      })),
    ]
    return items.sort((a, b) => {
      if (a.offset === b.offset) {
        if (a.kind === b.kind) return 0
        return a.kind === 'segment' ? -1 : 1
      }
      return a.offset - b.offset
    })
  }, [events, segments])

  function handleExport() {
    const filename = `${(lectureTitle ?? 'aula').replace(/[^a-z0-9-_]+/gi, '-').toLowerCase()}.txt`
    downloadTxt(buildTxtExport(timeline, lectureTitle, subjectName), filename)
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
          {timeline.length === 0 ? (
            <p style={{ fontSize: 13.5, color: 'var(--ink-4)' }}>
              Esta aula ainda não tem segmentos transcritos.
            </p>
          ) : (
            <div>
              {timeline.map((item, index) => {
                const t = formatOffset(item.offset)
                if (item.kind === 'event') {
                  const isAlert = item.event.type === 'ALERT'
                  return (
                    <div
                      key={`evt-${item.event.id}`}
                      style={{
                        display: 'grid',
                        gridTemplateColumns: '64px 1fr',
                        gap: 12,
                        padding: '10px 0',
                        borderBottom: index === timeline.length - 1 ? 'none' : '1px dashed var(--line)',
                      }}
                    >
                      <span style={{ fontFamily: 'var(--mono)', fontSize: 12, fontWeight: 600, color: isAlert ? 'var(--warn)' : 'var(--ink-4)' }}>
                        {t}
                      </span>
                      <span
                        style={{
                          fontSize: 13.5,
                          fontWeight: isAlert ? 600 : 500,
                          color: isAlert ? 'oklch(45% 0.1 60)' : 'var(--ink-2)',
                          lineHeight: 1.5,
                        }}
                      >
                        {isAlert ? '⚠️ ' : '• '}{item.event.content}
                      </span>
                    </div>
                  )
                }
                return (
                  <div
                    key={`seg-${item.segment.id}`}
                    style={{
                      display: 'grid',
                      gridTemplateColumns: '64px 1fr',
                      gap: 12,
                      padding: '10px 0',
                      borderBottom: index === timeline.length - 1 ? 'none' : '1px dashed var(--line)',
                    }}
                  >
                    <span style={{ fontFamily: 'var(--mono)', fontSize: 12, fontWeight: 600, color: 'var(--ink-4)' }}>
                      {t}
                    </span>
                    <span style={{ fontSize: 13.5, color: 'var(--ink-2)', lineHeight: 1.5 }}>
                      {item.segment.transcript}
                    </span>
                  </div>
                )
              })}
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
            disabled={timeline.length === 0}
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
