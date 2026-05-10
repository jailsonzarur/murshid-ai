import { Button } from '../ui/button'
import { Card } from '../ui/card'
import { Icon } from '../ui/icon'

export function MobileAppCard() {
  return (
    <Card className="tasko-dark-card tasko-mobile-card">
      <div className="tasko-wave" aria-hidden="true" />
      <div className="tasko-dark-card__content">
        <Icon name="smartphone" size={24} />
        <h2>Download our Mobile App</h2>
        <p>Get easy in another way</p>

        <div className="tasko-store-buttons">
          <Button variant="secondary">
            <Icon name="apple" size={18} />
            <span>
              <small>Download on the</small>
              App Store
            </span>
          </Button>
          <Button variant="secondary">
            <Icon name="creditCard" size={18} />
            <span>
              <small>Get it on</small>
              Google Play
            </span>
          </Button>
        </div>
      </div>
    </Card>
  )
}
