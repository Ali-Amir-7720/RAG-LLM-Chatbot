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
  Menu,
  ScrollArea,
  Stack,
  Text,
  TextInput,
  Textarea,
  Title,
  Tooltip,
} from '@mantine/core'
import {
  IconChevronLeft,
  IconChevronRight,
  IconDatabase,
  IconDotsVertical,
  IconLogout,
  IconMessage,
  IconPinned,
  IconPinnedOff,
  IconPlus,
  IconRefresh,
  IconSearch,
  IconSend,
  IconShare3,
  IconSparkles,
  IconTrash,
  IconEdit,
} from '@tabler/icons-react'
import { notifications } from '@mantine/notifications'
import { useNavigate } from 'react-router-dom'
import {
  createConversation,
  deleteConversation,
  listConversations,
  listMessages,
  renameConversation,
  streamMessage,
} from '../lib/chat'
import type { Conversation, Message } from '../lib/types'
import { logout } from '../lib/auth'

type LocalMessage = Message & { pending?: boolean }
const CONVERSATION_PAGE_SIZE = 10
const PINNED_STORAGE_KEY = 'pinned_conversation_ids'

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

type ChatPageProps = {
  onLogoutSuccess: () => void
}

export function ChatPage({ onLogoutSuccess }: ChatPageProps) {
  const nav = useNavigate()
  const viewportRef = useRef<HTMLDivElement>(null)
  const [convs, setConvs] = useState<Conversation[]>([])
  const [activeId, setActiveId] = useState<string | null>(null)
  const [messages, setMessages] = useState<LocalMessage[]>([])
  const [draft, setDraft] = useState('')
  const [loadingConvs, setLoadingConvs] = useState(false)
  const [loadingMessages, setLoadingMessages] = useState(false)
  const [sending, setSending] = useState(false)
  const [railCollapsed, setRailCollapsed] = useState(false)
  const [conversationOffset, setConversationOffset] = useState(0)
  const [hasMoreConvs, setHasMoreConvs] = useState(true)
  const [conversationSearch, setConversationSearch] = useState('')
  const [pinnedIds, setPinnedIds] = useState<string[]>(() => {
    try {
      return JSON.parse(localStorage.getItem(PINNED_STORAGE_KEY) ?? '[]')
    } catch {
      return []
    }
  })

  const active = useMemo(() => convs.find((c) => c.id === activeId) ?? null, [convs, activeId])
  const orderedConvs = useMemo(() => {
    const search = conversationSearch.trim().toLowerCase()
    return convs
      .filter((c) => !search || c.title.toLowerCase().includes(search) || c.model_name.toLowerCase().includes(search))
      .sort((a, b) => {
        const aPinned = pinnedIds.includes(a.id)
        const bPinned = pinnedIds.includes(b.id)
        if (aPinned !== bPinned) return aPinned ? -1 : 1
        return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
      })
  }, [convs, conversationSearch, pinnedIds])

  function savePinnedIds(next: string[]) {
    setPinnedIds(next)
    localStorage.setItem(PINNED_STORAGE_KEY, JSON.stringify(next))
  }

  async function refreshConvs() {
    setLoadingConvs(true)
    try {
      const data = await listConversations({ archived: false, limit: CONVERSATION_PAGE_SIZE, offset: 0 })

      if (data.length === 0) {
        // Brand-new user: nothing to select, so create their first conversation
        // instead of leaving the composer stuck on "Create a conversation first...".
        await onNewConversation()
        setConversationOffset(0)
        setHasMoreConvs(false)
        return
      }

      setConvs(data)
      setConversationOffset(data.length)
      setHasMoreConvs(data.length === CONVERSATION_PAGE_SIZE)
      setActiveId((current) => {
        const fromUrl = new URLSearchParams(window.location.search).get('conversation')
        if (current && data.some((c) => c.id === current)) return current
        if (fromUrl && data.some((c) => c.id === fromUrl)) return fromUrl
        return data[0]?.id ?? null
      })
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

  async function loadAllConversations() {
    setLoadingConvs(true)
    try {
      const loaded: Conversation[] = []
      let nextOffset = conversationOffset
      let keepLoading = true

      while (keepLoading) {
        const page = await listConversations({
          archived: false,
          limit: CONVERSATION_PAGE_SIZE,
          offset: nextOffset,
        })
        loaded.push(...page)
        nextOffset += page.length
        keepLoading = page.length === CONVERSATION_PAGE_SIZE
      }

      setConvs((prev) => {
        const seen = new Set(prev.map((c) => c.id))
        return [...prev, ...loaded.filter((c) => !seen.has(c.id))]
      })
      setConversationOffset(nextOffset)
      setHasMoreConvs(false)
    } catch (e) {
      notifications.show({
        title: 'Failed to load all conversations',
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

  async function onRenameConversation(conversation: Conversation) {
    const title = window.prompt('Rename conversation', conversation.title)?.trim()
    if (!title || title === conversation.title) return

    try {
      const updated = await renameConversation(conversation.id, title)
      setConvs((prev) => prev.map((c) => (c.id === conversation.id ? updated : c)))
      notifications.show({ title: 'Conversation renamed', message: updated.title })
    } catch (e) {
      notifications.show({
        title: 'Failed to rename conversation',
        message: e instanceof Error ? e.message : 'Unknown error',
        color: 'red',
      })
    }
  }

  async function onDeleteConversation(conversation: Conversation) {
    if (!window.confirm(`Delete "${conversation.title}"? This cannot be undone.`)) return

    try {
      await deleteConversation(conversation.id)
      const remaining = convs.filter((c) => c.id !== conversation.id)
      setConvs(remaining)
      savePinnedIds(pinnedIds.filter((id) => id !== conversation.id))
      if (activeId === conversation.id) {
        setActiveId(remaining[0]?.id ?? null)
        setMessages([])
      }
      notifications.show({ title: 'Conversation deleted', message: conversation.title })
    } catch (e) {
      notifications.show({
        title: 'Failed to delete conversation',
        message: e instanceof Error ? e.message : 'Unknown error',
        color: 'red',
      })
    }
  }

  async function onShareConversation(conversation: Conversation) {
    const url = `${window.location.origin}/?conversation=${conversation.id}`
    try {
      await navigator.clipboard.writeText(url)
      notifications.show({ title: 'Share link copied', message: conversation.title })
    } catch {
      notifications.show({ title: 'Share link', message: url })
    }
  }

  function onTogglePin(conversation: Conversation) {
    const next = pinnedIds.includes(conversation.id)
      ? pinnedIds.filter((id) => id !== conversation.id)
      : [conversation.id, ...pinnedIds]
    savePinnedIds(next)
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
    onLogoutSuccess()
    nav('/auth')
  }

  return (
    <Box className={railCollapsed ? 'chat-shell rail-collapsed' : 'chat-shell'}>
      <Box className={railCollapsed ? 'conversation-rail collapsed' : 'conversation-rail'}>
        <Group justify="space-between" align="center" mb="lg">
          <Group gap="sm">
            <Tooltip label={railCollapsed ? 'Show toolbar' : 'Hide toolbar'}>
            <ActionIcon
              className="brand-mark"
              variant="filled"
              onClick={() => setRailCollapsed((value) => !value)}
              aria-label={railCollapsed ? 'Show toolbar' : 'Hide toolbar'}
            >
              <IconSparkles size={18} />
            </ActionIcon>
            </Tooltip>
            {!railCollapsed && <Box>
              <Title order={3} className="brand-title">
                Fieldforce
              </Title>
              <Text size="xs" c="dimmed">
                RAG workspace
              </Text>
            </Box>}
          </Group>
          {!railCollapsed && (
          <Group gap={4}>
          <Tooltip label="Hide toolbar">
            <ActionIcon variant="subtle" color="gray" onClick={() => setRailCollapsed(true)} aria-label="Hide toolbar">
              <IconChevronLeft size={18} />
            </ActionIcon>
          </Tooltip>
          <Tooltip label="Logout">
            <ActionIcon variant="subtle" color="gray" onClick={onLogout} aria-label="Logout">
              <IconLogout size={18} />
            </ActionIcon>
          </Tooltip>
          </Group>
          )}
        </Group>

        {railCollapsed ? (
          <Stack gap="sm" align="center">
            <Tooltip label="Show toolbar" position="right">
              <ActionIcon variant="light" color="blue" onClick={() => setRailCollapsed(false)} aria-label="Show toolbar">
                <IconChevronRight size={18} />
              </ActionIcon>
            </Tooltip>
            <Tooltip label="New conversation" position="right">
              <ActionIcon variant="light" color="blue" onClick={onNewConversation} loading={loadingConvs} aria-label="New conversation">
                <IconPlus size={18} />
              </ActionIcon>
            </Tooltip>
            <Tooltip label="Refresh" position="right">
              <ActionIcon variant="subtle" color="gray" onClick={refreshConvs} loading={loadingConvs} aria-label="Refresh conversations">
                <IconRefresh size={18} />
              </ActionIcon>
            </Tooltip>
          </Stack>
        ) : (
          <>
        <Button leftSection={<IconPlus size={16} />} fullWidth onClick={onNewConversation} loading={loadingConvs}>
          New conversation
        </Button>

        <TextInput
          mt="md"
          value={conversationSearch}
          onChange={(event) => setConversationSearch(event.currentTarget.value)}
          placeholder="Search conversations"
          leftSection={<IconSearch size={16} />}
          className="conversation-search"
        />

        <Group justify="space-between" mt="lg" mb="xs">
          <Text size="xs" fw={700} tt="uppercase" c="dimmed">
            Last {Math.min(convs.length, CONVERSATION_PAGE_SIZE)} conversations
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
            ) : orderedConvs.length === 0 ? (
              <Box className="quiet-state">
                <IconMessage size={22} />
                <Text size="sm" c="dimmed">
                  {conversationSearch ? 'No matching conversations' : 'No conversations yet'}
                </Text>
              </Box>
            ) : (
              orderedConvs.map((c) => (
                <Card
                  key={c.id}
                  withBorder
                  className={c.id === activeId ? 'conversation-card active' : 'conversation-card'}
                  onClick={() => setActiveId(c.id)}
                >
                  <Group justify="space-between" wrap="nowrap" align="flex-start">
                    <Group gap={6} wrap="nowrap" miw={0}>
                      {pinnedIds.includes(c.id) && <IconPinned size={14} className="pin-indicator" />}
                      <Text fw={700} lineClamp={1}>
                        {c.title}
                      </Text>
                    </Group>
                    <Menu shadow="md" width={190} position="bottom-end">
                      <Menu.Target>
                        <ActionIcon
                          variant="subtle"
                          color="gray"
                          size="sm"
                          aria-label="Conversation actions"
                          onClick={(event) => event.stopPropagation()}
                        >
                          <IconDotsVertical size={16} />
                        </ActionIcon>
                      </Menu.Target>
                      <Menu.Dropdown onClick={(event) => event.stopPropagation()}>
                        <Menu.Item
                          leftSection={pinnedIds.includes(c.id) ? <IconPinnedOff size={16} /> : <IconPinned size={16} />}
                          onClick={() => onTogglePin(c)}
                        >
                          {pinnedIds.includes(c.id) ? 'Unpin' : 'Pin'}
                        </Menu.Item>
                        <Menu.Item leftSection={<IconEdit size={16} />} onClick={() => onRenameConversation(c)}>
                          Rename
                        </Menu.Item>
                        <Menu.Item leftSection={<IconShare3 size={16} />} onClick={() => onShareConversation(c)}>
                          Share
                        </Menu.Item>
                        <Menu.Divider />
                        <Menu.Item color="red" leftSection={<IconTrash size={16} />} onClick={() => onDeleteConversation(c)}>
                          Delete
                        </Menu.Item>
                      </Menu.Dropdown>
                    </Menu>
                  </Group>
                  <Group justify="space-between" mt={6} wrap="nowrap">
                    <Text size="xs" c="dimmed" lineClamp={1}>
                      Updated {formatRelative(c.updated_at)}
                    </Text>
                    <Badge variant="light" color="gray" size="xs">
                      {c.model_name}
                    </Badge>
                  </Group>
                </Card>
              ))
            )}
          </Stack>
        </ScrollArea>

        <Button
          mt="sm"
          variant="subtle"
          fullWidth
          onClick={loadAllConversations}
          loading={loadingConvs}
          disabled={!hasMoreConvs || Boolean(conversationSearch)}
        >
          {hasMoreConvs ? 'Load all conversations' : 'All conversations loaded'}
        </Button>

        <Divider my="md" />
        <Group gap="xs" className="db-chip">
          <IconDatabase size={15} />
          <Text size="xs">Rag-LLM connected</Text>
        </Group>
        </>
        )}
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