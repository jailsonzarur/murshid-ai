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

export function RecordingOrb({ isPaused, isProcessing, timerSeconds }: RecordingOrbProps) {
  const accent = isPaused ? 'oklch(70% 0.13 60)' : 'oklch(58% 0.22 25)'
  const accentSoft = isPaused ? 'oklch(70% 0.13 60 / 0.18)' : 'oklch(58% 0.22 25 / 0.22)'

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 28 }}>
      <div
        style={{
          position: 'relative',
          width: 200,
          height: 200,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        {!isPaused && (
          <>
            <span
              aria-hidden="true"
              style={{
                position: 'absolute',
                inset: -36,
                borderRadius: '50%',
                border: `1px solid ${accent}`,
                opacity: 0.2,
                animation: 'orb-ring 2.6s ease-out infinite',
              }}
            />
            <span
              aria-hidden="true"
              style={{
                position: 'absolute',
                inset: -20,
                borderRadius: '50%',
                border: `1px solid ${accent}`,
                opacity: 0.35,
                animation: 'orb-ring 2.6s ease-out infinite',
                animationDelay: '0.6s',
              }}
            />
            <span
              aria-hidden="true"
              style={{
                position: 'absolute',
                inset: -8,
                borderRadius: '50%',
                border: `1px solid ${accent}`,
                opacity: 0.5,
                animation: 'orb-ring 2.6s ease-out infinite',
                animationDelay: '1.2s',
              }}
            />
          </>
        )}
        <div
          style={{
            width: '100%',
            height: '100%',
            borderRadius: '50%',
            background: `radial-gradient(circle at 32% 28%, oklch(98% 0.005 270 / 0.95), ${accentSoft} 55%, ${accent})`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: `0 20px 50px ${accentSoft}, inset 0 -8px 24px oklch(0% 0 0 / 0.15)`,
            color: '#fff',
          }}
        >
          <Icon name={isPaused ? 'pause' : 'video'} size={64} strokeWidth={1.4} />
        </div>
      </div>

      <div style={{ display: 'flex', gap: 6, alignItems: 'center', justifyContent: 'center', height: 24 }}>
        {Array.from({ length: 15 }).map((_, index) => (
          <span
            aria-hidden="true"
            key={index}
            style={{
              display: 'block',
              width: 3,
              height: isPaused ? 6 : 18,
              borderRadius: 2,
              background: accent,
              opacity: isPaused ? 0.35 : 0.55 + (index % 4) * 0.1,
              animation: isPaused ? 'none' : 'orb-wave 1.2s ease-in-out infinite',
              animationDelay: `${(index % 7) * 0.09}s`,
            }}
          />
        ))}
      </div>

      <div style={{ textAlign: 'center' }}>
        <div
          style={{
            fontFamily: 'var(--mono)',
            fontSize: 40,
            fontWeight: 700,
            letterSpacing: '-0.02em',
            color: 'var(--ink)',
            lineHeight: 1,
          }}
        >
          {formatTimer(timerSeconds)}
        </div>
        <div style={{ fontSize: 11.5, color: 'var(--ink-4)', marginTop: 6, fontWeight: 500 }}>
          Tempo de gravação
        </div>
      </div>

      <div
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 7,
          padding: '6px 13px',
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
                animation: 'orb-spin 0.9s linear infinite',
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
          0%   { transform: scale(0.85); opacity: 0.55; }
          100% { transform: scale(1.6); opacity: 0; }
        }
        @keyframes orb-wave {
          0%, 100% { transform: scaleY(0.35); }
          50%      { transform: scaleY(1); }
        }
        @keyframes orb-spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  )
}
