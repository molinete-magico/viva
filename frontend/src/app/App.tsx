import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider, useAuth } from '../hooks/useAuth'
import { AppShell } from '../components/layout/AppShell'
import { Spinner } from '../components/ui'
import { LoginPage, RegisterPage } from '../features/auth/AuthPages'
import { OnboardingPage } from '../features/onboarding/OnboardingPage'
import { FeedPage } from '../features/feed/FeedPage'
import { ExplorePage } from '../features/explore/ExplorePage'
import { MessagesPage } from '../features/messages/MessagesPage'
import { ChatPage } from '../features/messages/ChatPage'
import { EventsPage } from '../features/events/EventsPage'
import { EventPage } from '../features/events/EventPage'
import { SessionPage } from '../features/events/SessionPage'
import { NotificationsPage } from '../features/notifications/NotificationsPage'
import { WorldPage } from '../features/world/WorldPage'
import { SettingsPage } from '../features/settings/SettingsPage'
import { RelationshipsPage } from '../features/settings/RelationshipsPage'
import { AdminPage } from '../features/settings/AdminPage'
import { OwnProfileRedirect, ProfilePage } from '../features/profile/ProfilePage'
import { NavigateToFeed } from './NavigateToFeed'

function Protected() {
  const { user, loading } = useAuth()
  if (loading) return <Spinner label="Abrindo a cidade" />
  if (!user) return <Navigate to="/login" replace />
  return <AppShell />
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route element={<Protected />}>
            <Route index element={<NavigateToFeed />} />
            <Route path="/feed" element={<FeedPage />} />
            <Route path="/explore" element={<ExplorePage />} />
            <Route path="/messages" element={<MessagesPage />} />
            <Route path="/messages/:conversationId" element={<ChatPage />} />
            <Route path="/events" element={<EventsPage />} />
            <Route path="/events/:eventId" element={<EventPage />} />
            <Route path="/events/session/:sessionId" element={<SessionPage />} />
            <Route path="/notifications" element={<NotificationsPage />} />
            <Route path="/world" element={<WorldPage />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="/settings/world/relationships" element={<RelationshipsPage />} />
            <Route path="/settings/admin" element={<AdminPage />} />
            <Route path="/onboarding" element={<OnboardingPage />} />
            <Route path="/profile" element={<OwnProfileRedirect />} />
            <Route path="/profile/:characterId" element={<ProfilePage />} />
            <Route path="*" element={<NavigateToFeed />} />
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}
