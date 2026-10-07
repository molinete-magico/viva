import { EmptyState, ErrorState, Spinner, useFetch } from '../../components/ui'
import type { Conversation, Listing } from '../../types/api'
import { relativeTime } from '../../utils/format'
import { Avatar } from '../../components/ui'
import { Link } from 'react-router-dom'

export function MessagesPage() {
  const conversations = useFetch<Listing<Conversation>>('/conversations')

  return (
    <div className="mx-auto max-w-2xl px-4 py-5">
      <h1 className="font-display text-xl font-semibold text-ink">Mensagens</h1>

      {conversations.loading ? (
        <Spinner label="Abrindo conversas" />
      ) : conversations.error ? (
        <ErrorState message={conversations.error} onRetry={conversations.reload} />
      ) : (conversations.data?.items.length ?? 0) === 0 ? (
        <EmptyState
          title="Nenhuma conversa por enquanto."
          hint="Quando alguém puxar papo com você, aparece aqui."
        />
      ) : (
        <ul className="mt-4 divide-y divide-line overflow-hidden rounded-2xl border border-line bg-surface">
          {conversations.data?.items.map((conversation) => (
            <li key={conversation.id}>
              <Link
                to={`/messages/${conversation.id}`}
                className="flex items-center gap-3 px-4 py-3.5 transition hover:bg-paper"
              >
                <Avatar name={conversation.partner.name} photoUrl={conversation.partner.photo_url} />
                <div className="min-w-0 flex-1">
                  <div className="flex items-baseline justify-between gap-2">
                    <p className="truncate text-sm font-semibold text-ink">{conversation.partner.name}</p>
                    {conversation.last_message_at && (
                      <span className="shrink-0 text-xs text-ink-faint">
                        {relativeTime(conversation.last_message_at)}
                      </span>
                    )}
                  </div>
                  {conversation.last_message_preview && (
                    <p className="truncate text-xs text-ink-soft">{conversation.last_message_preview}</p>
                  )}
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
