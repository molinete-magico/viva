import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { ApiError, api } from '../../services/api'
import { Avatar } from '../../components/ui'
import type { Comment, LikeOut, Post } from '../../types/api'
import { relativeTime } from '../../utils/format'

export function PostCard({
  post,
  currentCharacterId,
  onChanged,
}: {
  post: Post
  currentCharacterId?: number
  onChanged: () => void
}) {
  const [liked, setLiked] = useState(post.liked_by_me)
  const [likes, setLikes] = useState(post.likes_count)
  const [togglingLike, setTogglingLike] = useState(false)
  const [showComments, setShowComments] = useState(false)
  const [comments, setComments] = useState<Comment[]>([])
  const [deletingComment, setDeletingComment] = useState<number | null>(null)

  async function toggleLike() {
    if (togglingLike) return
    setTogglingLike(true)
    try {
      const result = liked
        ? await api<LikeOut>(`/posts/${post.id}/like`, { method: 'DELETE' })
        : await api<LikeOut>(`/posts/${post.id}/like`, { method: 'POST' })
      setLiked(result.liked)
      setLikes(result.likes_count)
    } catch {
      // mantém o estado atual em falha de rede
    } finally {
      setTogglingLike(false)
    }
  }

  async function loadComments() {
    if (showComments && comments.length) return
    try {
      setComments(await api<Comment[]>(`/posts/${post.id}/comments`))
    } catch {
      setComments([])
    }
  }

  async function toggleComments() {
    const next = !showComments
    setShowComments(next)
    if (next) await loadComments()
  }

  async function addComment(content: string) {
    const created = await api<Comment>(`/posts/${post.id}/comments`, { method: 'POST', body: { content } })
    setComments((prev) => [...prev, created])
    onChanged()
  }

  async function removeComment(commentId: number) {
    setDeletingComment(commentId)
    try {
      await api(`/comments/${commentId}`, { method: 'DELETE' })
      setComments((prev) => prev.filter((c) => c.id !== commentId))
      onChanged()
    } catch {
      // ignora
    } finally {
      setDeletingComment(null)
    }
  }

  const isMine = currentCharacterId === post.author.id

  return (
    <article className="viva-post border-b border-line bg-transparent px-1 py-5 sm:px-2">
      <div className="flex items-start gap-3">
        <Avatar name={post.author.name} photoUrl={post.author.photo_url} />
        <div className="min-w-0 flex-1">
          <div className="flex items-center justify-between gap-2">
            <Link to={`/profile/${post.author.id}`} className="truncate text-[15px] font-bold text-ink hover:underline">
              {post.author.name}
            </Link>
            {isMine && (
              <button
                type="button"
                onClick={async () => {
                  if (!window.confirm('Apagar este post?')) return
                  try {
                    await api(`/posts/${post.id}`, { method: 'DELETE' })
                    onChanged()
                  } catch {
                    // ignora
                  }
                }}
                className="text-xs text-ink-faint transition hover:text-accent-deep"
              >
                Apagar
              </button>
            )}
          </div>
          <p className="truncate text-xs text-ink-soft">
            {post.author.profession_label || 'morador'} · {relativeTime(post.created_at)}
          </p>
        </div>
      </div>

      <p className="mt-3 whitespace-pre-wrap text-[15px] leading-[1.65] text-ink">{post.content}</p>

      <div className="mt-3 flex items-center gap-1">
        <button
          type="button"
          onClick={toggleLike}
          disabled={!currentCharacterId || togglingLike}
          aria-pressed={liked}
          className={`viva-action tap flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium transition disabled:opacity-40 ${
            liked ? 'bg-accent/15 text-accent-deep' : 'text-ink-soft hover:bg-paper hover:text-ink'
          }`}
        >
          <span aria-hidden>{liked ? '♥' : '♡'}</span>
          {likes} {likes === 1 ? 'curtida' : 'curtidas'}
        </button>
        <button
          type="button"
          onClick={toggleComments}
          aria-expanded={showComments}
          className="viva-action tap flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-ink-soft transition hover:bg-paper hover:text-ink"
        >
          <span aria-hidden>💬</span>
          {post.comments_count} {post.comments_count === 1 ? 'comentário' : 'comentários'}
        </button>
      </div>

      {showComments && currentCharacterId && (
        <div className="mt-3 rounded-xl bg-paper p-3">
          <CommentForm onSubmit={addComment} />
          {comments.length === 0 ? (
            <p className="mt-3 text-center text-xs text-ink-faint">Nenhum comentário ainda. Quebra a conversa.</p>
          ) : (
            <ul className="mt-3 space-y-3">
              {comments.map((comment) => (
                <li key={comment.id} className="flex items-start gap-2.5">
                  <Avatar name={comment.author.name} size="sm" photoUrl={comment.author.photo_url} />
                  <div className="min-w-0 flex-1">
                    <p className="text-xs text-ink">
                      <Link to={`/profile/${comment.author.id}`} className="font-semibold hover:underline">
                        {comment.author.name}
                      </Link>{' '}
                      <span className="text-ink-faint">· {relativeTime(comment.created_at)}</span>
                    </p>
                    <p className="mt-0.5 text-sm leading-relaxed text-ink">{comment.content}</p>
                  </div>
                  {currentCharacterId === comment.author.id && (
                    <button
                      type="button"
                      disabled={deletingComment === comment.id}
                      onClick={() => removeComment(comment.id)}
                      className="text-xs text-ink-faint transition hover:text-accent-deep disabled:opacity-40"
                    >
                      {deletingComment === comment.id ? '…' : 'Apagar'}
                    </button>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </article>
  )
}

export function CommentForm({ onSubmit }: { onSubmit: (content: string) => Promise<void> }) {
  const [content, setContent] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    if (!content.trim()) return
    setError(null)
    setSubmitting(true)
    try {
      await onSubmit(content)
      setContent('')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Não foi possível comentar agora.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex items-center gap-2">
      <input
        type="text"
        value={content}
        maxLength={2000}
        onChange={(e) => setContent(e.target.value)}
        placeholder="Comentar…"
        aria-label="Escrever um comentário"
        className="min-w-0 flex-1 rounded-full border border-line bg-surface px-4 py-2 text-sm text-ink placeholder:text-ink-faint focus:border-accent focus:outline-none"
      />
      {error && <p className="text-xs text-accent-deep">{error}</p>}
      <button
        type="submit"
        disabled={submitting || !content.trim()}
        className="tap shrink-0 rounded-full bg-accent px-4 py-2 text-sm font-semibold text-white transition hover:bg-accent-deep disabled:opacity-50"
      >
        Enviar
      </button>
    </form>
  )
}