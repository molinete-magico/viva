import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../services/api'
import { ErrorState, Spinner, useFetch, WarningBanner } from '../../components/ui'
import type { CatchUpReport, CityPulse, Listing, SimulationLog } from '../../types/api'

export function WorldPage() {
  const report = useFetch<Listing<SimulationLog>>('/world/catchup-report')
  const pulse = useFetch<CityPulse>('/world/city-pulse')
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')


  async function advance() {
    setBusy(true)
    setError('')
    setNotice('')
    try {
      const result = await api<CatchUpReport>('/simulation/catchup?minutes=1440&with_social=true', {
        method: 'POST',
      })
      setNotice(`${result.summary}`)
      report.reload()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'A cidade não respondeu agora.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mx-auto max-w-2xl px-4 py-6">
      <div className="rounded-3xl border border-line bg-surface p-6">
        <p className="text-xs font-semibold uppercase tracking-widest text-accent">Vila Serena</p>
        <h1 className="mt-2 font-display text-4xl font-semibold text-ink">O que está rolando</h1>
        <p className="mt-2 max-w-xl text-sm leading-relaxed text-ink-soft">Não existe uma agenda para seguir. A cidade continua produzindo conversas, posts, encontros e situações que você pode entrar e viver quando quiser.</p>
      </div>

      {error && <div className="mt-3"><WarningBanner message={error} onClose={() => setError('')} /></div>}
      {notice && <div className="mt-3"><WarningBanner message={notice} onClose={() => setNotice('')} /></div>}

      <div className="mt-4 rounded-2xl border border-line bg-surface p-4">
        <h2 className="text-xs font-semibold uppercase tracking-wide text-ink-soft">Como anda a cidade</h2>
        <p className="mt-2 text-sm leading-relaxed text-ink-soft">
          A cidade não espera você para ter assunto. Atualize quando quiser para descobrir novas situações e consequências sociais.
        </p>
        <button
          type="button"
          disabled={busy}
          onClick={advance}
          className="tap mt-3 w-full rounded-full bg-accent py-2.5 text-sm font-semibold text-white transition hover:opacity-90 disabled:opacity-40"
        >
          {busy ? 'Atualizando…' : 'Ver o que mudou'}
        </button>
      </div>

      <section className="mt-4 rounded-2xl border border-line bg-surface p-4">
        <h2 className="text-xs font-semibold uppercase tracking-wide text-ink-soft">Pulso da cidade</h2>
        {pulse.loading ? (
          <Spinner label="Medindo a movimentação" />
        ) : pulse.data ? (
          <>
            <p className="mt-2 text-sm text-ink">{pulse.data.social_weather} <span className="text-ink-faint">({pulse.data.resident_count} moradores em movimento · {pulse.data.activity_count} sinais recentes)</span></p>
            <div className="mt-3 grid grid-cols-2 gap-2">
              {pulse.data.hot_locations.slice(0, 4).map((place) => (
                <div key={place.location_id} className="rounded-xl bg-paper px-3 py-2">
                  <p className="text-sm font-medium text-ink">{place.location_name}</p>
                  <p className="text-xs text-ink-faint">{place.resident_count} morador(es)</p>
                </div>
              ))}
            </div>
          </>
        ) : <p className="mt-2 text-sm text-ink-faint">O pulso ainda não foi calculado.</p>}
      </section>

      <section className="mt-4 rounded-2xl border border-line bg-surface p-4">
        <h2 className="text-xs font-semibold uppercase tracking-wide text-ink-soft">Enquanto você estava fora</h2>
        {pulse.loading ? (
          <Spinner label="Reconstruindo o que aconteceu" />
        ) : pulse.data ? (
          <div className="mt-3 space-y-3">
            {pulse.data.social_highlights.slice(0, 4).map((item) => (
              <div key={`${item.character_id}-${item.occurred_at}-${item.kind}`} className="border-l-2 border-accent pl-3">
                <p className="text-sm text-ink"><strong>{item.character_name}</strong> — {item.content}</p>
              </div>
            ))}
            {pulse.data.recent_posts.slice(0, 3).map((post) => (
              <div key={post.id} className="border-t border-line pt-2">
                <p className="text-xs font-medium text-ink-soft">{post.author_name} · {post.kind}</p>
                <p className="mt-1 text-sm text-ink">{post.content}</p>
              </div>
            ))}
            {!pulse.data.social_highlights.length && !pulse.data.recent_posts.length && (
              <p className="text-sm text-ink-faint">A cidade esteve quieta por enquanto.</p>
            )}
          </div>
        ) : (
          <p className="mt-2 text-sm text-ink-faint">O pulso da cidade ainda não foi calculado.</p>
        )}
      </section>

      <section className="mt-4 rounded-2xl border border-line bg-surface p-4">
        <h2 className="text-xs font-semibold uppercase tracking-wide text-ink-soft">Diário da cidade</h2>
        {report.loading ? (
          <Spinner label="Lendo o diário da vila" />
        ) : (report.data?.items.length ?? 0) === 0 ? (
          <p className="mt-2 text-sm text-ink-faint">Ainda não há relatórios de rotina.</p>
        ) : (
          <ul className="mt-2 space-y-2">
            {report.data?.items.map((log) => (
              <li key={log.id} className="text-sm text-ink-soft">
                <span className="font-medium text-ink">{log.summary}</span>
                <span className="block text-xs text-ink-faint">
                  {new Date(log.ran_at).toLocaleString('pt-BR', {
                    day: 'numeric',
                    month: 'short',
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </span>
              </li>
            ))}
          </ul>
        )}
        <Link
          to="/settings/world/relationships"
          className="tap mt-3 inline-block text-xs font-medium text-accent-deep transition hover:underline"
        >
          Ver relações, memórias e marcos da história ›
        </Link>
      </section>
    </div>
  )
}