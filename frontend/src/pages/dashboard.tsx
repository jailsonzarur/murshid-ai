import { useEffect, useState } from 'react'

import { MobileAppCard } from '../components/dashboard/mobile-app-card'
import { ProjectAnalytics } from '../components/dashboard/project-analytics'
import { ProjectList } from '../components/dashboard/project-list'
import { ProjectProgress } from '../components/dashboard/project-progress'
import { Reminders } from '../components/dashboard/reminders'
import { StatsCards } from '../components/dashboard/stats-cards'
import { TeamCollaboration } from '../components/dashboard/team-collaboration'
import { TimeTracker } from '../components/dashboard/time-tracker'
import { AppShell } from '../components/layout/app-shell'
import { Button } from '../components/ui/button'
import { ApiError, getProfile, type UserProfileResponseData } from '../lib/api'
import { getAccessToken, getAuthProfile, saveAuthProfile } from '../lib/auth'
import { navigateTo } from '../lib/navigation'

const dashboardStats = [
  {
    icon: 'fileText' as const,
    label: 'Total de provas',
    subtitle: 'Aumento em relação ao mês passado.',
    tone: 'primary' as const,
    value: '128',
  },
  {
    icon: 'checkCircle' as const,
    label: 'Provas concluídas',
    subtitle: 'Aumento em relação ao mês passado.',
    value: '99,2%',
  },
  {
    icon: 'clock' as const,
    label: 'Provas em processamento',
    subtitle: 'Aumento em relação ao mês passado.',
    value: '06',
  },
  {
    icon: 'shield' as const,
    label: 'Provas pendentes',
    subtitle: 'Em análise.',
    value: '2',
  },
]

const weeklyActivity = [
  { day: 'D', label: 'Domingo', value: 45 },
  { day: 'S', label: 'Segunda-feira', value: 75 },
  { day: 'T', label: 'Terça-feira', value: 74 },
  { day: 'Q', label: 'Quarta-feira', value: 92 },
  { day: 'Q', label: 'Quinta-feira', value: 35 },
  { day: 'S', label: 'Sexta-feira', value: 60 },
  { day: 'S', label: 'Sábado', value: 50 },
]

const collaborationItems = [
  {
    initials: 'CM',
    name: 'Clínica Médica',
    status: 'Concluída',
    task: 'Residência Clínica Médica 2026',
    tone: 'green' as const,
  },
  {
    initials: 'CB',
    name: 'Cardiologia B',
    status: 'Em andamento',
    task: 'Simulado Cardiologia - Turma B',
    tone: 'orange' as const,
  },
  {
    initials: 'IF',
    name: 'Infectologia',
    status: 'Pendente',
    task: 'Banco de questões Infectologia',
    tone: 'destructive' as const,
  },
  {
    initials: 'RX',
    name: 'Revisão OCR',
    status: 'Em andamento',
    task: 'Validação de alternativas',
    tone: 'orange' as const,
  },
]

const projectItems = [
  { date: 'Mai 10, 2026', icon: '+', name: 'Upload de prova', tone: 'blue' as const },
  { date: 'Mai 10, 2026', icon: '~', name: 'Processamento OCR', tone: 'cyan' as const },
  { date: 'Mai 11, 2026', icon: '*', name: 'Revisão de questões', tone: 'emerald' as const },
  { date: 'Mai 12, 2026', icon: '!', name: 'Exportação final', tone: 'amber' as const },
  { date: 'Mai 12, 2026', icon: '?', name: 'Conferência manual', tone: 'purple' as const },
]

export function DashboardPage() {
  const [profile, setProfile] = useState<UserProfileResponseData | null>(() => getAuthProfile())
  const [isLoadingProfile, setIsLoadingProfile] = useState(() => !getAuthProfile())
  const [feedback, setFeedback] = useState<string | null>(null)

  useEffect(() => {
    if (!getAccessToken()) {
      navigateTo('/login', { replace: true })
      return
    }

    if (profile) {
      return
    }

    let isMounted = true

    async function loadProfile() {
      setIsLoadingProfile(true)
      setFeedback(null)

      try {
        const nextProfile = await getProfile()

        if (!isMounted) {
          return
        }

        saveAuthProfile(nextProfile)
        setProfile(nextProfile)
      } catch (error) {
        if (!isMounted) {
          return
        }

        if (error instanceof ApiError && error.kind === 'validation') {
          setFeedback(error.message)
        }
      } finally {
        if (isMounted) {
          setIsLoadingProfile(false)
        }
      }
    }

    void loadProfile()

    return () => {
      isMounted = false
    }
  }, [profile])

  return (
    <AppShell
      actions={
        <>
          <Button onClick={() => navigateTo('/exams')}>+ Gerar prova</Button>
          <Button onClick={() => navigateTo('/exams')} variant="outline">
            Importar dados
          </Button>
        </>
      }
      activeItem="dashboard"
      description={
        isLoadingProfile
          ? 'Carregando seu ambiente de trabalho.'
          : `Planeje, priorize e acompanhe suas tarefas de OCR com facilidade.${profile?.name ? ` Bem-vindo, ${profile.name}.` : ''}`
      }
      searchPlaceholder="Buscar tarefa"
      title="Painel"
      userEmail={profile?.email}
      userName={profile?.name}
    >
      {feedback ? <p className="inline-alert inline-alert--danger">{feedback}</p> : null}

      <div className="tasko-dashboard-stack">
        <StatsCards stats={dashboardStats} />

        <div className="tasko-dashboard-main-grid">
          <div className="tasko-dashboard-main-grid__wide">
            <ProjectAnalytics data={weeklyActivity} />
            <TeamCollaboration items={collaborationItems} />
          </div>

          <div className="tasko-dashboard-main-grid__side">
            <Reminders />
            <ProjectProgress progress={41} />
          </div>
        </div>

        <div className="tasko-dashboard-bottom-grid">
          <ProjectList items={projectItems} />
          <MobileAppCard />
          <TimeTracker />
        </div>
      </div>
    </AppShell>
  )
}
