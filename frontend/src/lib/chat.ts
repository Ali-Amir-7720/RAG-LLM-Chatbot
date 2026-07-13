import { API_BASE_URL, apiFetch } from './api'
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

export async function streamMessage(
  conversationId: string,
  content: string,
  handlers: {
    onToken?: (token: string) => void
    onFinal?: (payload: Record<string, unknown>) => void
  } = {},
  parentMessageId?: string | null,
) {
  const token = localStorage.getItem('access_token')
  const res = await fetch(`${API_BASE_URL}/conversations/${conversationId}/messages`, {
    method: 'POST',
    headers: {
      Accept: 'text/event-stream',
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ content, parent_message_id: parentMessageId ?? null }),
  })

  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`
    try {
      const payload = await res.json()
      detail = payload.detail ?? detail
    } catch {
      // Keep the status text when the response is not JSON.
    }
    throw new Error(detail)
  }

  if (!res.body) return

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { value, done } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const events = buffer.split('\n\n')
    buffer = events.pop() ?? ''

    for (const event of events) {
      const dataLine = event
        .split('\n')
        .find((line) => line.startsWith('data: '))

      if (!dataLine) continue

      try {
        const payload = JSON.parse(dataLine.slice(6))
        if (typeof payload.token === 'string') {
          handlers.onToken?.(payload.token)
        } else {
          handlers.onFinal?.(payload)
        }
      } catch {
        // Ignore malformed stream frames so a single bad token does not kill the UI.
      }
    }
  }
}
