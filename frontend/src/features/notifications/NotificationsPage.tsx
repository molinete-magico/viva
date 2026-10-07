import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../services/api'
import { Avatar, EmptyState, ErrorState, Spinner, useFetch } from '../../components/ui'
import type { Listing, NotificationItem } from '../../types/api'
import { relativeTime } from '../../utils/format'

const TYPE_LABELS: Record<string, string> = {
  NEW_MESSAGE: 'Nova mensagem',
  EVENT_INVITE: 'Convite de evento',
  EVENT_STARTING: 'Evento começando',
  EVENT_CANCELLED: 'Evento cancelado',
  POST_LIKE: 'curtiu seu post',
  POST_COMMENT: 'comentou no seu post',
  NEW_FOLLOWER: 'passou a te seguir',
  RELATIONSHIP_CHANGE: 'Relacionamento mudou',
  MILESTONE: 'Marco da história',
  NPC_DM_INITIATIVE: 'Mensagem iniciada por alguém',
  EVENT_RESULT: 'Resultado do evento',
  CITY_RELEVANCE: 'novidade importante na cidade',
}

function targetOf(notification: NotificationItem): string {
  switch (notification.type) {
    case 'POST_LIKE':
    case 'POST_COMMENT':
      return '/feed'
    case 'NEW_FOLLOWER':
      return `/profile/${String(notification.payload.character_id)}`
    case 'NEW_MESSAGE':
      return `/messages/${String(notification.payload.conversation_id)}`
    case 'EVENT_INVITE':
    case 'EVENT_STARTING':
    case 'EVENT_RESULT':
    case 'EVENT_CANCELLED':
      return `/events/${String(notification.payload.event_id)}`
    case 'RELATIONSHIP_CHANGE':
      return `/profile/${String(notification.payload.other_id ?? notification.payload.character_id)}`
    case 'CITY_RELEVANCE':
      return '/world'
    case 'MILESTONE':
      return '/settings/world/relationships'
    default:
      return '/notifications'
  }
}

function describe(notification: NotificationItem) {
  const actorName = String(notification.payload.actor_name ?? notification.payload.name ?? '')
  const label = TYPE_LABELS[notification.type] ?? notification.type.toLowerCase()
  if (!actorName) return label
  return `${actorName} ${label}`
}

export function NotificationsPage() {
  const [busy, setBusy] = useState(false)
  const notifications = useFetch<Listing<NotificationItem>>('/notifications')

  async function markAllRead() {
    setBusy(true)
    try {
      await api('/notifications/read-all', { method: 'POST' })
      notifications.reload()
    } finally {
      setBusy(false)
    }
  }

  async function markRead(id: number) {
    await api(`/notifications/${id}/read`, { method: 'POST' })
    notifications.reload()
  }

  return (
    <div className="mx-auto max-w-2xl px-4 py-5">
      <div className="flex items-center justify-between">
        <h1 className="font-display text-xl font-semibold text-ink">Notificações</h1>
        {(notifications.data?.items.length ?? 0) > 0 && (
          <button
            type="button"
            onClick={markAllRead}
            disabled={busy}
            className="tap text-xs font-medium text-accent-deep transition hover:underline disabled:opacity-40"
          >
            Marcar todas como lidas
          </button>
        )}
      </div>

      {notifications.loading ? (
        <Spinner label="Carregando notificações" />
      ) : notifications.error ? (
        <ErrorState message={notifications.error} onRetry={notifications.reload} />
      ) : (notifications.data?.items.length ?? 0) === 0 ? (
        <EmptyState title="Nada de novidade ainda." hint="Convites, curtidas e recados aparecem aqui." />
      ) : (
        <ul className="mt-4 divide-y divide-line overflow-hidden rounded-2xl border border-line bg-surface">
          {notifications.data?.items.map((notification) => {
            const target = targetOf(notification)
            const isUnread = !notification.read_at
            const inner = (
              <span className="flex min-w-0 items-center gap-3">
                {notification.type === 'NEW_FOLLOWER' || notification.type === 'POST_COMMENT' || notification.type === 'POST_LIKE' ? (
                  <Avatar
                    name={String(notification.payload.actor_name ?? notification.payload.name ?? '?')}
                    size="sm"
                  />
                ) : (
                  <span
                    className={`mt-0.5 h-2 w-2 shrink-0 rounded-full ${isUnread ? 'bg-accent' : 'bg-line'}`}
                    aria-hidden
                  />
                )}
                <span className="min-w-0">
                  <span className={`block text-sm ${isUnread ? 'font-semibold text-ink' : 'font-medium text-ink-soft'}`}>
                    {describe(notification)}
                  </span>
                  <span className="block text-xs text-ink-faint">{relativeTime(notification.created_at)}</span>
                </span>
              </span>
            )
            return target === '/notifications' ? (
              <li key={notification.id} className="flex items-center gap-3 px-4 py-3.5">
                {inner}
              </li>
            ) : (
              <li key={notification.id} className="px-4 py-3.5">
                <Link
                  to={target}
                  onClick={async () => {
                    if (isUnread) await markRead(notification.id)
                  }}
                  className="flex items-center gap-3 transition hover:opacity-80"
                >
                  {inner}
                  <span aria-hidden className="ml-auto text-ink-faint">
                    ›
                  </span>
                </Link>
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}