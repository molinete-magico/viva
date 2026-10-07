import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import { ApiError } from '../../services/api'

export function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await login(email, password)
      navigate('/feed', { replace: true })
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Não foi possível entrar agora.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <AuthLayout title="Bem-vindo de volta" subtitle="Entre para ver como andou a cidade.">
      <form onSubmit={onSubmit} className="space-y-4">
        <Field label="E-mail">
          <input
            type="email"
            required
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="auth-input"
            placeholder="voce@exemplo.com"
          />
        </Field>
        <Field label="Senha">
          <input
            type="password"
            required
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="auth-input"
            placeholder="••••••••"
          />
        </Field>
        {error && (
          <p className="text-sm text-accent-deep" role="alert">
            {error}
          </p>
        )}
        <button
          type="submit"
          disabled={submitting}
          className="tap w-full rounded-full bg-accent px-6 py-3 text-sm font-semibold text-white transition hover:bg-accent-deep disabled:opacity-60"
        >
          {submitting ? 'Entrando…' : 'Entrar'}
        </button>
      </form>
      <p className="mt-6 text-center text-sm text-ink-soft">
        Ainda não tem conta?{' '}
        <Link to="/register" className="font-medium text-accent-deep underline-offset-2 hover:underline">
          Criar uma
        </Link>
      </p>
    </AuthLayout>
  )
}

export function RegisterPage() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await register(email, password)
      navigate('/onboarding', { replace: true })
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Não foi possível criar a conta agora.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <AuthLayout title="Chegou na Vila Serena" subtitle="Crie sua conta e depois dê vida ao seu personagem.">
      <form onSubmit={onSubmit} className="space-y-4">
        <Field label="E-mail">
          <input
            type="email"
            required
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="auth-input"
            placeholder="voce@exemplo.com"
          />
        </Field>
        <Field label="Senha (mínimo 6 caracteres)">
          <input
            type="password"
            required
            minLength={6}
            autoComplete="new-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="auth-input"
            placeholder="••••••••"
          />
        </Field>
        {error && (
          <p className="text-sm text-accent-deep" role="alert">
            {error}
          </p>
        )}
        <button
          type="submit"
          disabled={submitting}
          className="tap w-full rounded-full bg-accent px-6 py-3 text-sm font-semibold text-white transition hover:bg-accent-deep disabled:opacity-60"
        >
          {submitting ? 'Criando conta…' : 'Criar conta'}
        </button>
      </form>
      <p className="mt-6 text-center text-sm text-ink-soft">
        Já tem conta?{' '}
        <Link to="/login" className="font-medium text-accent-deep underline-offset-2 hover:underline">
          Entrar
        </Link>
      </p>
    </AuthLayout>
  )
}

function AuthLayout({
  title,
  subtitle,
  children,
}: {
  title: string
  subtitle: string
  children: React.ReactNode
}) {
  return (
    <div className="flex min-h-dvh flex-col justify-center px-6 py-12 safe-top safe-bottom">
      <div className="mx-auto w-full max-w-sm">
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-accent text-white shadow-sm">
            <span aria-hidden className="text-2xl">🍜</span>
          </div>
          <h1 className="font-display text-2xl font-semibold tracking-tight text-ink">{title}</h1>
          <p className="mt-2 text-sm text-ink-soft">{subtitle}</p>
        </div>
        {children}
        <p className="mt-10 text-center text-xs text-ink-faint">Vila Serena · cidade de gente de verdade</p>
      </div>
    </div>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-xs font-medium uppercase tracking-wide text-ink-soft">{label}</span>
      {children}
    </label>
  )
}
