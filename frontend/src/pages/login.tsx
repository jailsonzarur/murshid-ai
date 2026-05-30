import { useState, type FormEvent } from 'react'

import { ApiError, getProfile, signIn } from '../lib/api'
import { saveAuthProfile, saveAuthSession } from '../lib/auth'
import { navigateTo } from '../lib/navigation'

export function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
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

      setFeedback({ message: 'Login realizado. Redirecionando para o painel...', tone: 'success' })
      navigateTo('/dashboard')
    } catch (error) {
      if (error instanceof ApiError && error.kind === 'validation') {
        setFeedback({ message: error.message, tone: 'error' })
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="login">
      <section className="login-form-side">
        <div className="login-brand">
          <div className="brand-mark">M</div>
          <div>
            <div className="brand-name">Murshid</div>
            <div className="brand-sub">Plataforma de estudos</div>
          </div>
        </div>

        <div className="login-form-wrap">
          <div className="login-eyebrow">
            <span className="eyebrow-dot" />
            Bem-vindo de volta
          </div>
          <h1 className="login-h1">Entre na sua conta</h1>
          <p className="login-sub">
            Continue de onde parou — suas provas, flashcards, transcrições e anotações já estão te esperando.
          </p>

          <button className="social-btn" type="button">
            <svg viewBox="0 0 24 24">
              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.76h3.56c2.08-1.92 3.28-4.74 3.28-8.09z" />
              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.56-2.76c-.98.66-2.23 1.06-3.72 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84A11 11 0 0 0 12 23z" />
              <path fill="#FBBC05" d="M5.84 14.11A6.6 6.6 0 0 1 5.5 12c0-.73.13-1.44.34-2.11V7.05H2.18A11 11 0 0 0 1 12c0 1.78.43 3.46 1.18 4.95l3.66-2.84z" />
              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.05l3.66 2.84C6.71 7.3 9.14 5.38 12 5.38z" />
            </svg>
            <span>Continuar com Google</span>
          </button>

          <div className="divider-row"><span>ou com e-mail</span></div>

          <form onSubmit={handleSubmit}>
            <div className="field">
              <label htmlFor="login-email">E-mail</label>
              <div className={`input-wrap${fieldErrors.email ? ' input-wrap--error' : ''}`}>
                <span className="lead">
                  <svg viewBox="0 0 24 24"><rect x="3" y="5" width="18" height="14" rx="2" /><path d="M3 7l9 6 9-6" /></svg>
                </span>
                <input
                  autoComplete="email"
                  id="login-email"
                  onChange={(e) => { setEmail(e.target.value); setFieldErrors((c) => ({ ...c, email: undefined })) }}
                  placeholder="seu@email.com"
                  required
                  type="email"
                  value={email}
                />
              </div>
              {fieldErrors.email ? <span className="field-error">{fieldErrors.email}</span> : null}
            </div>

            <div className="field">
              <label htmlFor="login-pwd">Senha</label>
              <div className={`input-wrap${fieldErrors.password ? ' input-wrap--error' : ''}`}>
                <span className="lead">
                  <svg viewBox="0 0 24 24"><rect x="4" y="10" width="16" height="11" rx="2" /><path d="M8 10V7a4 4 0 0 1 8 0v3" /></svg>
                </span>
                <input
                  autoComplete="current-password"
                  id="login-pwd"
                  onChange={(e) => { setPassword(e.target.value); setFieldErrors((c) => ({ ...c, password: undefined })) }}
                  placeholder="••••••••"
                  required
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                />
                <button
                  aria-label="Mostrar senha"
                  className="toggle"
                  onClick={() => setShowPassword((v) => !v)}
                  type="button"
                >
                  {showPassword ? (
                    <svg viewBox="0 0 24 24"><path d="M17.94 17.94A10 10 0 0 1 12 19c-7 0-11-7-11-7a18 18 0 0 1 4.06-4.94M9.9 4.24A10 10 0 0 1 12 4c7 0 11 7 11 7a18 18 0 0 1-3.16 4.19M1 1l22 22M9.9 9.9a3 3 0 0 0 4.2 4.2" /></svg>
                  ) : (
                    <svg viewBox="0 0 24 24"><path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7S1 12 1 12z" /><circle cx="12" cy="12" r="3" /></svg>
                  )}
                </button>
              </div>
              {fieldErrors.password ? <span className="field-error">{fieldErrors.password}</span> : null}
            </div>

            <div className="form-row">
              <button
                className={`remember${rememberMe ? ' on' : ''}`}
                onClick={() => setRememberMe((v) => !v)}
                type="button"
              >
                <span className="box" />
                <span>Lembrar de mim</span>
              </button>
              <a className="forgot" href="#">Esqueceu a senha?</a>
            </div>

            <button className="submit-btn" disabled={isSubmitting} type="submit">
              <span>{isSubmitting ? 'Entrando...' : 'Entrar no painel'}</span>
              <svg viewBox="0 0 24 24"><path d="M5 12h14M12 5l7 7-7 7" /></svg>
            </button>

            {feedback ? (
              <p className={`login-feedback login-feedback--${feedback.tone}`}>
                {feedback.message}
              </p>
            ) : null}
          </form>

          <div className="signup-line">
            Ainda não tem uma conta?{' '}
            <a href="/register">Cadastre-se grátis →</a>
          </div>
        </div>

        <div className="login-foot">
          <span>© 2026 Murshid · Plataforma de estudos</span>
          <div className="links">
            <a href="#">Termos</a>
            <a href="#">Privacidade</a>
            <a href="#">Suporte</a>
          </div>
        </div>
      </section>

      <aside className="login-stage">
        <div className="stage-grain" />
        <div className="stage-orb o1" />
        <div className="stage-orb o2" />
        <div className="stage-orb o3" />

        <div className="stage-top">
          <span className="badge">Versão 2.6 · 26 Mai</span>
          <span>v2.6.0 · stable</span>
        </div>

        <div>
          <div className="stage-headline">
            <div className="stage-eyebrow">Seu mentor de estudos</div>
            <h2 className="stage-title">
              Tudo o que você estuda, <em>em um só lugar</em>.
            </h2>
            <p className="stage-lede">
              Provas, flashcards, transcrições de aulas, anotações e resumos. O Murshid organiza seu material e te guia até o próximo nível — seja qual for sua área de estudo.
            </p>
          </div>

          <div className="float-card">
            <div className="float-card-head">
              <div className="fc-icon">
                <svg viewBox="0 0 24 24"><path d="M12 3l9 5-9 5-9-5 9-5z" /><path d="M3 13l9 5 9-5" /><path d="M3 17l9 5 9-5" /></svg>
              </div>
              <div>
                <div className="fc-label">Esta semana</div>
                <div className="fc-name">Atividade de estudo</div>
              </div>
            </div>
            <div className="fc-value">14h 32m <small>estudadas</small></div>
            <div className="fc-bars">
              <i style={{ height: '30%' }} />
              <i style={{ height: '48%' }} />
              <i style={{ height: '38%' }} />
              <i style={{ height: '62%' }} />
              <i style={{ height: '22%' }} />
              <i className="hi" style={{ height: '92%' }} />
              <i style={{ height: '55%' }} />
            </div>
            <div className="fc-foot">
              <span>D · S · T · Q · Q · S · S</span>
              <span style={{ color: 'oklch(95% 0.10 90)' }}>↑ Pico Qua · 3h 12m</span>
            </div>
          </div>

          <div className="float-mini">
            <div className="ring">
              <svg width="38" height="38" viewBox="0 0 38 38">
                <circle cx="19" cy="19" r="14" fill="none" stroke="var(--bg-sunken)" strokeWidth="4" />
                <circle
                  cx="19" cy="19" r="14"
                  fill="none"
                  stroke="var(--accent)"
                  strokeWidth="4"
                  strokeLinecap="round"
                  strokeDasharray="87.96"
                  strokeDashoffset="51.9"
                  transform="rotate(-90 19 19)"
                />
              </svg>
              <strong>41%</strong>
            </div>
            <div>
              <div className="mini-label">Meta semanal</div>
              <div className="mini-name">14h de 20h</div>
            </div>
          </div>
        </div>

        <div className="stage-quote">
          <p className="quote-text">
            <span className="quote-mark">"</span>
            Larguei o caderno e três apps diferentes. Hoje subo minhas aulas e provas no Murshid, ele transcreve, gera flashcards e me cobra. É como ter um mentor que nunca dorme.
            <span className="quote-mark">"</span>
          </p>
          <div className="quote-author">
            <div className="quote-avatar">YF</div>
            <div>
              <div className="author-name">Yasmim Freitas</div>
              <div className="author-role">Estudante de medicina · UFPI</div>
            </div>
          </div>
          <div className="stat-dots">
            <span><span className="num">12k+</span> estudantes</span>
            <span className="sep" />
            <span><span className="num">98,7%</span> precisão</span>
            <span className="sep" />
            <span><span className="num">4,9</span> avaliação</span>
          </div>
        </div>
      </aside>
    </div>
  )
}
