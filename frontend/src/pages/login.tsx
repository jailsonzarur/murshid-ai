import { useState, type FormEvent } from 'react'

import { Badge } from '../components/ui/badge'
import { Button } from '../components/ui/button'
import { Card } from '../components/ui/card'
import { Icon } from '../components/ui/icon'
import { Input } from '../components/ui/input'
import { ApiError, getProfile, signIn } from '../lib/api'
import { saveAuthProfile, saveAuthSession } from '../lib/auth'
import { navigateTo } from '../lib/navigation'

export function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [fieldErrors, setFieldErrors] = useState<{
    email?: string
    password?: string
  }>({})
  const [rememberMe, setRememberMe] = useState(true)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [feedback, setFeedback] = useState<{
    message: string
    tone: 'error' | 'success'
  } | null>(null)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    const nextFieldErrors = {
      email: !email.trim() ? 'Informe o email.' : undefined,
      password: !password.trim() ? 'Informe a senha.' : undefined,
    }

    if (nextFieldErrors.email || nextFieldErrors.password) {
      setFieldErrors(nextFieldErrors)
      setFeedback(null)
      return
    }

    setIsSubmitting(true)
    setFieldErrors({})
    setFeedback(null)

    try {
      const authData = await signIn(email.trim(), password)

      saveAuthSession(
        {
          accessToken: authData.access_token,
          refreshToken: authData.refresh_token,
          tokenType: authData.token_type,
        },
        rememberMe,
      )

      try {
        const profile = await getProfile()
        saveAuthProfile(profile)
      } catch (profileError) {
        console.error('Falha ao carregar perfil após login', profileError)
      }

      setFeedback({
        message: 'Login realizado. Redirecionando para o dashboard...',
        tone: 'success',
      })

      navigateTo('/dashboard')
    } catch (error) {
      if (error instanceof ApiError && error.kind === 'validation') {
        setFeedback({
          message: error.message,
          tone: 'error',
        })
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <main className="auth-shell">
      <section className="auth-showcase" aria-label="IAsmim">
        <div className="auth-brand">
          <div className="auth-brand__mark">
            <Icon name="sparkles" size={20} strokeWidth={2.2} />
          </div>
          <div>
            <p>IAsmim</p>
            <span>OCR inteligente de provas médicas</span>
          </div>
        </div>

        <div className="auth-copy">
          <Badge tone="green">Painel operacional</Badge>
          <h1>Extraia, revise e acompanhe provas em um único fluxo.</h1>
          <p>
            Acesse o dashboard para gerenciar uploads, acompanhar status OCR e
            visualizar questões processadas.
          </p>
        </div>

        <Card className="auth-preview-card">
          <div className="auth-preview-card__header">
            <div>
              <Badge tone="blue">OCR IA</Badge>
              <p>Prova de Clínica Médica - PDF escaneado</p>
            </div>
            <span>
              <Icon name="checkCircle" size={15} />
              99%
            </span>
          </div>

          <div className="auth-document">
            <div className="auth-document__page">
              <span />
              <span />
              <span />
              <div>
                <strong>A</strong>
                <strong>B</strong>
                <strong>C</strong>
                <strong>D</strong>
              </div>
              <span />
              <span />
            </div>
            <div className="auth-document__scan" />
          </div>

          <div className="auth-preview-card__list">
            <div>
              <Icon name="fileText" size={16} />
              <span>Enunciados estruturados</span>
            </div>
            <div>
              <Icon name="listChecks" size={16} />
              <span>Alternativas identificadas</span>
            </div>
            <div>
              <Icon name="trendingUp" size={16} />
              <span>Fila monitorada</span>
            </div>
          </div>
        </Card>
      </section>

      <section className="auth-form-zone" aria-label="Login">
        <div className="auth-form-wrap">
          <div className="auth-form-heading">
            <Badge tone="neutral">Acesso seguro</Badge>
            <h2>Entrar</h2>
            <p>Use suas credenciais para continuar.</p>
          </div>

          <Card className="login-card">
            <form className="login-form" onSubmit={handleSubmit}>
              <Input
                autoComplete="email"
                error={fieldErrors.email}
                icon="mail"
                label="Email"
                onChange={(event) => {
                  setEmail(event.target.value)
                  setFieldErrors((current) => ({ ...current, email: undefined }))
                }}
                placeholder="você@faculdade.com"
                type="email"
                value={email}
              />
              <Input
                autoComplete="current-password"
                error={fieldErrors.password}
                icon="lock"
                label="Senha"
                onChange={(event) => {
                  setPassword(event.target.value)
                  setFieldErrors((current) => ({ ...current, password: undefined }))
                }}
                placeholder="Digite sua senha"
                type="password"
                value={password}
              />

              <div className="login-form__row">
                <label className="login-remember">
                  <input
                    checked={rememberMe}
                    onChange={(event) => setRememberMe(event.target.checked)}
                    type="checkbox"
                  />
                  <span>Lembrar acesso</span>
                </label>
                <a className="login-link" href="/login">
                  Esqueci a senha
                </a>
              </div>

              <Button
                className="login-submit"
                disabled={isSubmitting}
                icon="arrowRight"
                type="submit"
              >
                {isSubmitting ? 'Entrando...' : 'Entrar'}
              </Button>

              {feedback ? (
                <p className={`login-feedback login-feedback--${feedback.tone}`}>
                  {feedback.message}
                </p>
              ) : null}
            </form>
          </Card>
        </div>
      </section>
    </main>
  )
}
