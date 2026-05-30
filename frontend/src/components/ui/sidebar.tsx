import type { HTMLAttributes } from 'react'

import { cn } from '../../lib/cn'
import { Icon, type IconName } from './icon'

export type SidebarItem = {
  active?: boolean
  badge?: string | number
  disabled?: boolean
  icon: IconName
  label: string
  onSelect?: () => void | Promise<void>
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
  brandLabel = 'Murshid',
  brandSubtitle = 'Plataforma de estudo',
  className,
  items = defaultSidebarItems,
  sections,
  ...props
}: SidebarProps) {
  const sidebarSections = sections ?? [{ label: 'Menu', items }]

  return (
    <aside className={cn('sidebar', className)} {...props}>
      <div className="brand">
        <div className="brand-mark" aria-hidden="true">
          <Icon name="sparkles" size={16} />
        </div>
        <div>
          <p className="brand-name">{brandLabel}</p>
          <p className="brand-sub">{brandSubtitle}</p>
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '18px', flex: 1 }}>
        {sidebarSections.map((section) => (
          <div className="nav-section" key={section.label}>
            <p className="nav-section-label">{section.label}</p>
            <nav aria-label={section.label}>
              {section.items.map((item) => (
                <button
                  className={cn('nav-item', item.active && 'active')}
                  disabled={item.disabled}
                  key={item.label}
                  onClick={item.onSelect}
                  type="button"
                >
                  <Icon className="ico" name={item.icon} size={16} />
                  <span>{item.label}</span>
                  {item.badge !== undefined ? (
                    <span className="nav-count">{item.badge}</span>
                  ) : null}
                </button>
              ))}
            </nav>
          </div>
        ))}
      </div>
    </aside>
  )
}
