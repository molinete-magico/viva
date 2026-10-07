import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Avatar, EmptyState, ErrorState, Spinner, useFetch } from '../../components/ui'
import type { Character, District, Listing, Location } from '../../types/api'

const KIND_LABELS: Record<string, string> = {
  restaurant: 'Restaurante',
  cafe: 'Café / bar',
  shop: 'Comércio',
  work: 'Trabalho',
  park: 'Parque',
  street: 'Rua / praça',
  arcade: 'Lazer',
}

export function ExplorePage() {
  const [tab, setTab] = useState<'people' | 'places'>('people')
  const [query, setQuery] = useState('')
  const [districtFilter, setDistrictFilter] = useState('')

  const characters = useFetch<Listing<Character>>('/characters')
  const districts = useFetch<Listing<District>>('/world/districts')
  const locations = useFetch<Listing<Location>>('/world/locations')

  const people = (characters.data?.items ?? []).filter((c) =>
    `${c.name} ${c.profession_label}`.toLowerCase().includes(query.trim().toLowerCase()),
  )

  const places = (locations.data?.items ?? []).filter((loc) =>
    districtFilter === '' || loc.district_name === districtFilter,
  )

  return (
    <div className="mx-auto max-w-2xl px-4 py-5">
      <h1 className="font-display text-xl font-semibold text-ink">Explorar a cidade</h1>

      <div className="mt-4 flex gap-1 rounded-full border border-line bg-surface p-1">
        <button
          type="button"
          onClick={() => setTab('people')}
          aria-pressed={tab === 'people'}
          className={`flex-1 rounded-full px-4 py-2 text-sm font-medium transition ${
            tab === 'people' ? 'bg-accent text-white' : 'text-ink-soft hover:text-ink'
          }`}
        >
          Moradores
        </button>
        <button
          type="button"
          onClick={() => setTab('places')}
          aria-pressed={tab === 'places'}
          className={`flex-1 rounded-full px-4 py-2 text-sm font-medium transition ${
            tab === 'places' ? 'bg-accent text-white' : 'text-ink-soft hover:text-ink'
          }`}
        >
          Lugares
        </button>
      </div>

      {tab === 'people' ? (
        <>
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Procurar por nome ou profissão"
            aria-label="Procurar moradores"
            className="auth-input mt-4"
          />

          {characters.loading ? (
            <Spinner label="Procurando gente" />
          ) : characters.error ? (
            <ErrorState message={characters.error} onRetry={characters.reload} />
          ) : people.length === 0 ? (
            <EmptyState
              title={query ? 'Ninguém com esse nome por aqui.' : 'Ainda não conhecemos ninguém.'}
              hint={query ? 'Tente outra palavra.' : 'Os moradores aparecem conforme a cidade ganha vida.'}
            />
          ) : (
            <ul className="mt-5 divide-y divide-line overflow-hidden rounded-2xl border border-line bg-surface">
              {people.map((character) => (
                <li key={character.id}>
                  <Link
                    to={`/profile/${character.id}`}
                    className="flex items-center gap-3 px-4 py-3.5 transition hover:bg-paper"
                  >
                    <Avatar name={character.name} photoUrl={character.photo_url} />
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-semibold text-ink">{character.name}</p>
                      <p className="truncate text-xs text-ink-soft">
                        {character.profession_label || (character.is_npc ? 'morador' : 'novo por aqui')}
                        {character.pronouns ? ` · ${character.pronouns}` : ''}
                      </p>
                    </div>
                    <span aria-hidden className="text-ink-faint">
                      ›
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </>
      ) : (
        <>
          {districts.data?.items.length ? (
            <div className="mt-4 flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => setDistrictFilter('')}
                className={`rounded-full border px-3 py-1.5 text-xs font-medium transition ${
                  districtFilter === ''
                    ? 'border-accent bg-accent/10 text-accent-deep'
                    : 'border-line bg-surface text-ink-soft hover:text-ink'
                }`}
              >
                Toda a cidade
              </button>
              {districts.data.items.map((district) => (
                <button
                  key={district.id}
                  type="button"
                  onClick={() => setDistrictFilter(district.name)}
                  className={`rounded-full border px-3 py-1.5 text-xs font-medium transition ${
                    districtFilter === district.name
                      ? 'border-accent bg-accent/10 text-accent-deep'
                      : 'border-line bg-surface text-ink-soft hover:text-ink'
                  }`}
                >
                  {district.name}
                </button>
              ))}
            </div>
          ) : null}

          {locations.loading ? (
            <Spinner label="Olhando o mapa" />
          ) : locations.error ? (
            <ErrorState message={locations.error} onRetry={locations.reload} />
          ) : places.length === 0 ? (
            <EmptyState title="Nenhum lugar aqui ainda." hint="A cidade cresce aos poucos." />
          ) : (
            <ul className="mt-5 space-y-3">
              {places.map((place) => (
                <li key={place.id} className="rounded-2xl border border-line bg-surface p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="font-display font-semibold text-ink">{place.name}</p>
                      <p className="text-xs text-ink-soft">
                        {KIND_LABELS[place.kind] ?? place.kind} · {place.district_name}
                      </p>
                    </div>
                    <span className="rounded-full bg-accent/10 px-2.5 py-1 text-[11px] font-medium text-accent-deep">
                      {place.opening_hours?.ranges?.[0]?.join(' às ')}
                    </span>
                  </div>
                  <p className="mt-2 text-sm leading-relaxed text-ink">{place.description}</p>
                  {place.activities.length ? (
                    <div className="mt-3 flex flex-wrap gap-1.5">
                      {place.activities.map((activity) => (
                        <span
                          key={activity}
                          className="rounded-full border border-line bg-paper px-2.5 py-1 text-[11px] text-ink-soft"
                        >
                          {activity}
                        </span>
                      ))}
                    </div>
                  ) : null}
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </div>
  )
}