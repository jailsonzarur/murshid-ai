import { useEffect, useRef, useState } from 'react'

const FADE_MS = 400

type Entry = {
  key: number
  text: string
  state: 'in' | 'out'
}

type InsightTickerProps = {
  insight: string | null
}

export function InsightTicker({ insight }: InsightTickerProps) {
  const [entries, setEntries] = useState<Entry[]>([])
  const counterRef = useRef(0)
  const lastInsightRef = useRef<string | null>(null)

  useEffect(() => {
    if (!insight || insight === lastInsightRef.current) return
    lastInsightRef.current = insight

    const newKey = ++counterRef.current

    setEntries((current) => {
      const dimmed = current.map<Entry>((entry) => ({ ...entry, state: 'out' }))
      return [...dimmed, { key: newKey, text: insight, state: 'in' }]
    })

    const removalTimer = window.setTimeout(() => {
      setEntries((current) => current.filter((entry) => entry.key === newKey))
    }, FADE_MS + 50)

    return () => window.clearTimeout(removalTimer)
  }, [insight])

  return (
    <div
      style={{
        position: 'relative',
        width: '100%',
        maxWidth: 520,
        minHeight: 86,
        margin: '0 auto',
      }}
    >
      {entries.length === 0 ? (
        <div
          style={{
            opacity: 0.55,
            textAlign: 'center',
            fontSize: 13,
            color: 'var(--ink-4)',
            fontStyle: 'italic',
            padding: '20px 16px',
          }}
        >
          Aguardando o primeiro insight da aula...
        </div>
      ) : (
        entries.map((entry) => (
          <div
            key={entry.key}
            style={{
              position: 'absolute',
              inset: 0,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              padding: '16px 22px',
              borderRadius: 14,
              background: 'oklch(99% 0.005 270 / 0.7)',
              border: '1px solid var(--line)',
              boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
              fontSize: 14,
              color: 'var(--ink-2)',
              lineHeight: 1.5,
              textAlign: 'center',
              animation: entry.state === 'in'
                ? `insight-in ${FADE_MS}ms ease-out forwards`
                : `insight-out ${FADE_MS}ms ease-in forwards`,
              backdropFilter: 'blur(4px)',
              WebkitBackdropFilter: 'blur(4px)',
            }}
          >
            {entry.text}
          </div>
        ))
      )}
      <style>{`
        @keyframes insight-in {
          from { opacity: 0; transform: translateY(10px); }
          to   { opacity: 1; transform: translateY(0); }
        }
        @keyframes insight-out {
          from { opacity: 1; transform: translateY(0); }
          to   { opacity: 0; transform: translateY(-10px); }
        }
      `}</style>
    </div>
  )
}
