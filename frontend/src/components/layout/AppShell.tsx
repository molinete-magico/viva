import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import { Avatar } from '../ui'
import { useFetch } from '../ui'
import type { Listing, NotificationItem, World } from '../../types/api'

const navItems = [
  { to: '/feed', label: 'Feed', icon: HomeIcon },
  { to: '/explore', label: 'Explorar', icon: CompassIcon },
  { to: '/messages', label: 'Mensagens', icon: ChatIcon },
  { to: '/events', label: 'Eventos', icon: CalendarIcon },
  { to: '/profile', label: 'Perfil', icon: UserIcon },
]

export function AppShell() {
  const { user, character, logout } = useAuth()
  const navigate = useNavigate()
  const world = useFetch<World>('/world')
  const notifications = useFetch<Listing<NotificationItem>>('/notifications')
  const unread = (notifications.data?.items ?? []).filter((n) => !n.read_at).length

  return (
    <div className="min-h-dvh lg:flex">
      <header className="safe-top sticky top-0 z-30 border-b border-line bg-paper/95 backdrop-blur-sm">
        <div className="mx-auto flex h-14 max-w-3xl items-center justify-between gap-3 px-4 lg:max-w-5xl">
          <div className="flex items-baseline gap-3">
            <span className="font-display text-xl font-semibold tracking-tight text-ink">Viva</span>
            {world.data && (
              <span className="hidden text-xs text-ink-soft sm:inline">
                {world.data.city_name} · {world.data.day_name}, {world.data.time}
              </span>
            )}
          </div>
          <div className="flex items-center gap-1">
            <button
              type="button"
              onClick={() => navigate('/notifications')}
              aria-label={`Notificações${unread ? `, ${unread} novas` : ''}`}
              className="tap relative flex items-center justify-center rounded-full px-3 text-ink-soft transition hover:bg-line/60"
            >
              <BellIcon />
              {unread > 0 && (
                <span className="absolute right-1.5 top-1.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-accent px-1 text-[10px] font-bold text-white">
                  {unread > 9 ? '9+' : unread}
                </span>
              )}
            </button>
            <button
              type="button"
              onClick={() => navigate(character ? `/profile/${character.id}` : '/onboarding')}
              aria-label="Seu perfil"
              className="tap flex items-center rounded-full p-1.5 transition hover:bg-line/60"
            >
              <Avatar name={character?.name ?? user?.email ?? '?'} size="sm" photoUrl={character?.photo_url} />
            </button>
          </div>
        </div>
      </header>

      <div className="flex w-full">
        <nav aria-label="Navegação principal" className="hidden w-52 shrink-0 py-8 pl-6 lg:block">
          <ul className="space-y-1">
            {navItems.map((item) => (
              <li key={item.to}>
                <DesktopLink to={item.to} label={item.label} icon={item.icon} />
              </li>
            ))}
            <li className="pt-6">
              <DesktopLink to="/settings" label="Configurações" icon={SettingsIcon} />
            </li>
          </ul>
          <button
            type="button"
            onClick={() => {
              logout()
              navigate('/login')
            }}
            className="tap mt-6 rounded-full px-4 text-sm text-ink-soft transition hover:bg-line/60"
          >
            Sair da conta
          </button>
        </nav>

        <main className="min-w-0 flex-1 pb-24 lg:pb-10">
          <Outlet />
        </main>
      </div>

      <nav
        aria-label="Navegação principal"
        className="safe-bottom fixed inset-x-0 bottom-0 z-30 border-t border-line bg-paper/95 backdrop-blur-sm lg:hidden"
      >
        <ul className="mx-auto flex max-w-lg">
          {navItems.map((item) => (
            <li key={item.to} className="flex-1">
              <MobileLink to={item.to} label={item.label} icon={item.icon} />
            </li>
          ))}
        </ul>
      </nav>
    </div>
  )
}

function MobileLink({ to, label, icon: Icon }: { to: string; label: string; icon: typeof HomeIcon }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        `flex min-h-14 flex-col items-center justify-center gap-0.5 text-[11px] transition ${
          isActive ? 'text-accent' : 'text-ink-soft'
        }`
      }
    >
      <Icon />
      <span>{label}</span>
    </NavLink>
  )
}

function DesktopLink({ to, label, icon: Icon }: { to: string; label: string; icon: typeof HomeIcon }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        `flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition ${
          isActive ? 'bg-accent-soft text-accent-deep' : 'text-ink-soft hover:bg-line/60'
        }`
      }
    >
      <Icon />
      {label}
    </NavLink>
  )
}

const iconProps = {
  width: 22,
  height: 22,
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.8,
  strokeLinecap: 'round' as const,
  strokeLinejoin: 'round' as const,
  'aria-hidden': true,
}

function HomeIcon() {
  return (
    <svg {...iconProps}>
      <path d="M3 10.5 12 3l9 7.5" />
      <path d="M5.5 9.5V20a1 1 0 0 0 1 1H10v-5.5h4V21h3.5a1 1 0 0 0 1-1V9.5" />
    </svg>
  )
}

function CompassIcon() {
  return (
    <svg {...iconProps}>
      <circle cx="12" cy="12" r="9" />
      <path d="m15.5 8.5-2 5-5 2 2-5 5-2Z" />
    </svg>
  )
}

function ChatIcon() {
  return (
    <svg {...iconProps}>
      <path d="M21 11.5a8.38 8.38 0 0 1-9 8.4 8.5 8.5 0 0 1-3.8-.9L3 20.5l1.6-4.7A8.38 8.38 0 0 1 3.6 11 8.5 8.5 0 0 1 12 3a8.38 8.38 0 0 1 9 8.5Z" />
    </svg>
  )
}

function CalendarIcon() {
  return (
    <svg {...iconProps}>
      <rect x="3" y="5" width="18" height="16" rx="2" />
      <path d="M8 3v4M16 3v4M3 10h18" />
    </svg>
  )
}

function UserIcon() {
  return (
    <svg {...iconProps}>
      <circle cx="12" cy="8" r="4" />
      <path d="M4 21c0-4 3.6-6.5 8-6.5s8 2.5 8 6.5" />
    </svg>
  )
}

function BellIcon() {
  return (
    <svg {...iconProps}>
      <path d="M18 9a6 6 0 1 0-12 0c0 6-2.5 7-2.5 7h17S18 15 18 9Z" />
      <path d="M10.3 20a2 2 0 0 0 3.4 0" />
    </svg>
  )
}

function SettingsIcon() {
  return (
    <svg {...iconProps}>
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1Z" />
    </svg>
  )
}
