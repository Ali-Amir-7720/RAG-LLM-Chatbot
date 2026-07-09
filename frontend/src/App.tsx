import { Navigate, Route, Routes } from 'react-router-dom'
import { AppShell } from '@mantine/core'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthPage } from './pages/AuthPage'
import { ChatPage } from './pages/ChatPage'

const qc = new QueryClient()

function App() {
  const authed = Boolean(localStorage.getItem('access_token'))

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
          <Route path="/auth" element={<AuthPage />} />
          <Route path="/" element={authed ? <ChatPage /> : <Navigate to="/auth" replace />} />
          <Route path="*" element={<Navigate to={authed ? '/' : '/auth'} replace />} />
        </Routes>
      </AppShell>
    </QueryClientProvider>
  )
}

export default App
