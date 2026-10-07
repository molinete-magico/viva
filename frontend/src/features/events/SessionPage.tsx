import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api } from '../../services/api'
import { Spinner, useFetch, WarningBanner } from '../../components/ui'
import type { EventTurnAction, Outcome, SessionState } from '../../types/api'

export function SessionPage() {
  const { sessionId = '' } = useParams()
  const navigate = useNavigate()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const session = useFetch<SessionState>(`/events/sessions/${sessionId}`, [sessionId])
  const [outcome, setOutcome] = useState<Outcome | null>(null)

  const state = session.data
  const lastTurn = state ? state.turns[state.turns.length - 1] : undefined
  const closed = !state?.can_act

  useEffect(() => {
    if (!closed || outcome || !state?.outcome_id) return
    api<Outcome>(`/events/sessions/${sessionId}/outcome`).then(setOutcome).catch(() => {})
  }, [closed, outcome, sessionId, state?.outcome_id])

  async function act(action: EventTurnAction) {
    setBusy(true)
    setError('')
    try {
      await api(`/events/sessions/${sessionId}/actions`, { method: 'POST', body: { action_id: action.id } })
      session.reload()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Essa ação não entrou.')
    } finally {
      setBusy(false)
    }
  }

  async function endSession() {
    setBusy(true)
    setError('')
    try {
      const done = await api<Outcome>(`/events/sessions/${sessionId}/end`, { method: 'POST' })
      setOutcome(done)
      session.reload()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Não deu para encerrar.')
    } finally {
      setBusy(false)
    }
  }

  async function abandon() {
    setBusy(true)
    setError('')
    try {
      await api(`/events/sessions/${sessionId}/abandon`, { method: 'POST' })
      navigate(`/events/${session.data?.session.event_id ?? ''}`, { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Não deu para sair.')
      setBusy(false)
    }
  }

  if (session.loading) return <Spinner label="Montando a cena" />
  if (session.error) return <div className="px-4 py-8 text-center text-sm text-ink-soft">{session.error}</div>
  if (!session.data) return null

  const live = session.data

  return (
    <div className="mx-auto max-w-2xl px-4 py-5">
      <Link to={`/events/${live.session.event_id}`} className="text-xs font-medium text-accent-deep transition hover:underline">
        ‹ Voltar ao evento
      </Link>

      {error && <div className="mt-3"><WarningBanner message={error} onClose={() => setError('')} /></div>}

      <h1 className="mt-4 font-display text-2xl font-semibold text-ink">A cena continua…</h1>
      <p className="mt-1 text-xs text-ink-faint">
        Turno {live.turns.length} · {live.session.status.toLowerCase()}
      </p>

      <div className="mt-4 space-y-4">
        {live.turns.map((turn) => (
          <article key={turn.id} className="rounded-2xl border border-line bg-surface p-5">
            <p className="text-[11px] font-medium uppercase tracking-wide text-ink-faint">Turno {turn.turn_index + 1}</p>
            <p className="mt-2 text-[15px] leading-relaxed text-ink">{turn.narrative}</p>
            {turn.dialogue.length > 0 && (
              <div className="mt-3 space-y-2 border-l-2 border-line pl-3">
                {turn.dialogue.map((line, index) => (
                  <p key={index} className="text-sm text-ink-soft">
                    <span className="font-semibold text-ink-soft">{line.speaker}:</span> {line.line}
                  </p>
                ))}
              </div>
            )}
            {turn.player_action_label && (
              <p className="mt-3 rounded-full bg-accent-soft px-3 py-1 text-xs font-medium text-accent-deep">
                Você: {turn.player_action_label}
              </p>
            )}
          </article>
        ))}
      </div>

      {live.can_act && lastTurn && (
        <section className="mt-5 rounded-2xl border border-line bg-surface p-4">
          <h2 className="text-sm font-semibold text-ink">O que você faz?</h2>
          <div className="mt-3 space-y-2">
            {lastTurn.available_actions.map((action) => (
              <button
                key={action.id}
                type="button"
                disabled={busy}
                onClick={() => act(action)}
                className="tap w-full rounded-xl border border-line bg-paper px-4 py-3 text-left text-sm font-medium text-ink transition hover:border-accent/50 disabled:opacity-40"
              >
                {action.label}
                {action.hint ? <span className="block text-xs font-normal text-ink-faint">{action.hint}</span> : null}
              </button>
            ))}
          </div>
          <div className="mt-3 flex gap-2">
            <button
              type="button"
              disabled={busy}
              onClick={endSession}
              className="tap rounded-full bg-accent px-4 py-2 text-sm font-semibold text-white transition hover:opacity-90 disabled:opacity-40"
            >
              Encerrar e colher os efeitos
            </button>
            <button
              type="button"
              disabled={busy}
              onClick={abandon}
              className="tap rounded-full border border-line bg-paper px-4 py-2 text-sm font-medium text-ink-soft transition hover:border-warn/40 disabled:opacity-40"
            >
              Ir embora
            </button>
          </div>
        </section>
      )}

      {outcome && (
        <section className="mt-6 rounded-2xl border border-accent/30 bg-accent-soft p-5">
          <h2 className="font-display text-lg font-semibold text-accent-deep">O que ficou dessa noite</h2>
          <p className="mt-2 text-sm leading-relaxed text-ink">{outcome.summary}</p>
          {outcome.memories.length > 0 && (
            <p className="mt-3 text-xs text-ink-soft">
              Novas memórias guardadas na Vila Serena · e a vida segue.
            </p>
          )}
          <Link
            to={`/settings/world/relationships`}
            className="tap mt-4 inline-block rounded-full bg-accent px-4 py-2 text-sm font-semibold text-white transition hover:opacity-90"
          >
            Ver memórias e laços
          </Link>
        </section>
      )}
    </div>
  )
}