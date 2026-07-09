import { useState } from 'react'
import {
  Anchor,
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
import { login, signup } from '../lib/auth'
import { useNavigate } from 'react-router-dom'

export function AuthPage() {
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
    <Box
      style={{
        minHeight: '100vh',
        display: 'grid',
        placeItems: 'center',
        padding: 24,
      }}
    >
      <Container size={420} w="100%">
        <Card
          radius="lg"
          p="xl"
          withBorder
          style={{
            backdropFilter: 'blur(10px)',
            background: 'rgba(255,255,255,0.06)',
            borderColor: 'rgba(255,255,255,0.14)',
          }}
        >
          <Stack gap="md">
            <Title order={2} c="white">
              Fieldforce RAG Chat
            </Title>
            <Text c="gray.3" size="sm">
              Sign in to start conversations, upload documents, and chat with grounded answers.
            </Text>

            {mode === 'signup' && (
              <TextInput
                label="Username"
                value={username}
                onChange={(e) => setUsername(e.currentTarget.value)}
                placeholder="yourname"
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
              placeholder="••••••••"
              required
            />

            <Button loading={loading} onClick={onSubmit} fullWidth>
              {mode === 'login' ? 'Login' : 'Create account'}
            </Button>

            <Group justify="space-between">
              <Anchor
                component="button"
                type="button"
                onClick={() => setMode((m) => (m === 'login' ? 'signup' : 'login'))}
                size="sm"
              >
                {mode === 'login' ? 'Need an account? Sign up' : 'Already have an account? Login'}
              </Anchor>
              <Text c="dimmed" size="xs">
                API: <code style={{ color: 'white' }}>/api/v1</code>
              </Text>
            </Group>
          </Stack>
        </Card>
      </Container>
    </Box>
  )
}

