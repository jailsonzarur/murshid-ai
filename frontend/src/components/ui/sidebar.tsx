import type { HTMLAttributes } from 'react'

import { cn } from '../../lib/cn'
import { Badge } from './badge'
import { Icon, type IconName } from './icon'

export type SidebarItem = {
  active?: boolean
  badge?: string | number
  disabled?: boolean
  icon: IconName
  label: string
  onSelect?: () => void
}

export type SidebarSection = {
  items: SidebarItem[]
  label: string
}

export type SidebarProps = HTMLAttributes<HTMLElement> & {
  brandLabel?: string
  brandSubtitle?: string
  items?: SidebarItem[]
  sections?: SidebarSection[]
}

const defaultSidebarItems: SidebarItem[] = [
  { label: 'Painel', icon: 'home', active: true },
  { label: 'Provas', icon: 'layers' },
  { label: 'Análises', icon: 'chart' },
  { label: 'Usuários', icon: 'users' },
  { label: 'Segurança', icon: 'shield' },
  { label: 'Configurações', icon: 'settings' },
]

export function Sidebar({
  brandLabel = 'IAsmim',
  brandSubtitle = 'OCR de provas',
  className,
  items = defaultSidebarItems,
  sections,
  ...props
}: SidebarProps) {
  const sidebarSections = sections ?? [{ label: 'Menu', items }]

  return (
    <aside className={cn('tasko-sidebar', className)} {...props}>
      <div className="tasko-sidebar__panel">
        <div className="tasko-sidebar__brand">
          <div className="tasko-sidebar__mark" aria-hidden="true">
            <Icon name="sparkles" size={18} />
          </div>
          <div className="tasko-sidebar__brand-copy">
            <p>{brandLabel}</p>
            <span>{brandSubtitle}</span>
          </div>
        </div>

        <div className="tasko-sidebar__sections">
          {sidebarSections.map((section) => (
            <div className="tasko-sidebar__section" key={section.label}>
              <p className="tasko-sidebar__section-label">{section.label}</p>
              <nav aria-label={section.label} className="tasko-sidebar__nav">
                {section.items.map((item) => (
                  <button
                    className={cn(
                      'tasko-sidebar__item',
                      item.active && 'tasko-sidebar__item--active',
                    )}
                    disabled={item.disabled}
                    key={item.label}
                    onClick={item.onSelect}
                    type="button"
                  >
                    <Icon name={item.icon} size={16} />
                    <span>{item.label}</span>
                    {item.badge ? (
                      <Badge className="tasko-sidebar__badge" tone="green">
                        {item.badge}
                      </Badge>
                    ) : null}
                  </button>
                ))}
              </nav>
            </div>
          ))}
        </div>
      </div>
    </aside>
  )
}
