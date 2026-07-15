import { useEffect, useMemo, useRef, useState } from 'react'
import { notifications } from '@mantine/notifications'
import { useNavigate } from 'react-router-dom'
import {
  IconPlus,
  IconSearch,
  IconPaperclip,
  IconArrowUp,
  IconFileText,
  IconMenu2,
  IconEdit,
  IconTrash,
  IconLogout
} from '@tabler/icons-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import {
  createConversation,
  listConversations,
  listMessages,
  streamMessage,
  deleteConversation,
  renameConversation
} from '../lib/chat'
import type { Conversation, Message } from '../lib/types'
import { logout, fetchMe } from '../lib/auth'

type LocalMessage = Message & { pending?: boolean }
const CONVERSATION_PAGE_SIZE = 50

function makeLocalMessage(input: Pick<Message, 'conversation_id' | 'role' | 'content'> & Partial<Message>): LocalMessage {
  return {
    id: `local-${crypto.randomUUID()}`,
    created_at: new Date().toISOString(),
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
  
  const [user, setUser] = useState<{ username: string } | null>(null)
  const [convs, setConvs] = useState<Conversation[]>([])
  const [activeId, setActiveId] = useState<string | null>(null)
  const [messages, setMessages] = useState<LocalMessage[]>([])
  const [draft, setDraft] = useState('')
  const [sending, setSending] = useState(false)
  const [conversationSearch, setConversationSearch] = useState('')
  const [sidebarVisible, setSidebarVisible] = useState(true)
  const [renameDialog, setRenameDialog] = useState<{ conv: Conversation; value: string } | null>(null)
  const [deleteDialog, setDeleteDialog] = useState<Conversation | null>(null)
  const [dialogBusy, setDialogBusy] = useState(false)
  const renameInputRef = useRef<HTMLInputElement>(null)

  const active = useMemo(() => convs.find((c) => c.id === activeId) ?? null, [convs, activeId])
  const orderedConvs = useMemo(() => {
    const search = conversationSearch.trim().toLowerCase()
    return convs
      .filter((c) => !search || c.title.toLowerCase().includes(search))
      .sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())
  }, [convs, conversationSearch])

  useEffect(() => {
    fetchMe().then(u => setUser(u)).catch(() => {})
  }, [])

  async function refreshConvs() {
    try {
      const data = await listConversations({ archived: false, limit: CONVERSATION_PAGE_SIZE, offset: 0 })
      setConvs(data)
      setActiveId((current) => {
        const fromUrl = new URLSearchParams(window.location.search).get('conversation')
        if (current && data.some((c) => c.id === current)) return current
        if (fromUrl && data.some((c) => c.id === fromUrl)) return fromUrl
        return data[0]?.id ?? null
      })
    } catch (e) {
      console.error(e)
    }
  }

  async function refreshMessages(conversationId: string) {
    try {
      const data = await listMessages(conversationId)
      setMessages(data)
    } catch (e) {
      console.error(e)
    }
  }

  useEffect(() => {
    refreshConvs()
  }, [])

  useEffect(() => {
    if (activeId) refreshMessages(activeId)
  }, [activeId])

  useEffect(() => {
    if (viewportRef.current) {
      viewportRef.current.scrollTop = viewportRef.current.scrollHeight
    }
  }, [messages, sending])

  useEffect(() => {
    if (renameDialog) {
      requestAnimationFrame(() => {
        renameInputRef.current?.focus()
        renameInputRef.current?.select()
      })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [renameDialog?.conv.id])

  async function onNewConversation() {
    try {
      const c = await createConversation({ model_name: 'default', title: 'New conversation' })
      setConvs((prev) => [c, ...prev])
      setActiveId(c.id)
      setMessages([])
    } catch (e) {
      notifications.show({ title: 'Failed to create', message: 'Could not create a new conversation.', color: 'red' })
    }
  }

  function onDeleteConversation(c: Conversation) {
    setDeleteDialog(c)
  }

  async function confirmDeleteConversation() {
    const c = deleteDialog
    if (!c) return
    setDialogBusy(true)
    try {
      await deleteConversation(c.id)
      const remaining = convs.filter(x => x.id !== c.id)
      setConvs(remaining)
      if (activeId === c.id) {
        setActiveId(remaining[0]?.id ?? null)
        setMessages([])
      }
      setDeleteDialog(null)
    } catch (e) {
      notifications.show({ title: 'Error', message: 'Could not delete', color: 'red' })
    } finally {
      setDialogBusy(false)
    }
  }

  function onRenameConversation(c: Conversation) {
    setRenameDialog({ conv: c, value: c.title })
  }

  async function confirmRenameConversation() {
    if (!renameDialog) return
    const title = renameDialog.value.trim()
    if (!title || title === renameDialog.conv.title) {
      setRenameDialog(null)
      return
    }
    setDialogBusy(true)
    try {
      const updated = await renameConversation(renameDialog.conv.id, title)
      setConvs(prev => prev.map(x => x.id === renameDialog.conv.id ? updated : x))
      setRenameDialog(null)
    } catch (e) {
      notifications.show({ title: 'Error', message: 'Could not rename', color: 'red' })
    } finally {
      setDialogBusy(false)
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
            ? { ...msg, pending: false, content: 'I could not generate a response.' }
            : msg,
        ),
      )
    } finally {
      setSending(false)
    }
  }

  async function handleLogout() {
    await logout()
    onLogoutSuccess()
    nav('/auth')
  }

  return (
    <div className="app-shell">
      {/* ──── Sidebar ──── */}
      <div className={`sidebar ${sidebarVisible ? '' : 'hidden'}`}>
        <div className="sidebar-header">
          <div className="sidebar-dot"></div>
          Fieldforce
        </div>

        <div className="sidebar-actions">
          <button className="new-chat-btn" onClick={onNewConversation}>
            <IconPlus size={16} /> New conversation
          </button>
          <div className="search-btn">
            <IconSearch size={16} /> Search
          </div>
        </div>

        <div className="sidebar-section-title">Recent</div>
        
        <div className="sidebar-list">
          {orderedConvs.map((c) => (
            <div key={c.id} className={`sidebar-item-container ${c.id === activeId ? 'active' : ''}`}>
              <button
                className="sidebar-item"
                onClick={() => setActiveId(c.id)}
                title={c.title}
              >
                {c.title || 'New Conversation'}
              </button>
              <div className="sidebar-item-actions">
                <button className="action-icon-btn" onClick={(e) => { e.stopPropagation(); onRenameConversation(c) }}>
                  <IconEdit size={14} />
                </button>
                <button className="action-icon-btn" onClick={(e) => { e.stopPropagation(); onDeleteConversation(c) }}>
                  <IconTrash size={14} />
                </button>
              </div>
            </div>
          ))}
        </div>

        <div className="sidebar-footer">
          <div className="user-profile">
            {user ? (
              <>
                <div className="user-avatar">
                  {user.username.substring(0, 2).toUpperCase()}
                </div>
                <span className="user-name">{user.username}</span>
                <button
                  className="logout-btn"
                  onClick={handleLogout}
                  title="Log out"
                  aria-label="Log out"
                >
                  <IconLogout size={16} />
                </button>
              </>
            ) : (
              <div style={{ visibility: 'hidden' }}>Loading...</div>
            )}
          </div>
        </div>
      </div>

      {/* ──── Main Chat ──── */}
      <div className="chat-main">
        {/* Header */}
        <div className="chat-header">
          <div className="chat-header-left">
            <button className="header-toggle" onClick={() => setSidebarVisible(!sidebarVisible)}>
              <IconMenu2 size={20} />
            </button>
            <h2 className="chat-title">{active?.title ?? 'Select or create a conversation'}</h2>
          </div>
          {active && <span className="chat-sources">3 sources</span>}
        </div>

        {/* Message Area */}
        <div className="messages-container" ref={viewportRef}>
          {messages.length === 0 ? (
            <div className="empty-chat">
              Start a new conversation to ask questions.
            </div>
          ) : (
            messages.map((m) => (
              <div key={m.id} className={`message-row ${m.role}`}>
                <div className="message-bubble">
                  {m.role === 'user' ? (
                    m.content
                  ) : (
                    <>
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {m.content || (m.pending ? 'Thinking...' : '')}
                      </ReactMarkdown>
                      
                      {/* Fake Citations mimicking the design */}
                      {!m.pending && m.content.length > 50 && (
                        <div className="citations-row">
                          <div className="citation-pill"><IconFileText size={12}/> Q3_Policy.pdf p. 4</div>
                          <div className="citation-pill"><IconFileText size={12}/> Q3_Policy.pdf p. 12</div>
                          <div className="citation-pill"><IconFileText size={12}/> Handbook.pdf p. 7</div>
                        </div>
                      )}
                    </>
                  )}
                </div>
              </div>
            ))
          )}
        </div>

        {/* Composer */}
        <div className="composer-container">
          <div className="composer-box">
            <IconPaperclip size={18} className="composer-icon" />
            <textarea
              className="composer-input"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  onSend()
                }
              }}
              placeholder="Ask anything..."
              rows={1}
              disabled={!activeId || sending}
            />
            <button
              className="composer-send"
              onClick={onSend}
              disabled={!activeId || sending || !draft.trim()}
            >
              <IconArrowUp size={16} stroke={3} />
            </button>
          </div>
          <div className="composer-footer">
            Fieldforce can make mistakes. Verify before acting.
          </div>
        </div>
      </div>

      {/* ──── Rename Dialog ──── */}
      {renameDialog && (
        <div className="modal-overlay" onClick={() => !dialogBusy && setRenameDialog(null)}>
          <div className="modal-card" onClick={(e) => e.stopPropagation()}>
            <h3 className="modal-title">Rename conversation</h3>
            <p className="modal-subtitle">Give this conversation a new name.</p>
            <input
              ref={renameInputRef}
              className="modal-input"
              value={renameDialog.value}
              onChange={(e) => setRenameDialog({ ...renameDialog, value: e.target.value })}
              onKeyDown={(e) => {
                if (e.key === 'Enter') { e.preventDefault(); confirmRenameConversation() }
                if (e.key === 'Escape') setRenameDialog(null)
              }}
              maxLength={120}
              disabled={dialogBusy}
            />
            <div className="modal-actions">
              <button
                className="modal-btn modal-btn-ghost"
                onClick={() => setRenameDialog(null)}
                disabled={dialogBusy}
              >
                Cancel
              </button>
              <button
                className="modal-btn modal-btn-primary"
                onClick={confirmRenameConversation}
                disabled={dialogBusy || !renameDialog.value.trim()}
              >
                Save
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ──── Delete Dialog ──── */}
      {deleteDialog && (
        <div className="modal-overlay" onClick={() => !dialogBusy && setDeleteDialog(null)}>
          <div className="modal-card" onClick={(e) => e.stopPropagation()}>
            <h3 className="modal-title">Delete conversation</h3>
            <p className="modal-subtitle">
              Are you sure you want to delete <strong>{deleteDialog.title || 'this conversation'}</strong>? This action can&apos;t be undone.
            </p>
            <div className="modal-actions">
              <button
                className="modal-btn modal-btn-ghost"
                onClick={() => setDeleteDialog(null)}
                disabled={dialogBusy}
              >
                Cancel
              </button>
              <button
                className="modal-btn modal-btn-danger"
                onClick={confirmDeleteConversation}
                disabled={dialogBusy}
              >
                {dialogBusy ? 'Deleting…' : 'Delete'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}