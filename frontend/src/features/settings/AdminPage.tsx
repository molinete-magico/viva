import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../services/api'
import { ErrorState, Spinner, useFetch, WarningBanner } from '../../components/ui'
import type { Listing } from '../../types/api'

interface AdminCharacter {
  id: number
  name: string
  age: number
  bio: string
  profession_label: string
  is_npc: boolean
  discovered_level: number
  money: number
  current_location_id: number | null
}

interface AdminJob {
  id: number
  title: string
  salary_per_shift: number
}

const LEVEL_LABELS: Record<number, string> = { 1: 'rosto novo', 2: 'conhecido', 3: 'amigo da vila' }

export function AdminPage() {
  const characters = useFetch<Listing<AdminCharacter>>('/admin/characters')
  const jobs = useFetch<Listing<AdminJob>>('/admin/jobs')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  async function update(character: AdminCharacter, patch: Record<string, unknown>) {
    setBusy(true)
    setError('')
    try {
      await api(`/admin/characters/${character.id}`, { method: 'PATCH', body: patch })
      characters.reload()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Algo deu errado.')
    } finally {
      setBusy(false)
    }
  }

  async function runRoutines() {
    setBusy(true)
    setError('')
    setNotice('')
    try {
      const result = await api<{ summary: string; elapsed_minutes: number }>(`/admin/simulation/routines`, {
        method: 'POST',
      })
      setNotice(`${result.summary}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'A simulação falhou.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mx-auto max-w-2xl px-4 py-5">
      <Link to="/settings" className="text-xs font-medium text-accent-deep transition hover:underline">
        ‹ Configurações
      </Link>
      <h1 className="mt-2 font-display text-xl font-semibold text-ink">Painel da simulação</h1>

      {error && <div className="mt-3"><WarningBanner message={error} onClose={() => setError('')} /></div>}
      {notice && <div className="mt-3"><WarningBanner message={notice} onClose={() => setNotice('')} /></div>}

      <button
        type="button"
        disabled={busy}
        onClick={runRoutines}
        className="tap mt-4 w-full rounded-full bg-accent py-2.5 text-sm font-semibold text-white transition hover:opacity-90 disabled:opacity-40"
      >
        Rodar rotinas agora
      </button>

      <section className="mt-5 rounded-2xl border border-line bg-surface p-5">
        <h2 className="text-xs font-semibold uppercase tracking-wide text-ink-soft">
          Moradores · {characters.data?.items.length ?? '…'}
        </h2>
        {characters.loading ? (
          <Spinner />
        ) : characters.error ? (
          <ErrorState message={characters.error} onRetry={characters.reload} />
        ) : (
          <ul className="mt-3 space-y-2">
            {characters.data?.items.map((character) => (
              <li key={character.id} className="rounded-xl border border-line bg-paper p-3">
                <div className="flex items-center justify-between gap-2">
                  <p className="text-sm font-semibold text-ink">{character.name}</p>
                  <span className="text-xs text-ink-faint">
                    {character.is_npc ? 'morador' : 'você? não — jogador'}
                  </span>
                </div>
                <p className="mt-1 text-xs text-ink-soft">{character.profession_label || 'sem ocupação'}</p>
                <div className="mt-2 flex items-center gap-2 text-xs">
                  <span className="text-ink-faint">Nível:</span>
                  {(character.is_npc ? [1, 2, 3] : [character.discovered_level]).map((level) => (
                    <button
                      key={level}
                      type="button"
                      disabled={busy}
                      onClick={() => update(character, { discovered_level: level })}
                      className={`tap rounded-full px-2 py-0.5 transition ${
                        character.discovered_level === level
                          ? 'bg-sea-soft font-semibold text-sea'
                          : 'border border-line text-ink-faint hover:border-sea'
                      }`}
                    >
                      {level} · {LEVEL_LABELS[level]}
                    </button>
                  ))}
                </div>
                <div className="mt-2 flex items-center gap-2 text-xs">
                  <span className="text-ink-faint">Vivas:</span>
                  <span className="tabular-nums text-ink">{character.money}</span>
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => update(character, { money: (character.money ?? 0) + 100 })}
                    className="tap ml-auto rounded-full border border-line px-2 py-0.5 text-ink-soft transition hover:border-sea"
                  >
                    +100
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="mt-5 rounded-2xl border border-line bg-surface p-5">
        <h2 className="text-xs font-semibold uppercase tracking-wide text-ink-soft">Vagas e salários</h2>
        {jobs.data?.items.length ? (
          <ul className="mt-3 space-y-1.5">
            {jobs.data.items.map((job) => (
              <li key={job.id} className="flex items-center justify-between text-sm">
                <span className="text-ink">{job.title}</span>
                <span className="tabular-nums text-ink-faint">R$ {job.salary_per_shift}/turno</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-2 text-sm text-ink-faint">Sem vagas registradas.</p>
        )}
      </section>
    </div>
  )
}