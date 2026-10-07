import { Navigate } from 'react-router-dom'

export function NavigateToFeed() {
  return <Navigate to="/feed" replace />
}
