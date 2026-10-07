import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import { ApiError, api } from '../../services/api'
import { EmptyState, ErrorState, Spinner, useFetch } from '../../components/ui'
import type { FeedResponse } from '../../types/api'
import { PostCard } from './PostCard'

export function FeedPage() {
  const { character } = useAuth()
  const [scope, setScope] = useState<'all' | 'following'>('all')
  const feed = useFetch<FeedResponse>(`/feed?scope=${scope}`, [scope])

  return (
    <div className="mx-auto max-w-2xl px-4 py-5">
      {!character && (
        <Link
          to="/onboarding"
          className="mb-5 flex items-center justify-between gap-3 rounded-2xl border border-accent/30 bg-accent-soft px-4 py-3.5 text-sm text-accent-deep transition hover:border-accent/50"
        >
          <span>
            <strong className="font-semibold">Crie seu personagem</strong> para viver a cidade e publicar posts.
          </span>
          <span aria-hidden>→</span>
        </Link>
      )}

      {character && <Composer onPosted={feed.reload} />}

      <div className="mt-2 flex gap-1 rounded-full border border-line bg-surface p-1">
        <button
          type="button"
          onClick={() => setScope('all')}
          aria-pressed={scope === 'all'}
          className={`flex-1 rounded-full px-4 py-2 text-sm font-medium transition ${
            scope === 'all' ? 'bg-accent text-white' : 'text-ink-soft hover:text-ink'
          }`}
        >
          Tudo
        </button>
        <button
          type="button"
          onClick={() => setScope('following')}
          aria-pressed={scope === 'following'}
          className={`flex-1 rounded-full px-4 py-2 text-sm font-medium transition ${
            scope === 'following' ? 'bg-accent text-white' : 'text-ink-soft hover:text-ink'
          }`}
        >
          Seguindo
        </button>
      </div>

      {feed.loading ? (
        <Spinner label="Carregando o feed" />
      ) : feed.error ? (
        <ErrorState message={feed.error} onRetry={feed.reload} />
      ) : (feed.data?.items.length ?? 0) === 0 ? (
        <EmptyState
          title={scope === 'following' ? 'Você ainda não segue ninguém.' : 'A cidade está tranquila hoje.'}
          hint={
            scope === 'following'
              ? 'Explore os moradores e siga quem você gosta.'
              : 'Talvez alguma coisa aconteça mais tarde.'
          }
        />
      ) : (
        <ul className="mt-3 space-y-3">
          {feed.data?.items.map((post) => (
            <li key={post.id}>
              <PostCard post={post} currentCharacterId={character?.id} onChanged={feed.reload} />
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function Composer({ onPosted }: { onPosted: () => void }) {
  const [content, setContent] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    if (!content.trim()) return
    setError(null)
    setSubmitting(true)
    try {
      await api('/posts', { method: 'POST', body: { content } })
      setContent('')
      onPosted()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Não foi possível publicar agora.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form onSubmit={onSubmit} className="mb-5 rounded-2xl border border-line bg-surface p-4">
      <label className="sr-only" htmlFor="composer">
        O que está acontecendo?
      </label>
      <textarea
        id="composer"
        rows={3}
        maxLength={5000}
        value={content}
        onChange={(e) => setContent(e.target.value)}
        placeholder="O que está acontecendo na cidade?"
        className="w-full resize-none bg-transparent text-[15px] leading-relaxed text-ink placeholder:text-ink-faint focus:outline-none"
      />
      {error && (
        <p className="mb-2 text-sm text-accent-deep" role="alert">
          {error}
        </p>
      )}
      <div className="flex justify-end">
        <button
          type="submit"
          disabled={submitting || !content.trim()}
          className="tap rounded-full bg-accent px-5 py-2 text-sm font-semibold text-white transition hover:bg-accent-deep disabled:opacity-50"
        >
          {submitting ? 'Publicando…' : 'Publicar'}
        </button>
      </div>
    </form>
  )
}