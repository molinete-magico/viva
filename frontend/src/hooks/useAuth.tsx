import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { api, clearToken, getToken, setToken } from '../services/api'
import type { AuthResponse, Character, MeResponse, User } from '../types/api'

interface AuthContextValue {
  user: User | null
  character: Character | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string) => Promise<void>
  logout: () => void
  refresh: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [character, setCharacter] = useState<Character | null>(null)
  const [loading, setLoading] = useState(true)

  const refresh = useCallback(async () => {
    if (!getToken()) {
      setUser(null)
      setCharacter(null)
      setLoading(false)
      return
    }
    try {
      const me = await api<MeResponse>('/auth/me')
      setUser(me.user)
      setCharacter(me.active_character)
    } catch {
      clearToken()
      setUser(null)
      setCharacter(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void refresh()
  }, [refresh])

  const login = useCallback(async (email: string, password: string) => {
    const data = await api<AuthResponse>('/auth/login', {
      method: 'POST',
      body: { email, password },
    })
    setToken(data.token)
    setUser(data.user)
    await refresh()
  }, [refresh])

  const register = useCallback(async (email: string, password: string) => {
    const data = await api<AuthResponse>('/auth/register', {
      method: 'POST',
      body: { email, password },
    })
    setToken(data.token)
    setUser(data.user)
    await refresh()
  }, [refresh])

  const logout = useCallback(() => {
    clearToken()
    setUser(null)
    setCharacter(null)
  }, [])

  const value = useMemo(
    () => ({ user, character, loading, login, register, logout, refresh }),
    [user, character, loading, login, register, logout, refresh],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth precisa estar dentro de AuthProvider')
  return ctx
}
