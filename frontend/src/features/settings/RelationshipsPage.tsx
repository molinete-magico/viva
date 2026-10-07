import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import { api } from '../../services/api'
import { EmptyState, ErrorState, Spinner, useFetch, WarningBanner } from '../../components/ui'
import type { Listing, MemoryItem, MilestoneItem, RelationshipItem } from '../../types/api'
import { relativeTime } from '../../utils/format'

const DIMS: { key: keyof RelationshipItem; label: string }[] = [
  { key: 'familiarity', label: 'Familiaridade' },
  { key: 'friendship', label: 'Amizade' },
  { key: 'trust', label: 'Confiança' },
  { key: 'romance', label: 'Romance' },
  { key: 'respect', label: 'Respeito' },
  { key: 'tension', label: 'Tensão' },
]

const MILESTONE_REWARD = 80

export function RelationshipsPage() {
  const { character } = useAuth()
  const relationships = useFetch<Listing<RelationshipItem>>('/relationships')
  const memories = useFetch<Listing<MemoryItem>>(character ? `/characters/${character.id}/memories` : '', [character?.id])
  const milestones = useFetch<Listing<MilestoneItem>>('/milestones')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  async function claim(key: string) {
    setBusy(true)
    setError('')
    setNotice('')
    try {
      const result = await api<{ reward: number; name: string }>(`/milestones/${key}/claim`, { method: 'POST' })
      setNotice(`${result.name}: +${result.reward} Vivas para você.`)
      milestones.reload()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Não deu para resgatar agora.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mx-auto max-w-2xl px-4 py-5">
      <Link to="/settings" className="text-xs font-medium text-accent-deep transition hover:underline">
        ‹ Configurações
      </Link>
      <h1 className="mt-2 font-display text-xl font-semibold text-ink">Mundo, relações & memórias</h1>

      {error && <div className="mt-3"><WarningBanner message={error} onClose={() => setError('')} /></div>}
      {notice && <div className="mt-3"><WarningBanner message={notice} onClose={() => setNotice('')} /></div>}

      <section className="mt-5 rounded-2xl border border-line bg-surface p-5">
        <h2 className="text-xs font-semibold uppercase tracking-wide text-ink-soft">Marcos da história</h2>
        {milestones.loading ? (
          <Spinner label="Consultando marcos" />
        ) : milestones.error ? (
          <ErrorState message={milestones.error} onRetry={milestones.reload} />
        ) : (
          <ul className="mt-3 space-y-3">
            {(milestones.data?.items ?? []).map((milestone) => {
              const progress = Math.min(100, Math.round((milestone.count / milestone.threshold) * 100))
              return (
                <li key={milestone.key} className="rounded-xl border border-line bg-paper p-3">
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-sm font-semibold text-ink">{milestone.name}</p>
                    <span className="text-xs tabular-nums text-ink-faint">
                      {milestone.count}/{milestone.threshold}
                    </span>
                  </div>
                  <p className="mt-1 text-xs text-ink-soft">{milestone.description}</p>
                  <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-line">
                    <div className="h-full rounded-full bg-accent" style={{ width: `${progress}%` }} />
                  </div>
                  {milestone.pending && (
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => claim(milestone.key)}
                      className="tap mt-3 w-full rounded-full bg-accent py-2 text-xs font-semibold text-white transition hover:opacity-90 disabled:opacity-40"
                    >
                      Resgatar oportunidade (+{MILESTONE_REWARD} Vivas)
                    </button>
                  )}
                </li>
              )
            })}
          </ul>
        )}
      </section>

      <section className="mt-5 rounded-2xl border border-line bg-surface p-5">
        <h2 className="text-xs font-semibold uppercase tracking-wide text-ink-soft">Laços que você formou</h2>
        {relationships.loading ? (
          <Spinner label="Consultando laços" />
        ) : relationships.error ? (
          <ErrorState message={relationships.error} onRetry={relationships.reload} />
        ) : (relationships.data?.items.length ?? 0) === 0 ? (
          <EmptyState title="Você ainda não tem laços." hint="Converse, publique e apareça nos eventos — a cidade responde." />
        ) : (
          <ul className="mt-3 space-y-3">
            {relationships.data?.items.map((relationship) => (
              <li key={relationship.id} className="rounded-xl border border-line bg-paper p-3">
                <div className="flex items-center justify-between gap-3">
                  <Link
                    to={`/profile/${relationship.other_character_id}`}
                    className="text-sm font-semibold text-ink transition hover:opacity-75"
                  >
                    {relationship.other_name}
                  </Link>
                  {relationship.last_interaction_at && (
                    <span className="text-xs text-ink-faint">visto {relativeTime(relationship.last_interaction_at)}</span>
                  )}
                </div>
                <dl className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1.5">
                  {DIMS.map((dim) => (
                    <div key={dim.key}>
                      <dt className="text-[11px] text-ink-faint">{dim.label}</dt>
                      <dd className="h-1 mt-0.5 w-full overflow-hidden rounded-full bg-line">
                        <span
                          className="block h-full rounded-full"
                          style={{
                            width: `${relationship[dim.key]}%`,
                            backgroundColor: dim.key === 'tension' ? 'var(--color-warn)' : 'var(--color-sea)',
                          }}
                        />
                      </dd>
                    </div>
                  ))}
                </dl>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="mt-5 rounded-2xl border border-line bg-surface p-5">
        <h2 className="text-xs font-semibold uppercase tracking-wide text-ink-soft">Suas memórias</h2>
        {memories.loading ? (
          <Spinner label="Revirando lembranças" />
        ) : memories.error ? (
          <ErrorState message={memories.error} onRetry={memories.reload} />
        ) : (memories.data?.items.length ?? 0) === 0 ? (
          <EmptyState title="Nenhuma memória guardada ainda." hint="Momentos vividos na Vila Serena aparecem aqui." />
        ) : (
          <ul className="mt-3 space-y-2">
            {memories.data?.items.map((memory) => (
              <li key={memory.id} className="rounded-xl border border-line bg-paper px-3 py-2.5">
                <p className="text-sm leading-relaxed text-ink">{memory.content}</p>
                <p className="mt-1 text-xs text-ink-faint">
                  {memory.other_name ? `com ${memory.other_name} · ` : ''}
                  {memory.category.toLowerCase()} · {relativeTime(memory.occurred_at)}
                </p>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  )
}