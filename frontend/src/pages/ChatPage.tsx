import { useEffect, useMemo, useState } from 'react'
import {
  ActionIcon,
  Badge,
  Box,
  Button,
  Card,
  Divider,
  Group,
  ScrollArea,
  Stack,
  Text,
  TextInput,
  Title,
} from '@mantine/core'
import { IconLogout, IconPlus, IconSend } from '@tabler/icons-react'
import { notifications } from '@mantine/notifications'
import { createConversation, listConversations, listMessages, sendMessage } from '../lib/chat'
import type { Conversation, Message } from '../lib/types'
import { logout } from '../lib/auth'
import { useNavigate } from 'react-router-dom'

export function ChatPage() {
  const nav = useNavigate()
  const [convs, setConvs] = useState<Conversation[]>([])
  const [activeId, setActiveId] = useState<string | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [draft, setDraft] = useState('')
  const [loadingConvs, setLoadingConvs] = useState(false)
  const [sending, setSending] = useState(false)

  const active = useMemo(() => convs.find((c) => c.id === activeId) ?? null, [convs, activeId])

  async function refreshConvs() {
    setLoadingConvs(true)
    try {
      const data = await listConversations({ archived: false })
      setConvs(data)
      if (!activeId && data[0]) setActiveId(data[0].id)
    } catch (e) {
      notifications.show({
        title: 'Failed to load conversations',
        message: e instanceof Error ? e.message : 'Unknown error',
        color: 'red',
      })
    } finally {
      setLoadingConvs(false)
    }
  }

  async function refreshMessages(conversationId: string) {
    try {
      const data = await listMessages(conversationId)
      setMessages(data)
    } catch (e) {
      notifications.show({
        title: 'Failed to load messages',
        message: e instanceof Error ? e.message : 'Unknown error',
        color: 'red',
      })
    }
  }

  useEffect(() => {
    refreshConvs()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (activeId) refreshMessages(activeId)
  }, [activeId])

  async function onNewConversation() {
    try {
      const c = await createConversation({ model_name: 'default', title: 'New conversation' })
      setConvs((prev) => [c, ...prev])
      setActiveId(c.id)
      setMessages([])
    } catch (e) {
      notifications.show({
        title: 'Failed to create conversation',
        message: e instanceof Error ? e.message : 'Unknown error',
        color: 'red',
      })
    }
  }

  async function onSend() {
    if (!activeId) return
    const content = draft.trim()
    if (!content) return
    setSending(true)
    setDraft('')
    try {
      const msg = await sendMessage(activeId, content)
      setMessages((prev) => [...prev, msg])
      // Placeholder: assistant streaming will be added once backend implements feature 11 fully.
      setMessages((prev) => [
        ...prev,
        {
          id: `local-${Date.now()}`,
          conversation_id: activeId,
          parent_message_id: msg.id,
          role: 'assistant',
          content: 'Assistant response streaming is not implemented yet. Next step: implement LLM streaming + citations on the backend.',
          created_at: new Date().toISOString(),
          model_name: null,
          token_count: null,
          generation_time: null,
          is_helpful: null,
          feedback_text: null,
        },
      ])
    } catch (e) {
      notifications.show({
        title: 'Failed to send message',
        message: e instanceof Error ? e.message : 'Unknown error',
        color: 'red',
      })
    } finally {
      setSending(false)
    }
  }

  async function onLogout() {
    await logout()
    nav('/auth')
  }

  return (
    <Box
      style={{
        height: '100vh',
        display: 'grid',
        gridTemplateColumns: '340px 1fr',
      }}
    >
      <Box
        style={{
          borderRight: '1px solid rgba(255,255,255,0.10)',
          padding: 16,
          background: 'rgba(255,255,255,0.03)',
        }}
      >
        <Group justify="space-between" align="center" mb="md">
          <Title order={3} c="white">
            Fieldforce
          </Title>
          <ActionIcon variant="subtle" color="gray" onClick={onLogout} title="Logout">
            <IconLogout size={18} />
          </ActionIcon>
        </Group>

        <Button
          leftSection={<IconPlus size={16} />}
          fullWidth
          onClick={onNewConversation}
          loading={loadingConvs}
          variant="light"
        >
          New conversation
        </Button>

        <Divider my="md" opacity={0.2} />

        <ScrollArea h="calc(100vh - 150px)" type="hover">
          <Stack gap="xs">
            {convs.map((c) => (
              <Card
                key={c.id}
                withBorder
                radius="md"
                p="sm"
                onClick={() => setActiveId(c.id)}
                style={{
                  cursor: 'pointer',
                  background: c.id === activeId ? 'rgba(36,99,235,0.18)' : 'rgba(255,255,255,0.04)',
                  borderColor: 'rgba(255,255,255,0.10)',
                }}
              >
                <Group justify="space-between" wrap="nowrap">
                  <Text c="white" fw={600} lineClamp={1}>
                    {c.title}
                  </Text>
                  <Badge variant="outline" color="gray">
                    {c.model_name}
                  </Badge>
                </Group>
                <Text size="xs" c="dimmed" mt={4} lineClamp={1}>
                  Updated {new Date(c.updated_at).toLocaleString()}
                </Text>
              </Card>
            ))}
          </Stack>
        </ScrollArea>
      </Box>

      <Box style={{ display: 'grid', gridTemplateRows: 'auto 1fr auto' }}>
        <Box
          style={{
            padding: '16px 18px',
            borderBottom: '1px solid rgba(255,255,255,0.10)',
            background: 'rgba(255,255,255,0.02)',
          }}
        >
          <Group justify="space-between">
            <Group gap="xs">
              <Text c="white" fw={700}>
                {active?.title ?? 'No conversation selected'}
              </Text>
              {active && (
                <Badge variant="light" color="blue">
                  /api/v1
                </Badge>
              )}
            </Group>
          </Group>
        </Box>

        <ScrollArea p="lg" type="hover">
          <Stack gap="sm">
            {messages.length === 0 ? (
              <Box>
                <Title order={2} c="white">
                  Ask anything.
                </Title>
                <Text c="gray.3" mt="sm">
                  Start by sending a message. Next we’ll add streaming, documents, and citations.
                </Text>
              </Box>
            ) : (
              messages.map((m) => (
                <Box
                  key={m.id}
                  style={{
                    display: 'flex',
                    justifyContent: m.role === 'user' ? 'flex-end' : 'flex-start',
                  }}
                >
                  <Card
                    radius="lg"
                    p="md"
                    style={{
                      maxWidth: 860,
                      background:
                        m.role === 'user'
                          ? 'rgba(36,99,235,0.22)'
                          : 'rgba(255,255,255,0.05)',
                      border: '1px solid rgba(255,255,255,0.10)',
                    }}
                  >
                    <Text c="white" style={{ whiteSpace: 'pre-wrap' }}>
                      {m.content}
                    </Text>
                    <Text size="xs" c="dimmed" mt={6}>
                      {m.role} · {new Date(m.created_at).toLocaleTimeString()}
                    </Text>
                  </Card>
                </Box>
              ))
            )}
          </Stack>
        </ScrollArea>

        <Box
          style={{
            padding: 16,
            borderTop: '1px solid rgba(255,255,255,0.10)',
            background: 'rgba(11,16,32,0.65)',
            backdropFilter: 'blur(10px)',
          }}
        >
          <Group align="flex-end" gap="sm">
            <TextInput
              value={draft}
              onChange={(e) => setDraft(e.currentTarget.value)}
              placeholder={activeId ? 'Message…' : 'Create a conversation first…'}
              disabled={!activeId || sending}
              styles={{
                input: {
                  background: 'rgba(255,255,255,0.05)',
                  borderColor: 'rgba(255,255,255,0.12)',
                  color: 'white',
                },
              }}
              style={{ flex: 1 }}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  onSend()
                }
              }}
            />
            <ActionIcon
              size="lg"
              variant="filled"
              color="blue"
              onClick={onSend}
              disabled={!activeId || sending || !draft.trim()}
              loading={sending}
              title="Send"
            >
              <IconSend size={18} />
            </ActionIcon>
          </Group>
        </Box>
      </Box>
    </Box>
  )
}

