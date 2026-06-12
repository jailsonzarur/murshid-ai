import { Card, CardContent } from '../ui/card'
import { Icon } from '../ui/icon'

type ExitConfirmModalProps = {
  isBusy: boolean
  onCancel: () => void
  onDiscard: () => void
  onPauseAndExit: () => void
}

export function ExitConfirmModal({ isBusy, onCancel, onDiscard, onPauseAndExit }: ExitConfirmModalProps) {
  return (
    <div className="modal-backdrop" role="presentation">
      <Card style={{ maxWidth: 480, width: '100%' }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'flex-start',
            gap: 12,
            padding: '20px 22px 8px',
          }}
        >
          <div
            aria-hidden="true"
            style={{
              width: 40,
              height: 40,
              borderRadius: 10,
              background: 'var(--warn-soft)',
              color: 'var(--warn)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
            }}
          >
            <Icon name="alertTriangle" size={18} />
          </div>
          <div>
            <h2 style={{ margin: 0, fontSize: 16, fontWeight: 700 }}>Sair da gravação</h2>
            <p style={{ margin: '4px 0 0', fontSize: 13, color: 'var(--ink-3)', lineHeight: 1.5 }}>
              Você pode pausar a aula para retomar mais tarde ou descartar tudo o que foi capturado
              até agora.
            </p>
          </div>
        </div>

        <CardContent>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <button
              className="btn btn-primary"
              disabled={isBusy}
              onClick={onPauseAndExit}
              style={{ justifyContent: 'flex-start' }}
              type="button"
            >
              <Icon name="pause" size={14} />
              <span>Salvar como pausada</span>
            </button>
            <button
              className="btn btn-danger"
              disabled={isBusy}
              onClick={onDiscard}
              style={{ justifyContent: 'flex-start' }}
              type="button"
            >
              <Icon name="trash" size={14} />
              <span>Descartar aula</span>
            </button>
            <button
              className="btn btn-ghost"
              disabled={isBusy}
              onClick={onCancel}
              style={{ justifyContent: 'flex-start' }}
              type="button"
            >
              <Icon name="x" size={14} />
              <span>Cancelar</span>
            </button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
