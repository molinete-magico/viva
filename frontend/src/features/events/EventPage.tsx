import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api } from '../../services/api'
import { ErrorState, Spinner, useFetch, WarningBanner } from '../../components/ui'
import type { EventDetail } from '../../types/api'
import { formatEventTime } from '../../utils/format'

const STATUS_LABELS: Record<string, string> = {
  SCHEDULED: 'Marcado',
  OPEN: 'Aberto',
  ACTIVE: 'Acontecendo agora',
  COMPLETED: 'Encerrado',
  CANCELLED: 'Cancelado',
}

const PARTICIPANT_LABELS: Record<string, string> = {
  INVITED: 'convidado(a)',
  ACCEPTED: 'confirmado(a)',
  JOINED: 'participando',
  DECLINED: 'recusou',
  WITHDREW: 'saiu',
}

export function EventPage() {
  const { eventId = '' } = useParams()
  const navigate = useNavigate()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const event = useFetch<EventDetail>(`/events/${eventId}`, [eventId])

  if (event.loading) return <Spinner label="Abrindo o evento" />
  if (event.error) return <ErrorState message={event.error} onRetry={event.reload} />
  if (!event.data) return null

  const data = event.data
  const open = ['SCHEDULED', 'OPEN', 'ACTIVE'].includes(data.status)
  const canPlay = open && ['ACCEPTED', 'JOINED'].includes(data.my_status ?? '')

  async function rsvp(accept: boolean) {
    setBusy(true)
    setError('')
    try {
      await api<EventDetail>(`/events/${data.id}/rsvp`, { method: 'POST', body: { accept } })
      event.reload()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Algo deu errado.')
    } finally {
      setBusy(false)
    }
  }

  async function enter() {
    setBusy(true)
    setError('')
    try {
      const session = await api<{ session: { id: number } }>(`/events/${data.id}/sessions`, { method: 'POST' })
      navigate(`/events/session/${session.session.id}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Algo deu errado.')
      setBusy(false)
    }
  }

  async function cancelEvent() {
    const reason = window.prompt('Motivo do cancelamento (opcional):') ?? ''
    setBusy(true)
    setError('')
    try {
      await api<EventDetail>(`/events/${data.id}/cancel`, { method: 'POST', body: { reason } })
      event.reload()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Não rolou cancelar.')
    } finally {
      setBusy(false)
    }
  }

  const isHost = data.am_host

  return (
    <div className="mx-auto max-w-2xl px-4 py-5">
      <Link to="/events" className="text-xs font-medium text-accent-deep transition hover:underline">
        ‹ Voltar aos eventos
      </Link>

      {error && <div className="mt-3"><WarningBanner message={error} onClose={() => setError('')} /></div>}

      <div className="mt-3 rounded-3xl border border-line bg-surface p-5">
        <div className="flex items-start justify-between gap-3">
          <h1 className="font-display text-2xl font-semibold text-ink">{data.title}</h1>
          <span className="shrink-0 rounded-full bg-sea-soft px-3 py-1 text-xs font-medium text-sea">
            {STATUS_LABELS[data.status] ?? data.status}
          </span>
        </div>
        <p className="mt-2 text-sm text-ink-soft">
          {formatEventTime(data.scheduled_at)}
          {data.location_name ? ` · ${data.location_name}` : ''}
        </p>
        {data.description && <p className="mt-3 text-sm leading-relaxed text-ink-soft">{data.description}</p>}
        {data.cancel_reason && (
          <p className="mt-3 rounded-xl bg-warn-soft px-3 py-2 text-xs text-warn">Cancelado: {data.cancel_reason}</p>
        )}

        <div className="mt-4 flex flex-wrap gap-2">
          {open && data.my_status === 'INVITED' && (
            <button
              type="button"
              disabled={busy}
              onClick={() => rsvp(true)}
              className="tap rounded-full bg-accent px-4 py-2 text-sm font-semibold text-white transition hover:opacity-90 disabled:opacity-40"
            >
              Confirmar presença
            </button>
          )}
          {open && (
            <button
              type="button"
              disabled={busy}
              onClick={enter}
              className="tap rounded-full bg-accent px-5 py-2 text-sm font-semibold text-white transition hover:opacity-90 disabled:opacity-40"
            >
              Entrar na cena
            </button>
          )}
          {open && data.my_status === 'ACCEPTED' && (
            <button
              type="button"
              disabled={busy}
              onClick={() => rsvp(false)}
              className="tap rounded-full border border-line bg-paper px-4 py-2 text-sm font-medium text-ink-soft transition hover:border-accent/40"
            >
              Recusar
            </button>
          )}
          {isHost && open && (
            <button
              type="button"
              disabled={busy}
              onClick={cancelEvent}
              className="tap rounded-full border border-line bg-paper px-4 py-2 text-sm font-medium text-ink-soft transition hover:border-warn/40"
            >
              Cancelar evento
            </button>
          )}
        </div>
      </div>

      <section className="mt-4 rounded-3xl border border-line bg-surface p-5">
        <h2 className="text-xs font-semibold uppercase tracking-wide text-ink-soft">
          Participantes · {data.participant_count}
        </h2>
        {data.participants.length === 0 ? (
          <p className="mt-2 text-sm text-ink-faint">Ninguém por aqui ainda.</p>
        ) : (
          <ul className="mt-3 space-y-2">
            {data.participants.map((participant) => (
              <li key={participant.character_id} className="flex items-center justify-between gap-3 text-sm">
                <Link
                  to={participant.is_npc ? `/profile/${participant.character_id}` : `/profile/${participant.character_id}`}
                  className="min-w-0 truncate font-medium text-ink transition hover:opacity-75"
                >
                  {participant.name}
                </Link>
                <span className="shrink-0 text-xs text-ink-faint">
                  {PARTICIPANT_LABELS[participant.status] ?? participant.status}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  )
}