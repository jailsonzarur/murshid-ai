import { useEffect, useState } from 'react'

import { ExamViewer } from '../components/exam-viewer/ExamViewer'
import { AppShell } from '../components/layout/app-shell'
import { Button } from '../components/ui/button'
import { Card } from '../components/ui/card'
import { Icon } from '../components/ui/icon'
import { getExamQuestions } from '../lib/api'
import { getAccessToken } from '../lib/auth'
import { navigateTo } from '../lib/navigation'
import type { Question } from '../types/exam'

function getExamIdFromPath() {
  const [, resource, examId] = window.location.pathname.split('/')
  return resource === 'exams' ? examId : ''
}

export function ExamViewerPage() {
  const [questions, setQuestions] = useState<Question[]>([])
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    if (!getAccessToken()) {
      navigateTo('/login', { replace: true })
      return
    }

    const examId = getExamIdFromPath()

    if (!examId) {
      navigateTo('/exams', { replace: true })
      return
    }

    async function loadQuestions() {
      setIsLoading(true)

      try {
        const nextQuestions = await getExamQuestions(examId)
        setQuestions(nextQuestions)
      } catch {
        setQuestions([])
      } finally {
        setIsLoading(false)
      }
    }

    void loadQuestions()
  }, [])

  return (
    <AppShell
      actions={
        <Button icon="arrowLeft" onClick={() => navigateTo('/exams')} variant="outline">
          Voltar para provas
        </Button>
      }
      activeItem="exams"
      description="Responda uma questão por vez e navegue pela prova processada."
      searchPlaceholder="Buscar questões..."
      title="Visualizar prova"
    >
      <Card className="tasko-card exam-viewer-panel">
        {isLoading ? (
          <div className="loading-state">
            <span>
              <Icon name="clock" size={18} />
            </span>
            <p>Carregando questões...</p>
          </div>
        ) : (
          <ExamViewer questions={questions} />
        )}
      </Card>
    </AppShell>
  )
}
