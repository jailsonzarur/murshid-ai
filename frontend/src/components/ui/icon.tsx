import {
  AlertTriangle,
  Apple,
  ArrowLeft,
  ArrowRight,
  ArrowUpRight,
  BarChart3,
  Bell,
  Calendar,
  Check,
  CheckCircle2,
  ChevronDown,
  Clock,
  Command,
  CreditCard,
  Eye,
  FileText,
  Filter,
  HelpCircle,
  Home,
  Layers,
  ListChecks,
  LockKeyhole,
  LogOut,
  Mail,
  Menu,
  MessageSquare,
  MoreHorizontal,
  Pause,
  Plus,
  Search,
  Settings,
  ShieldCheck,
  Smartphone,
  Sparkles,
  Square,
  Tag,
  Trash2,
  TrendingUp,
  Upload,
  User,
  Users,
  Video,
  X,
  type LucideIcon,
  type LucideProps,
} from 'lucide-react'

import { cn } from '../../lib/cn'

const iconComponents = {
  alertTriangle: AlertTriangle,
  apple: Apple,
  arrowLeft: ArrowLeft,
  arrowRight: ArrowRight,
  arrowUpRight: ArrowUpRight,
  bell: Bell,
  calendar: Calendar,
  chart: BarChart3,
  check: Check,
  checkCircle: CheckCircle2,
  chevronDown: ChevronDown,
  clock: Clock,
  command: Command,
  creditCard: CreditCard,
  eye: Eye,
  fileText: FileText,
  filter: Filter,
  helpCircle: HelpCircle,
  home: Home,
  layers: Layers,
  listChecks: ListChecks,
  lock: LockKeyhole,
  logOut: LogOut,
  mail: Mail,
  menu: Menu,
  message: MessageSquare,
  more: MoreHorizontal,
  pause: Pause,
  plus: Plus,
  search: Search,
  settings: Settings,
  shield: ShieldCheck,
  smartphone: Smartphone,
  sparkles: Sparkles,
  square: Square,
  tag: Tag,
  trash: Trash2,
  trendingUp: TrendingUp,
  upload: Upload,
  user: User,
  users: Users,
  video: Video,
  x: X,
} satisfies Record<string, LucideIcon>

export type IconName = keyof typeof iconComponents

export type IconProps = Omit<LucideProps, 'name'> & {
  name: IconName
}

export function Icon({
  name,
  size = 16,
  className,
  strokeWidth = 2,
  style,
  ...props
}: IconProps) {
  const LucideIconComponent = iconComponents[name]

  return (
    <LucideIconComponent
      aria-hidden="true"
      className={cn('ui-icon', className)}
      size={size}
      strokeWidth={strokeWidth}
      style={{ flexShrink: 0, ...style }}
      {...props}
    />
  )
}
