import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'

export function SettingsPage() {
  const { user, character, logout } = useAuth()
  const navigate = useNavigate()

  return (
    <div className="mx-auto max-w-2xl px-4 py-6">
      <h1 className="font-display text-xl font-semibold text-ink">Configurações</h1>

      <section className="mt-5 rounded-2xl border border-line bg-surface p-5">
        <h2 className="text-xs font-semibold uppercase tracking-wide text-ink-soft">Conta</h2>
        <dl className="mt-3 space-y-2 text-sm">
          <div className="flex justify-between gap-3">
            <dt className="text-ink-soft">E-mail</dt>
            <dd className="truncate font-medium text-ink">{user?.email}</dd>
          </div>
          <div className="flex justify-between gap-3">
            <dt className="text-ink-soft">Personagem</dt>
            <dd className="font-medium text-ink">{character?.name ?? 'ainda não criado'}</dd>
          </div>
          <div className="flex justify-between gap-3">
            <dt className="text-ink-soft">Permissão</dt>
            <dd className="font-medium text-ink">{user?.is_admin ? 'administrador' : 'morador'}</dd>
          </div>
        </dl>
      </section>

      <section className="mt-4 rounded-2xl border border-line bg-surface p-5">
        <h2 className="text-xs font-semibold uppercase tracking-wide text-ink-soft">Simulação</h2>
        <p className="mt-2 text-sm leading-relaxed text-ink-soft">
          Veja o que os moradores estão fazendo, descubra novas cenas e acompanhe relações, memórias e consequências sociais.
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          <Link
            to="/world"
            className="tap rounded-full border border-line bg-paper px-4 py-2 text-sm font-medium text-ink transition hover:border-accent/40"
          >
            Vida da cidade
          </Link>
          <Link
            to="/settings/world/relationships"
            className="tap rounded-full border border-line bg-paper px-4 py-2 text-sm font-medium text-ink transition hover:border-accent/40"
          >
            Relações, memórias e marcos
          </Link>
          {user?.is_admin && (
            <Link
              to="/settings/admin"
              className="tap rounded-full border border-line bg-paper px-4 py-2 text-sm font-medium text-ink transition hover:border-warn/40"
            >
              Painel da simulação
            </Link>
          )}
        </div>
      </section>

      <section className="mt-4 rounded-2xl border border-line bg-surface p-5">
        <h2 className="text-xs font-semibold uppercase tracking-wide text-ink-soft">Aplicativo</h2>
        <p className="mt-2 text-sm leading-relaxed text-ink-soft">
          O Viva funciona como PWA: no celular, use o menu do navegador e toque em
          <strong className="font-medium text-ink"> “Adicionar à tela inicial”</strong> para abrir como aplicativo.
        </p>
      </section>

      <button
        type="button"
        onClick={() => {
          logout()
          navigate('/login', { replace: true })
        }}
        className="tap mt-5 w-full rounded-full border border-line bg-surface text-sm font-medium text-accent-deep transition hover:border-accent/40"
      >
        Sair da conta
      </button>
    </div>
  )
}
