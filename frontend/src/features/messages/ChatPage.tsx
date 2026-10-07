import { useEffect, useRef, useState } from 'react'
import { Link, Navigate, useParams } from 'react-router-dom'
import { ApiError, api } from '../../services/api'
import { Avatar, ErrorState, Spinner, WarningBanner, useFetch } from '../../components/ui'
import type { ConversationDetail, Message, MessageList, SendMessageResponse } from '../../types/api'
import { relativeTime } from '../../utils/format'

export function ChatPage() {
  const { conversationId } = useParams()
  const numericId = Number(conversationId)
  const detail = useFetch<ConversationDetail>(`/conversations/${numericId}`, [conversationId])
  const fetched = useFetch<MessageList>(`/conversations/${numericId}/messages`, [conversationId])
  const [chat, setChat] = useState<Message[]>([])
  const [draft, setDraft] = useState('')
  const [sending, setSending] = useState(false)
  const [warning, setWarning] = useState<string | null>(null)
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (fetched.data) setChat(fetched.data.items)
  }, [fetched.data])

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chat.length, sending])

  if (!Number.isFinite(numericId)) return <Navigate to="/messages" replace />

  if (detail.loading || fetched.loading) return <Spinner label="Abrindo conversa" />
  if (detail.error || fetched.error) {
    const err = detail.error ?? fetched.error
    return (
      <ErrorState
        message={err ?? 'Algo deu errado.'}
        onRetry={() => {
          detail.reload()
          fetched.reload()
        }}
      />
    )
  }
  if (!detail.data) return <ErrorState message="Conversa não encontrada." />

  const partner = detail.data.partner

  async function handleSend() {
    const content = draft.trim()
    if (!content || sending) return
    setSending(true)
    setWarning(null)
    const optimistic: Message = {
      id: -Date.now(),
      conversation_id: numericId,
      sender_character_id: 0,
      content,
      created_at: new Date().toISOString(),
      is_mine: true,
    }
    setChat((previous) => [...previous, optimistic])
    try {
      const result = await api<SendMessageResponse>(`/conversations/${numericId}/messages`, {
        method: 'POST',
        body: { content },
      })
      if (result.npc_reply) {
        setChat((previous) => [...previous, result.npc_reply!])
      }
      if (result.warning) setWarning(result.warning)
      setDraft('')
    } catch (err) {
      const message = err instanceof ApiError ? err.message : 'Não deu para enviar. Tente de novo.'
      setWarning(message)
      fetched.reload()
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="mx-auto flex h-[calc(100dvh-3.5rem)] w-full max-w-2xl flex-col px-4 pb-4 pt-2">
      <div className="flex items-center gap-3 border-b border-line pb-2">
        <Link to="/messages" className="tap rounded-full px-2 text-sm text-ink-soft transition hover:bg-surface" aria-label="Voltar">
          ‹
        </Link>
        <Avatar name={partner.name} photoUrl={partner.photo_url} />
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-ink">{partner.name}</p>
          <p className="truncate text-xs text-ink-soft">{partner.profession_label || 'morador(a) da Vila Serena'}</p>
        </div>
      </div>

      {warning && (
        <div className="mt-3">
          <WarningBanner message={warning} onClose={() => setWarning(null)} />
        </div>
      )}

      <div className="flex-1 space-y-3 overflow-y-auto py-4">
        {chat.map((message) => (
          <div key={message.id} className={`flex ${message.is_mine ? 'justify-end' : 'justify-start'}`}>
            <div
              className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed shadow-sm ${
                message.is_mine ? 'rounded-br-md bg-accent text-white' : 'rounded-bl-md bg-surface text-ink'
              }`}
            >
              <p>{message.content}</p>
              <p className={`mt-1 text-[10px] ${message.is_mine ? 'text-white/70' : 'text-ink-faint'}`}>
                {relativeTime(message.created_at)}
              </p>
            </div>
          </div>
        ))}
        <div ref={endRef} />
      </div>

      <form
        onSubmit={(event) => {
          event.preventDefault()
          void handleSend()
        }}
        className="flex items-end gap-2 border-t border-line pt-3"
      >
        <textarea
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          rows={1}
          placeholder={`Escrever para ${partner.name}…`}
          className="min-h-[2.75rem] max-h-32 flex-1 resize-none rounded-2xl border border-line bg-surface px-4 py-2 text-sm text-ink transition focus:border-accent focus:outline-none"
        />
        <button
          type="submit"
          disabled={sending || !draft.trim()}
          className="tap rounded-full bg-accent px-5 text-sm font-semibold text-white transition hover:bg-accent-deep disabled:opacity-50"
        >
          {sending ? '…' : 'Enviar'}
        </button>
      </form>
    </div>
  )
}