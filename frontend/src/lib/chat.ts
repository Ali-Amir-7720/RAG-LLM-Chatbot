import { apiFetch } from './api'
import type { Conversation, Message } from './types'

export function listConversations(opts?: { archived?: boolean }) {
  const archived = opts?.archived ?? false
  return apiFetch<Conversation[]>(`/conversations?archived=${archived}`)
}

export function createConversation(input: { title?: string; model_name: string }) {
  return apiFetch<Conversation>('/conversations', {
    method: 'POST',
    body: JSON.stringify({
      title: input.title,
      model_name: input.model_name,
      generation_config: {},
    }),
  })
}

export function listMessages(conversationId: string) {
  return apiFetch<Message[]>(`/conversations/${conversationId}/messages`)
}

export function sendMessage(conversationId: string, content: string, parentMessageId?: string | null) {
  return apiFetch<Message>(`/conversations/${conversationId}/messages`, {
    method: 'POST',
    body: JSON.stringify({ content, parent_message_id: parentMessageId ?? null }),
  })
}

