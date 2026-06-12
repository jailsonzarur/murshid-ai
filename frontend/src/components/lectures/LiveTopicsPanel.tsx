import { useEffect, useMemo, useRef } from 'react'

import type { LectureEvent } from '../../types/lecture'
import { Icon } from '../ui/icon'

type LiveTopicsPanelProps = {
  events: LectureEvent[]
  isProcessing: boolean
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

export function LiveTopicsPanel({ events, isProcessing }: LiveTopicsPanelProps) {
  const scrollRef = useRef<HTMLDivElement | null>(null)

  const orderedEvents = useMemo(() => {
    return [...events].sort((a, b) => {
      if (a.offset_seconds === b.offset_seconds) return a.sequence - b.sequence
      return a.offset_seconds - b.offset_seconds
    })
  }, [events])

  const currentTopicId = useMemo(() => {
    for (let index = orderedEvents.length - 1; index >= 0; index -= 1) {
      if (orderedEvents[index].type === 'TOPIC') return orderedEvents[index].id
    }
    return null
  }, [orderedEvents])

  const topicCount = orderedEvents.filter((event) => event.type === 'TOPIC').length

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [orderedEvents.length, isProcessing])

  return (
    <div
      style={{
        background: 'var(--card-bg, #fff)',
        border: '1px solid var(--line)',
        borderRadius: 14,
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        height: '100%',
        minHeight: 480,
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '14px 18px',
          borderBottom: '1px solid var(--line)',
        }}
      >
        <h3 style={{ margin: 0, fontSize: 14, fontWeight: 700, letterSpacing: '-0.01em' }}>
          Tópicos detectados
        </h3>
        <span
          style={{
            fontSize: 11,
            fontWeight: 700,
            padding: '3px 9px',
            borderRadius: 999,
            background: 'var(--accent-softer)',
            color: 'var(--accent)',
          }}
        >
          {topicCount}
        </span>
      </div>

      {orderedEvents.length === 0 && !isProcessing ? (
        <div
          style={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 12,
            padding: 24,
            textAlign: 'center',
          }}
        >
          <div
            aria-hidden="true"
            style={{
              width: 64,
              height: 64,
              borderRadius: '50%',
              background: 'var(--bg-sunken)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--ink-4)',
            }}
          >
            <Icon name="listChecks" size={28} />
          </div>
          <div>
            <h4 style={{ margin: 0, fontSize: 14, fontWeight: 700 }}>Ouvindo a aula...</h4>
            <p style={{ margin: '6px 0 0', fontSize: 12.5, color: 'var(--ink-4)' }}>
              Os tópicos da sua aula aparecerão aqui conforme o professor avança.
            </p>
          </div>
        </div>
      ) : (
        <div
          ref={scrollRef}
          style={{
            flex: 1,
            overflowY: 'auto',
            padding: 14,
            display: 'flex',
            flexDirection: 'column',
            gap: 10,
          }}
        >
          {orderedEvents.map((event) => {
            const isAlert = event.type === 'ALERT'
            const isCurrent = event.id === currentTopicId
            return (
              <div
                key={event.id}
                style={{
                  display: 'grid',
                  gridTemplateColumns: '52px 1fr',
                  gap: 10,
                  alignItems: 'flex-start',
                }}
              >
                <span
                  style={{
                    fontFamily: 'var(--mono)',
                    fontSize: 11.5,
                    fontWeight: 600,
                    color: isAlert ? 'var(--warn)' : 'var(--ink-4)',
                    paddingTop: 6,
                  }}
                >
                  {formatOffset(event.offset_seconds)}
                </span>
                {isAlert ? (
                  <div
                    style={{
                      background: 'var(--warn-soft)',
                      border: '1px solid oklch(82% 0.10 72)',
                      borderRadius: 10,
                      padding: '10px 12px',
                      display: 'flex',
                      gap: 10,
                    }}
                  >
                    <span
                      aria-hidden="true"
                      style={{ color: 'var(--warn)', flexShrink: 0, marginTop: 2 }}
                    >
                      <Icon name="alertTriangle" size={16} />
                    </span>
                    <div style={{ minWidth: 0 }}>
                      <div style={{ fontSize: 10.5, fontWeight: 700, color: 'var(--warn)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                        Cai na prova
                      </div>
                      <div style={{ fontSize: 13.5, color: 'oklch(40% 0.08 60)', fontWeight: 600, marginTop: 2 }}>
                        "{event.content}"
                      </div>
                    </div>
                  </div>
                ) : (
                  <div
                    style={
                      isCurrent
                        ? {
                            background: 'var(--accent-softer)',
                            border: '1px solid var(--accent-soft)',
                            borderRadius: 10,
                            padding: '8px 12px',
                          }
                        : { padding: '6px 0' }
                    }
                  >
                    <div style={{ fontSize: 13.5, fontWeight: isCurrent ? 600 : 500, color: 'var(--ink)' }}>
                      {event.content}
                    </div>
                    {isCurrent && (
                      <div
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: 5,
                          marginTop: 4,
                          fontSize: 10.5,
                          fontWeight: 700,
                          color: 'var(--accent)',
                          textTransform: 'uppercase',
                          letterSpacing: '0.06em',
                        }}
                      >
                        <span
                          aria-hidden="true"
                          style={{
                            width: 6,
                            height: 6,
                            borderRadius: '50%',
                            background: 'var(--accent)',
                            animation: 'pulse 1.4s ease-in-out infinite',
                          }}
                        />
                        Tópico atual
                      </div>
                    )}
                  </div>
                )}
              </div>
            )
          })}

          {isProcessing && (
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: '52px 1fr',
                gap: 10,
                alignItems: 'flex-start',
              }}
            >
              <span
                style={{
                  fontFamily: 'var(--mono)',
                  fontSize: 11.5,
                  fontWeight: 600,
                  color: 'var(--ink-4)',
                  paddingTop: 6,
                }}
              >
                ...
              </span>
              <div
                style={{
                  background: 'var(--bg-sunken)',
                  borderRadius: 10,
                  padding: '10px 12px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  color: 'var(--ink-4)',
                  fontSize: 12.5,
                  fontWeight: 500,
                }}
              >
                <span
                  aria-hidden="true"
                  style={{
                    width: 10,
                    height: 10,
                    borderRadius: '50%',
                    border: '2px solid currentColor',
                    borderTopColor: 'transparent',
                    animation: 'spin 0.9s linear infinite',
                    display: 'inline-block',
                  }}
                />
                Processando segmento...
              </div>
            </div>
          )}

          <style>{`
            @keyframes pulse {
              0%, 100% { opacity: 1; }
              50% { opacity: 0.35; }
            }
          `}</style>
        </div>
      )}
    </div>
  )
}
