import { Icon } from '../ui/icon'

type RecordingOrbProps = {
  isPaused: boolean
  isProcessing: boolean
  timerSeconds: number
}

function formatTimer(totalSeconds: number) {
  const hours = Math.floor(totalSeconds / 3600)
  const minutes = Math.floor((totalSeconds % 3600) / 60)
  const seconds = Math.floor(totalSeconds % 60)
  return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
}

const ORB_BASE_STYLE: React.CSSProperties = {
  position: 'relative',
  width: 168,
  height: 168,
  borderRadius: '50%',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  margin: '0 auto',
}

export function RecordingOrb({ isPaused, isProcessing, timerSeconds }: RecordingOrbProps) {
  const accent = isPaused ? 'oklch(70% 0.12 60)' : 'oklch(58% 0.22 25)'
  const accentSoft = isPaused ? 'oklch(70% 0.12 60 / 0.18)' : 'oklch(58% 0.22 25 / 0.18)'

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 24 }}>
      <div style={ORB_BASE_STYLE}>
        {!isPaused && (
          <>
            <span
              aria-hidden="true"
              style={{
                position: 'absolute',
                inset: -28,
                borderRadius: '50%',
                border: `1px solid ${accent}`,
                opacity: 0.28,
                animation: 'orb-ring 2.4s ease-out infinite',
              }}
            />
            <span
              aria-hidden="true"
              style={{
                position: 'absolute',
                inset: -14,
                borderRadius: '50%',
                border: `1px solid ${accent}`,
                opacity: 0.45,
                animation: 'orb-ring 2.4s ease-out infinite',
                animationDelay: '0.8s',
              }}
            />
          </>
        )}
        <div
          style={{
            width: '100%',
            height: '100%',
            borderRadius: '50%',
            background: `radial-gradient(circle at 35% 30%, ${accentSoft}, ${accent})`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: `0 16px 40px ${accentSoft}`,
            color: '#fff',
          }}
        >
          <Icon name={isPaused ? 'pause' : 'video'} size={48} strokeWidth={1.5} />
        </div>
      </div>

      <div style={{ display: 'flex', gap: 6, alignItems: 'center', justifyContent: 'center' }}>
        {Array.from({ length: 13 }).map((_, index) => (
          <span
            aria-hidden="true"
            key={index}
            style={{
              display: 'block',
              width: 3,
              height: isPaused ? 6 : 16,
              borderRadius: 2,
              background: accent,
              opacity: isPaused ? 0.4 : 0.6 + (index % 4) * 0.1,
              animation: isPaused ? 'none' : `wave 1.2s ease-in-out infinite`,
              animationDelay: `${(index % 7) * 0.09}s`,
            }}
          />
        ))}
      </div>

      <div style={{ textAlign: 'center' }}>
        <div
          style={{
            fontFamily: 'var(--mono)',
            fontSize: 32,
            fontWeight: 700,
            letterSpacing: '-0.02em',
            color: 'var(--ink)',
          }}
        >
          {formatTimer(timerSeconds)}
        </div>
        <div style={{ fontSize: 11.5, color: 'var(--ink-4)', marginTop: 2 }}>Tempo de gravação</div>
      </div>

      <div
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 6,
          padding: '6px 12px',
          borderRadius: 999,
          background: isProcessing ? 'var(--warn-soft)' : 'var(--ok-soft)',
          color: isProcessing ? 'var(--warn)' : 'var(--ok)',
          fontSize: 11.5,
          fontWeight: 600,
        }}
      >
        {isProcessing ? (
          <>
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
          </>
        ) : (
          <>
            <Icon name="check" size={11} strokeWidth={2.5} />
            Áudio sincronizado
          </>
        )}
      </div>

      <style>{`
        @keyframes orb-ring {
          0% { transform: scale(0.8); opacity: 0.55; }
          100% { transform: scale(1.5); opacity: 0; }
        }
        @keyframes wave {
          0%, 100% { transform: scaleY(0.4); }
          50% { transform: scaleY(1); }
        }
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  )
}
