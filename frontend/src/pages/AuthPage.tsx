import { useState } from 'react'
import {
  Anchor,
  Badge,
  Box,
  Button,
  Card,
  Container,
  Group,
  PasswordInput,
  Stack,
  Text,
  TextInput,
  Title,
} from '@mantine/core'
import { notifications } from '@mantine/notifications'
import { IconArrowRight, IconDatabase, IconLock, IconMessageCircle, IconSparkles } from '@tabler/icons-react'
import { useNavigate } from 'react-router-dom'
import { login, signup } from '../lib/auth'

type AuthPageProps = {
  onAuthSuccess: () => void
}

export function AuthPage({ onAuthSuccess }: AuthPageProps) {
  const [mode, setMode] = useState<'login' | 'signup'>('login')
  const [email, setEmail] = useState('')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const nav = useNavigate()

  async function onSubmit() {
    setLoading(true)
    try {
      if (mode === 'login') {
        await login({ email, password, device: 'web' })
        notifications.show({ title: 'Welcome back', message: 'Logged in successfully.' })
      } else {
        await signup({ username, email, password })
        notifications.show({ title: 'Account created', message: 'You are now signed in.' })
      }
      onAuthSuccess()
      nav('/')
    } catch (e) {
      notifications.show({
        title: 'Authentication failed',
        message: e instanceof Error ? e.message : 'Unknown error',
        color: 'red',
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <Box className="auth-shell">
      <Container size="lg" w="100%">
        <Box className="auth-grid">
          <Stack className="auth-copy" gap="xl">
            <Badge className="status-badge" leftSection={<IconDatabase size={14} />}>
              PostgreSQL + pgvector connected
            </Badge>

            <Stack gap="md">
              <Title className="auth-title">Fieldforce RAG Chat</Title>
              <Text className="auth-subtitle">
                A focused workspace for asking questions, keeping conversation context, and grounding answers in your own documents.
              </Text>
            </Stack>

            <Group gap="sm" className="feature-row">
              <Box className="feature-pill">
                <IconMessageCircle size={18} />
                <span>Threaded chat</span>
              </Box>
              <Box className="feature-pill">
                <IconSparkles size={18} />
                <span>Streaming answers</span>
              </Box>
              <Box className="feature-pill">
                <IconLock size={18} />
                <span>Private sessions</span>
              </Box>
            </Group>
          </Stack>

          <Card className="auth-panel" withBorder>
            <Stack gap="lg">
              <Stack gap={4}>
                <Title order={2}>{mode === 'login' ? 'Sign in' : 'Create account'}</Title>
                <Text c="dimmed" size="sm">
                  {mode === 'login'
                    ? 'Continue to your conversations and document workspace.'
                    : 'Create a workspace account to start testing the RAG flow.'}
                </Text>
              </Stack>

              {mode === 'signup' && (
                <TextInput
                  label="Username"
                  value={username}
                  onChange={(e) => setUsername(e.currentTarget.value)}
                  placeholder="ali"
                  required
                />
              )}

              <TextInput
                label="Email"
                value={email}
                onChange={(e) => setEmail(e.currentTarget.value)}
                placeholder="you@example.com"
                required
              />

              <PasswordInput
                label="Password"
                value={password}
                onChange={(e) => setPassword(e.currentTarget.value)}
                placeholder="Enter your password"
                required
              />

              <Button
                loading={loading}
                onClick={onSubmit}
                fullWidth
                rightSection={<IconArrowRight size={17} />}
                disabled={!email.trim() || !password.trim() || (mode === 'signup' && !username.trim())}
              >
                {mode === 'login' ? 'Login' : 'Create account'}
              </Button>

              <Group justify="space-between" gap="sm">
                <Anchor
                  component="button"
                  type="button"
                  onClick={() => setMode((m) => (m === 'login' ? 'signup' : 'login'))}
                  size="sm"
                >
                  {mode === 'login' ? 'Need an account?' : 'Already have an account?'}
                </Anchor>
                <Text c="dimmed" size="xs">
                  API /api/v1
                </Text>
              </Group>
            </Stack>
          </Card>
        </Box>
      </Container>
    </Box>
  )
}
