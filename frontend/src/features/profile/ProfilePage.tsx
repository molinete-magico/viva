import { useState } from 'react'
import { Link, Navigate, useNavigate, useParams } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import { ApiError, api } from '../../services/api'
import { Avatar, ErrorState, Spinner, useFetch } from '../../components/ui'
import { PostCard } from '../feed/PostCard'
import type { CharacterDetail, FeedResponse, FollowOut } from '../../types/api'

const LEVEL_LABELS: Record<number, string> = {
  1: 'rosto novo na cidade',
  2: 'um conhecido para você',
  3: 'amigo da Vila Serena',
}

export function OwnProfileRedirect() {
  const { character, loading } = useAuth()
  if (loading) return <Spinner label="Abrindo seu perfil" />
  if (!character) return <Navigate to="/onboarding" replace />
  return <Navigate to={`/profile/${character.id}`} replace />
}

export function ProfilePage() {
  const { characterId } = useParams()
  const navigate = useNavigate()
  const { character: ownCharacter } = useAuth()
  const numericId = Number(characterId)
  const detail = useFetch<CharacterDetail>(`/characters/${numericId}`, [characterId])
  const posts = useFetch<FeedResponse>(`/characters/${numericId}/posts`, [characterId])
  const [followBusy, setFollowBusy] = useState(false)
  const [dmBusy, setDmBusy] = useState(false)

  if (!Number.isFinite(numericId)) return <Navigate to="/feed" replace />

  if (detail.loading) return <Spinner label="Carregando perfil" />
  if (detail.error) return <ErrorState message={detail.error} onRetry={detail.reload} />
  if (!detail.data) return <ErrorState message="Perfil não encontrado." />

  const person = detail.data

  async function toggleFollow() {
    if (followBusy || !ownCharacter) return
    setFollowBusy(true)
    try {
      if (person.is_following) {
        const result = await api<FollowOut>(`/characters/${person.id}/follow`, { method: 'DELETE' })
        if (!result.following) detail.reload()
      } else {
        const result = await api<FollowOut>(`/characters/${person.id}/follow`, { method: 'POST' })
        if (result.following) detail.reload()
      }
    } catch (err) {
      alert(err instanceof ApiError ? err.message : 'Não rolou. Tente de novo.')
    } finally {
      setFollowBusy(false)
    }
  }

  async function startDm() {
    if (dmBusy || !ownCharacter) return
    setDmBusy(true)
    try {
      const conversation = await api<{ id: number }>(`/characters/${person.id}/dm`, { method: 'POST' })
      navigate(`/messages/${conversation.id}`)
    } catch (err) {
      alert(err instanceof ApiError ? err.message : 'Não rolou. Tente de novo.')
    } finally {
      setDmBusy(false)
    }
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-6 lg:px-0">
      <div className="viva-panel overflow-hidden rounded-3xl border border-line bg-surface">
        <div className="viva-profile-cover viva-grid-noise h-28 sm:h-36" />
        <div className="relative px-5 pb-5 sm:px-7">
          <div className="-mt-10 flex items-end justify-between gap-4">
            <Avatar name={person.name} size="lg" photoUrl={person.photo_url} />
            {!person.is_me && ownCharacter && <div className="flex gap-2">
              <button type="button" onClick={toggleFollow} disabled={followBusy} className={`tap rounded-full border px-5 text-sm font-bold transition disabled:opacity-50 ${person.is_following ? 'border-line bg-surface text-ink hover:border-accent/40' : 'border-accent bg-accent text-white hover:bg-accent-deep'}`}>
                {followBusy ? '…' : person.is_following ? 'Seguindo' : 'Seguir'}
              </button>
              {person.is_npc && <button type="button" onClick={startDm} disabled={dmBusy} className="tap rounded-full border border-line bg-surface px-4 text-sm font-bold text-ink transition hover:border-accent/40 disabled:opacity-50" aria-label="Conversar">Mensagem</button>}
            </div>}
          </div>
          <div className="mt-3">
            <p className="viva-kicker text-accent">{person.is_npc ? 'Morador da cidade' : 'Perfil'}</p>
            <h1 className="mt-1 font-display text-3xl font-black tracking-tight text-ink">{person.name}</h1>
            <p className="mt-1 text-sm text-ink-soft">@{person.name.toLowerCase().replace(/\\s+/g, '_')} · {person.profession_label || 'morador'}{person.pronouns ? ` · ${person.pronouns}` : ''}</p>
          </div>
          <Avatar name={person.name} size="lg" photoUrl={person.photo_url} />
          <div className="min-w-0">
            <h1 className="truncate font-display text-2xl font-semibold text-ink">{person.name}</h1>
            <p className="text-sm text-ink-soft">
              {person.profession_label || 'morador'}
              {person.pronouns ? ` · ${person.pronouns}` : ''} · {person.age} anos
            </p>
            {person.is_npc && (
              <p className="mt-1 inline-flex rounded-full bg-sea-soft px-2.5 py-0.5 text-[11px] font-medium text-sea">
                {LEVEL_LABELS[person.discovered_level] ?? 'rosto novo na cidade'}
              </p>
            )}
          </div>
        </div>

        {person.bio && <p className="mt-4 text-[15px] leading-relaxed text-ink">{person.bio}</p>}

        <dl className="mt-5 grid grid-cols-3 border-y border-line py-4 text-left">
          <div className="px-2 py-1">
            <dt className="text-xs text-ink-soft">Posts</dt>
            <dd className="text-lg font-semibold text-ink">{person.stats.posts}</dd>
          </div>
          <div className="rounded-xl bg-paper px-2 py-3">
            <dt className="text-xs text-ink-soft">Seguidores</dt>
            <dd className="text-lg font-semibold text-ink">{person.stats.followers}</dd>
          </div>
          <div className="rounded-xl bg-paper px-2 py-3">
            <dt className="text-xs text-ink-soft">Seguindo</dt>
            <dd className="text-lg font-semibold text-ink">{person.stats.following}</dd>
          </div>
        </dl>

        {person.is_me && person.money !== null && (
          <p className="mt-4 rounded-xl bg-sea-soft px-4 py-3 text-sm text-sea">
            No bolso: <strong>R$ {person.money.toFixed(2).replace('.', ',')}</strong>
          </p>
        )}
      </div>

      {person.is_me && (
        <div className="mt-4 space-y-3">
          {person.hobbies.length > 0 && (
            <div className="rounded-2xl border border-line bg-surface p-4">
              <h2 className="text-xs font-semibold uppercase tracking-wide text-ink-soft">Seus interesses</h2>
              <ul className="mt-2 flex flex-wrap gap-2">
                {person.hobbies.map((hobby) => (
                  <li key={hobby} className="rounded-full bg-accent-soft px-3 py-1 text-xs text-accent-deep">
                    {hobby}
                  </li>
                ))}
              </ul>
            </div>
          )}
          <div className="flex flex-wrap gap-3">
            <Link
              to="/settings"
              className="tap inline-flex items-center rounded-full border border-line bg-surface px-5 text-sm font-medium text-ink transition hover:border-ink/30"
            >
              Configurações
            </Link>
          </div>
        </div>
      )}

      {!person.is_me && ownCharacter && false && (
        <div className="mt-4 space-y-3">
          <button
            type="button"
            onClick={toggleFollow}
            disabled={followBusy}
            className={`tap w-full rounded-full px-5 py-2.5 text-sm font-semibold transition disabled:opacity-50 ${
              person.is_following
                ? 'border border-line bg-surface text-ink hover:border-accent/40 hover:text-accent-deep'
                : 'bg-accent text-white hover:bg-accent-deep'
            }`}
          >
            {followBusy ? '…' : person.is_following ? 'Seguindo' : 'Seguir'}
          </button>
          {person.is_npc && (
            <button
              type="button"
              onClick={startDm}
              disabled={dmBusy}
              className="tap w-full rounded-full border border-sea/40 bg-sea-soft px-5 py-2.5 text-sm font-semibold text-sea transition hover:border-sea hover:bg-sea/10 disabled:opacity-50"
            >
              {dmBusy ? 'Abrindo…' : 'Conversar'}
            </button>
          )}
        </div>
      )}

      {!person.is_me && !ownCharacter && (
        <p className="mt-4 text-center text-xs text-ink-faint">
          Você ainda não conhece {person.name} direito. Isso muda com o tempo.
        </p>
      )}

      <section className="mt-6">
        <h2 className="viva-kicker text-ink-soft">Publicações</h2>
        {posts.loading ? (
          <Spinner label="Carregando publicações" />
        ) : posts.error ? (
          <ErrorState message={posts.error} onRetry={posts.reload} />
        ) : (posts.data?.items.length ?? 0) === 0 ? (
          <p className="mt-3 rounded-2xl border border-line bg-surface px-4 py-6 text-center text-sm text-ink-faint">
            {person.is_me ? 'Você ainda não publicou nada.' : `${person.name} ainda não publicou nada.`}
          </p>
        ) : (
          <ul className="mt-3 space-y-3">
            {posts.data?.items.map((post) => (
              <li key={post.id}>
                <PostCard post={post} currentCharacterId={ownCharacter?.id} onChanged={posts.reload} />
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  )
}
