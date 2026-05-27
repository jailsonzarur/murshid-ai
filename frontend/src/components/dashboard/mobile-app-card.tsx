import { Button } from '../ui/button'
import { Card } from '../ui/card'
import { Icon } from '../ui/icon'

export function MobileAppCard() {
  return (
    <Card className="widget-dark">
      <div className="widget-dark__wave" aria-hidden="true" />
      <div style={{ padding: '22px', position: 'relative', zIndex: 1 }}>
        <Icon name="smartphone" size={24} />
        <h2>Baixe nosso aplicativo</h2>
        <p>Acesse seus fluxos de outra forma.</p>

        <div className="widget-dark__actions" style={{ flexWrap: 'wrap' }}>
          <Button variant="secondary">
            <Icon name="apple" size={18} />
            <span>
              <small>Baixar na</small>
              App Store
            </span>
          </Button>
          <Button variant="secondary">
            <Icon name="creditCard" size={18} />
            <span>
              <small>Disponível no</small>
              Google Play
            </span>
          </Button>
        </div>
      </div>
    </Card>
  )
}
