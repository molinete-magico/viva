import { EmptyState, ErrorState, Spinner, useFetch } from '../../components/ui'
import type { Conversation, Listing } from '../../types/api'
import { relativeTime } from '../../utils/format'
import { Avatar } from '../../components/ui'
import { Link } from 'react-router-dom'

export function MessagesPage() {
  const conversations = useFetch<Listing<Conversation>>('/conversations')

  return (
    <div className="mx-auto max-w-2xl">
      <div><p className="viva-kicker text-accent">Caixa de entrada</p><h1 className="mt-1 font-display text-3xl font-black tracking-tight text-ink">Mensagens</h1><p className="mt-1 text-sm text-ink-soft">Conversas que continuam vivendo quando você sai.</p></div>

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
        <ul className="mt-5 divide-y divide-line border-y border-line">
          {conversations.data?.items.map((conversation) => (
            <li key={conversation.id}>
              <Link
                to={`/messages/${conversation.id}`}
                className="flex items-center gap-4 px-4 py-4 transition hover:bg-paper"
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
