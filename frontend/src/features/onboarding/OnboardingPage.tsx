import { useState } from 'react'
import type { FormEvent } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import { ApiError, api } from '../../services/api'

export function OnboardingPage() {
  const { character, refresh } = useAuth()
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [age, setAge] = useState('25')
  const [pronouns, setPronouns] = useState('')
  const [profession, setProfession] = useState('')
  const [bio, setBio] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  if (character) return <Navigate to={`/profile/${character.id}`} replace />

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await api('/characters', {
        method: 'POST',
        body: {
          name,
          age: Number(age),
          pronouns,
          profession_label: profession,
          bio,
        },
      })
      await refresh()
      navigate('/feed', { replace: true })
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Não foi possível criar seu personagem agora.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="mx-auto max-w-lg px-5 py-10 safe-top">
      <p className="text-xs font-semibold uppercase tracking-widest text-accent">Seu personagem</p>
      <h1 className="mt-2 font-display text-2xl font-semibold text-ink">Quem vive em Vila Serena?</h1>
      <p className="mt-2 text-sm leading-relaxed text-ink-soft">
        Você será mais um morador da cidade — com rotina, contas para pagar e gente para encontrar.
      </p>

      <form onSubmit={onSubmit} className="mt-8 space-y-5">
        <label className="block">
          <span className="mb-1.5 block text-xs font-medium uppercase tracking-wide text-ink-soft">Nome</span>
          <input
            required
            minLength={2}
            maxLength={120}
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="auth-input"
            placeholder="Como todo mundo te chama"
          />
        </label>
        <div className="grid grid-cols-2 gap-4">
          <label className="block">
            <span className="mb-1.5 block text-xs font-medium uppercase tracking-wide text-ink-soft">Idade</span>
            <input
              type="number"
              required
              min={16}
              max={99}
              value={age}
              onChange={(e) => setAge(e.target.value)}
              className="auth-input"
            />
          </label>
          <label className="block">
            <span className="mb-1.5 block text-xs font-medium uppercase tracking-wide text-ink-soft">
              Pronomes (opcional)
            </span>
            <input
              value={pronouns}
              onChange={(e) => setPronouns(e.target.value)}
              className="auth-input"
              placeholder="ela/dela"
            />
          </label>
        </div>
        <label className="block">
          <span className="mb-1.5 block text-xs font-medium uppercase tracking-wide text-ink-soft">
            Como você se sustenta
          </span>
          <input
            value={profession}
            onChange={(e) => setProfession(e.target.value)}
            className="auth-input"
            placeholder="Motorista de dia, garçom à noite…"
          />
        </label>
        <label className="block">
          <span className="mb-1.5 block text-xs font-medium uppercase tracking-wide text-ink-soft">Sobre você</span>
          <textarea
            rows={4}
            maxLength={2000}
            value={bio}
            onChange={(e) => setBio(e.target.value)}
            className="auth-input resize-none"
            placeholder="Uma ou duas frases sobre quem é você."
          />
        </label>
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
          {submitting ? 'Chegando na cidade…' : 'Começar a vida na cidade'}
        </button>
      </form>
    </div>
  )
}
