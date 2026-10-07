import { useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { api, ApiError } from '../services/api'

interface State<T> {
  data: T | null
  error: string | null
  loading: boolean
  reload: () => void
}

export function useFetch<T>(path: string, deps: unknown[] = []): State<T> {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [version, setVersion] = useState(0)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    api<T>(path)
      .then((result) => {
        if (!cancelled) setData(result)
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(err instanceof ApiError ? err.message : 'Algo deu errado. Tente novamente.')
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path, version, ...deps])

  return {
    data,
    error,
    loading,
    reload: () => setVersion((v) => v + 1),
  }
}

export function Spinner({ label = 'Carregando' }: { label?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-14 text-ink-soft" role="status">
      <span className="h-7 w-7 animate-spin rounded-full border-[3px] border-line border-t-accent" />
      <span className="text-sm">{label}…</span>
    </div>
  )
}

export function EmptyState({ title, hint, action }: { title: string; hint?: string; action?: ReactNode }) {
  return (
    <div className="mx-auto max-w-md px-6 py-16 text-center">
      <div className="mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-full bg-accent-soft text-2xl" aria-hidden>
        ☕
      </div>
      <h2 className="font-display text-xl text-ink">{title}</h2>
      {hint && <p className="mt-2 text-sm leading-relaxed text-ink-soft">{hint}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  )
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="mx-auto max-w-md px-6 py-14 text-center" role="alert">
      <p className="text-sm leading-relaxed text-ink-soft">{message}</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="tap mt-5 rounded-full bg-ink px-6 text-sm font-medium text-paper transition hover:bg-ink/85"
        >
          Tentar novamente
        </button>
      )}
    </div>
  )
}

export function WarningBanner({ message, onClose }: { message: string; onClose?: () => void }) {
  return (
    <div
      role="alert"
      className="flex items-start gap-3 rounded-xl border border-warn/40 bg-warn-soft px-4 py-3 text-sm text-warn"
    >
      <span className="mt-0.5 shrink-0 text-base" aria-hidden>
        ⚠️
      </span>
      <p className="flex-1 leading-relaxed">{message}</p>
      {onClose && (
        <button
          type="button"
          onClick={onClose}
          aria-label="Fechar aviso"
          className="shrink-0 rounded-full px-2 text-warn/70 transition hover:bg-warn/20 hover:text-warn"
        >
          ✕
        </button>
      )}
    </div>
  )
}

export function Avatar({
  name,
  size = 'md',
  photoUrl,
}: {
  name: string
  size?: 'sm' | 'md' | 'lg'
  photoUrl?: string | null
}) {
  const initial = name.trim().charAt(0).toUpperCase() || '?'
  const classes =
    size === 'sm'
      ? 'h-9 w-9 text-sm'
      : size === 'lg'
        ? 'h-16 w-16 text-2xl'
        : 'h-11 w-11 text-lg'
  if (photoUrl) {
    return (
      <img
        src={photoUrl}
        alt={`Avatar de ${name}`}
        className={`${classes} shrink-0 rounded-full object-cover ring-1 ring-accent/20`}
      />
    )
  }
  return (
    <span
      aria-hidden
      className={`${classes} inline-flex shrink-0 items-center justify-center rounded-full bg-accent-soft font-semibold text-accent-deep ring-1 ring-accent/20`}
    >
      {initial}
    </span>
  )
}
