import { useEffect, useMemo, useRef, useState } from 'react'
import {
  ActionIcon,
  Badge,
  Box,
  Button,
  Card,
  Divider,
  Group,
  Loader,
  ScrollArea,
  Stack,
  Text,
  Textarea,
  Title,
  Tooltip,
} from '@mantine/core'
import {
  IconDatabase,
  IconLogout,
  IconMessage,
  IconPlus,
  IconRefresh,
  IconSearch,
  IconSend,
  IconSparkles,
} from '@tabler/icons-react'
import { notifications } from '@mantine/notifications'
import { useNavigate } from 'react-router-dom'
import { createConversation, listConversations, listMessages, streamMessage } from '../lib/chat'
import type { Conversation, Message } from '../lib/types'
import { logout } from '../lib/auth'

type LocalMessage = Message & { pending?: boolean }

function formatRelative(value: string) {
  const date = new Date(value)
  const diff = Date.now() - date.getTime()
  const minutes = Math.max(1, Math.round(diff / 60_000))
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.round(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  return date.toLocaleDateString()
}

function makeLocalMessage(input: Pick<Message, 'conversation_id' | 'role' | 'content'> & Partial<Message>): LocalMessage {
  return {
    id: `local-${crypto.randomUUID()}`,
    parent_message_id: null,
    created_at: new Date().toISOString(),
    model_name: null,
    token_count: null,
    generation_time: null,
    is_helpful: null,
    feedback_text: null,
    pending: true,
    ...input,
  }
}

export function ChatPage() {
  const nav = useNavigate()
  const viewportRef = useRef<HTMLDivElement>(null)
  const [convs, setConvs] = useState<Conversation[]>([])
  const [activeId, setActiveId] = useState<string | null>(null)
  const [messages, setMessages] = useState<LocalMessage[]>([])
  const [draft, setDraft] = useState('')
  const [loadingConvs, setLoadingConvs] = useState(false)
  const [loadingMessages, setLoadingMessages] = useState(false)
  const [sending, setSending] = useState(false)

  const active = useMemo(() => convs.find((c) => c.id === activeId) ?? null, [convs, activeId])

  async function refreshConvs() {
    setLoadingConvs(true)
    try {
      const data = await listConversations({ archived: false })
      setConvs(data)
      setActiveId((current) => current ?? data[0]?.id ?? null)
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
    setLoadingMessages(true)
    try {
      const data = await listMessages(conversationId)
      setMessages(data)
    } catch (e) {
      notifications.show({
        title: 'Failed to load messages',
        message: e instanceof Error ? e.message : 'Unknown error',
        color: 'red',
      })
    } finally {
      setLoadingMessages(false)
    }
  }

  useEffect(() => {
    refreshConvs()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (activeId) refreshMessages(activeId)
  }, [activeId])

  useEffect(() => {
    viewportRef.current?.scrollTo({ top: viewportRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, sending])

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
    if (!activeId || sending) return
    const content = draft.trim()
    if (!content) return

    const userMessage = makeLocalMessage({ conversation_id: activeId, role: 'user', content })
    const assistantId = `local-assistant-${Date.now()}`
    const assistantMessage = makeLocalMessage({
      id: assistantId,
      conversation_id: activeId,
      role: 'assistant',
      content: '',
    })

    setDraft('')
    setSending(true)
    setMessages((prev) => [...prev, userMessage, assistantMessage])

    try {
      await streamMessage(activeId, content, {
        onToken: (token) => {
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantId ? { ...msg, content: `${msg.content}${token}` } : msg,
            ),
          )
        },
      })
      await refreshMessages(activeId)
      await refreshConvs()
    } catch (e) {
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantId
            ? {
                ...msg,
                pending: false,
                content:
                  e instanceof Error
                    ? `I could not generate a response: ${e.message}`
                    : 'I could not generate a response.',
              }
            : msg,
        ),
      )
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
    <Box className="chat-shell">
      <Box className="conversation-rail">
        <Group justify="space-between" align="center" mb="lg">
          <Group gap="sm">
            <Box className="brand-mark">
              <IconSparkles size={18} />
            </Box>
            <Box>
              <Title order={3} className="brand-title">
                Fieldforce
              </Title>
              <Text size="xs" c="dimmed">
                RAG workspace
              </Text>
            </Box>
          </Group>
          <Tooltip label="Logout">
            <ActionIcon variant="subtle" color="gray" onClick={onLogout} aria-label="Logout">
              <IconLogout size={18} />
            </ActionIcon>
          </Tooltip>
        </Group>

        <Button leftSection={<IconPlus size={16} />} fullWidth onClick={onNewConversation} loading={loadingConvs}>
          New conversation
        </Button>

        <Group justify="space-between" mt="lg" mb="xs">
          <Text size="xs" fw={700} tt="uppercase" c="dimmed">
            Conversations
          </Text>
          <Tooltip label="Refresh">
            <ActionIcon variant="subtle" color="gray" onClick={refreshConvs} loading={loadingConvs} aria-label="Refresh conversations">
              <IconRefresh size={16} />
            </ActionIcon>
          </Tooltip>
        </Group>

        <ScrollArea className="conversation-list" type="hover">
          <Stack gap="xs">
            {loadingConvs && convs.length === 0 ? (
              <Box className="quiet-state">
                <Loader size="sm" />
                <Text size="sm" c="dimmed">
                  Loading conversations
                </Text>
              </Box>
            ) : convs.length === 0 ? (
              <Box className="quiet-state">
                <IconMessage size={22} />
                <Text size="sm" c="dimmed">
                  No conversations yet
                </Text>
              </Box>
            ) : (
              convs.map((c) => (
                <Card
                  key={c.id}
                  withBorder
                  className={c.id === activeId ? 'conversation-card active' : 'conversation-card'}
                  onClick={() => setActiveId(c.id)}
                >
                  <Group justify="space-between" wrap="nowrap" align="flex-start">
                    <Text fw={700} lineClamp={1}>
                      {c.title}
                    </Text>
                    <Badge variant="light" color="gray" size="xs">
                      {c.model_name}
                    </Badge>
                  </Group>
                  <Text size="xs" c="dimmed" mt={6} lineClamp={1}>
                    Updated {formatRelative(c.updated_at)}
                  </Text>
                </Card>
              ))
            )}
          </Stack>
        </ScrollArea>

        <Divider my="md" />
        <Group gap="xs" className="db-chip">
          <IconDatabase size={15} />
          <Text size="xs">Rag-LLM connected</Text>
        </Group>
      </Box>

      <Box className="chat-main">
        <Box className="chat-header">
          <Group justify="space-between" align="center">
            <Box>
              <Group gap="xs">
                <Title order={3}>{active?.title ?? 'Select or create a conversation'}</Title>
                {active && (
                  <Badge variant="light" color="teal">
                    Live
                  </Badge>
                )}
              </Group>
              <Text c="dimmed" size="sm">
                {active ? 'Messages are saved to PostgreSQL and streamed back from the API.' : 'Create a conversation to begin.'}
              </Text>
            </Box>
            <Badge leftSection={<IconSearch size={13} />} variant="outline" color="gray">
              /api/v1
            </Badge>
          </Group>
        </Box>

        <ScrollArea className="message-area" viewportRef={viewportRef} type="hover">
          <Stack gap="md">
            {loadingMessages ? (
              <Box className="empty-chat">
                <Loader />
                <Text c="dimmed">Loading messages</Text>
              </Box>
            ) : messages.length === 0 ? (
              <Box className="empty-chat">
                <IconSparkles size={36} />
                <Title order={2}>Start with a question.</Title>
                <Text c="dimmed" maw={560} ta="center">
                  Ask about a document workflow, test the chat memory, or create a quick prompt to verify the backend stream.
                </Text>
                <Group gap="xs" justify="center">
                  {['Summarize the system design', 'What can this RAG app do?', 'How should we test citations?'].map((prompt) => (
                    <Button key={prompt} variant="light" size="xs" onClick={() => setDraft(prompt)} disabled={!activeId}>
                      {prompt}
                    </Button>
                  ))}
                </Group>
              </Box>
            ) : (
              messages.map((m) => (
                <Box key={m.id} className={m.role === 'user' ? 'message-row user' : 'message-row assistant'}>
                  <Box className="message-bubble">
                    <Group justify="space-between" mb={6}>
                      <Text size="xs" fw={800} tt="uppercase" c={m.role === 'user' ? 'blue.1' : 'teal.2'}>
                        {m.role === 'user' ? 'You' : 'Assistant'}
                      </Text>
                      <Text size="xs" c="dimmed">
                        {new Date(m.created_at).toLocaleTimeString()}
                      </Text>
                    </Group>
                    <Text className="message-text">{m.content || (m.pending ? 'Thinking...' : '')}</Text>
                  </Box>
                </Box>
              ))
            )}
          </Stack>
        </ScrollArea>

        <Box className="composer">
          <Group align="flex-end" gap="sm" wrap="nowrap">
            <Textarea
              value={draft}
              onChange={(e) => setDraft(e.currentTarget.value)}
              placeholder={activeId ? 'Message Fieldforce...' : 'Create a conversation first...'}
              disabled={!activeId || sending}
              autosize
              minRows={1}
              maxRows={5}
              className="composer-input"
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  onSend()
                }
              }}
            />
            <Tooltip label="Send">
              <ActionIcon
                size={44}
                variant="filled"
                color="blue"
                onClick={onSend}
                disabled={!activeId || sending || !draft.trim()}
                loading={sending}
                aria-label="Send message"
              >
                <IconSend size={19} />
              </ActionIcon>
            </Tooltip>
          </Group>
        </Box>
      </Box>
    </Box>
  )
}
