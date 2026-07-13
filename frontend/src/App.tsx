import { useState } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { AppShell } from '@mantine/core'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthPage } from './pages/AuthPage'
import { ChatPage } from './pages/ChatPage'
import { getAccessToken } from './lib/api'

const qc = new QueryClient()

function App() {
  const [authed, setAuthed] = useState(() => Boolean(getAccessToken()))

  return (
    <QueryClientProvider client={qc}>
      <AppShell
        padding={0}
        styles={{
          main: {
            minHeight: '100vh',
          },
        }}
      >
        <Routes>
          <Route
            path="/auth"
            element={
              authed ? (
                <Navigate to="/" replace />
              ) : (
                <AuthPage onAuthSuccess={() => setAuthed(true)} />
              )
            }
          />
          <Route
            path="/"
            element={
              authed ? (
                <ChatPage onLogoutSuccess={() => setAuthed(false)} />
              ) : (
                <Navigate to="/auth" replace />
              )
            }
          />
          <Route path="*" element={<Navigate to={authed ? '/' : '/auth'} replace />} />
        </Routes>
      </AppShell>
    </QueryClientProvider>
  )
}

export default App
