import { useState, type FormEvent } from 'react'

import { Button } from '../components/ui/button'
import { Card } from '../components/ui/card'
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
      email: !email.trim() ? 'Informe o e-mail.' : undefined,
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
        message: 'Login realizado. Redirecionando para o painel...',
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
      <section className="auth-form-zone" aria-label="Login">
        <div className="auth-form-wrap">
          <div className="auth-form-heading">
            <h2>Entrar</h2>
            <p>Use suas credenciais para continuar.</p>
          </div>

          <Card className="login-card">
            <form className="login-form" onSubmit={handleSubmit}>
              <Input
                autoComplete="email"
                error={fieldErrors.email}
                icon="mail"
                label="E-mail"
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
