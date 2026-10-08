import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../services/api'
import { EmptyState, ErrorState, Spinner, useFetch, WarningBanner } from '../../components/ui'
import type { Conversation, EventItem, Listing, Location } from '../../types/api'

const STATUS_LABELS: Record<string, string> = {
  SCHEDULED: 'Disponível',
  OPEN: 'Aberto',
  ACTIVE: 'Em andamento',
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

const emptyForm = {
  title: '',
  description: '',
  location_id: 0,
  invite_conversation_ids: [] as number[],
}

export function EventsPage() {
  const [form, setForm] = useState(emptyForm)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [showCreate, setShowCreate] = useState(false)
  const [onlyMine, setOnlyMine] = useState(false)
  const events = useFetch<Listing<EventItem>>(onlyMine ? '/events?mine=true' : '/events', [onlyMine])
  const locations = useFetch<Listing<Location>>('/world/locations')
  const conversations = useFetch<Listing<Conversation>>('/conversations')

  async function createEvent() {
    setSaving(true)
    setError('')
    try {
      if (!form.title.trim()) throw new Error('Dê um título ao evento.')
      if (!form.location_id) throw new Error('Escolha onde vai rolar.')
      await api<EventItem>('/events', {
        method: 'POST',
        body: {
          title: form.title,
          description: form.description,
          location_id: form.location_id,
          invite_conversation_ids: form.invite_conversation_ids,
        },
      })
      setForm(emptyForm)
      setShowCreate(false)
      events.reload()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Não deu para criar o evento.')
      setSaving(false)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="mx-auto max-w-2xl">
      <div className="flex items-center justify-between gap-2">
        <h1 className="font-display text-xl font-semibold text-ink">Atividades</h1>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => setOnlyMine((v) => !v)}
            className={`tap rounded-full px-3 py-1.5 text-xs font-medium transition ${
              onlyMine ? 'bg-accent-soft text-accent-deep' : 'bg-surface text-ink-soft'
            }`}
          >
            Meus
          </button>
          <button
            type="button"
            onClick={() => setShowCreate((v) => !v)}
            className="tap rounded-full bg-accent px-3 py-1.5 text-xs font-semibold text-white transition hover:opacity-90"
          >
            {showCreate ? 'Fechar' : 'Criar cena'}
          </button>
        </div>
      </div>

      {error && <div className="mt-3"><WarningBanner message={error} onClose={() => setError('')} /></div>}

      {showCreate && (
        <form
          className="mt-4 space-y-3 border-y border-line bg-transparent p-4"
          onSubmit={(e) => {
            e.preventDefault()
            createEvent()
          }}
        >
          <h2 className="text-sm font-semibold text-ink">Criar uma cena</h2>
          <input
            value={form.title}
            onChange={(e) => setForm({ ...form, title: e.target.value })}
            placeholder="Título do evento"
            className="w-full rounded-xl border border-line bg-paper px-3 py-2 text-sm text-ink outline-none focus:border-accent"
          />
          <textarea
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
            placeholder="Do que se trata (opcional)"
            rows={2}
            className="w-full resize-none rounded-xl border border-line bg-paper px-3 py-2 text-sm text-ink outline-none focus:border-accent"
          />
          <div>
            <select
              value={form.location_id}
              onChange={(e) => setForm({ ...form, location_id: Number(e.target.value) })}
              className="w-full rounded-xl border border-line bg-paper px-3 py-2 text-sm text-ink outline-none focus:border-accent"
            >
              <option value={0}>Onde?</option>
              {(locations.data?.items ?? []).map((location) => <option key={location.id} value={location.id}>{location.name}</option>)}
            </select>
          </div>
          <div>
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-soft">Convidar moradores</p>
            {conversations.loading ? (
              <p className="text-xs text-ink-faint">Carregando conversas…</p>
            ) : conversations.error ? (
              <p className="text-xs text-warn">{conversations.error}</p>
            ) : (conversations.data?.items.length ?? 0) === 0 ? (
              <p className="text-xs text-ink-faint">Você ainda não tem conversas para convidar alguém.</p>
            ) : (
              <ul className="divide-y divide-line border-y border-line">
                {(conversations.data?.items ?? []).map((conversation) => {
                  const selected = form.invite_conversation_ids.includes(conversation.id)
                  return (
                    <li key={conversation.id}>
                      <label className="flex cursor-pointer items-center gap-3 px-2 py-2.5 hover:bg-paper">
                        <input
                          type="checkbox"
                          checked={selected}
                          onChange={() => {
                            const ids = selected
                              ? form.invite_conversation_ids.filter((id) => id !== conversation.id)
                              : [...form.invite_conversation_ids, conversation.id]
                            setForm({ ...form, invite_conversation_ids: ids })
                          }}
                        />
                        <div className="min-w-0 flex-1">
                          <p className="text-sm font-medium text-ink">{conversation.partner.name}</p>
                          <p className="text-[11px] text-ink-faint">Conversa #{conversation.id}</p>
                        </div>
                      </label>
                    </li>
                  )
                })}
              </ul>
            )}
            <p className="mt-2 text-[11px] text-ink-faint">
              O convite usa o ID da conversa por baixo; o nome é apenas para facilitar a escolha.
            </p>
          </div>
          <button
            type="submit"
            disabled={saving}
            className="tap w-full rounded-full bg-accent py-2.5 text-sm font-semibold text-white transition hover:opacity-90 disabled:opacity-40"
          >
            {saving ? 'Marcando...' : 'Criar atividade'}
          </button>
        </form>
      )}

      {events.loading ? (
        <Spinner label="Procurando cenas" />
      ) : events.error ? (
        <ErrorState message={events.error} onRetry={events.reload} />
      ) : (events.data?.items.length ?? 0) === 0 ? (
        <EmptyState title="Nada acontecendo por aqui." hint="Novas situações aparecem quando alguém da cidade puxa uma cena." />
      ) : (
        <ul className="mt-4 space-y-3">
          {events.data?.items.map((event) => (
            <li key={event.id}>
              <Link
                to={`/events/${event.id}`}
                className="block border-b border-line bg-transparent px-4 py-5 transition hover:bg-surface"
              >
                <div className="flex items-start justify-between gap-3">
                  <h2 className="text-base font-semibold text-ink">{event.title}</h2>
                  <span className="shrink-0 text-[11px] font-medium uppercase tracking-wide text-sea">
                    {STATUS_LABELS[event.status] ?? event.status}
                  </span>
                </div>
                <p className="mt-1 text-xs text-ink-soft">
                  {event.location_name ? `📍 ${event.location_name}` : 'Na cidade'}
                </p>
                {event.description && (
                  <p className="mt-2 text-sm leading-relaxed text-ink-soft">{event.description}</p>
                )}
                <p className="mt-2 text-xs text-ink-faint">
                  {event.participant_count} {event.participant_count === 1 ? 'na cena' : 'na cena'}
                  {event.host_name ? ` · por ${event.host_name}` : ''}
                  {event.my_status ? ` · ${PARTICIPANT_LABELS[event.my_status] ?? event.my_status}` : ''}
                </p>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}