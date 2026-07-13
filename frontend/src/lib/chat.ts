import { API_BASE_URL, apiFetch, getAccessToken } from "./api-client";
import type { Conversation, Message } from "./types";
export function listConversations(opts?: {
  archived?: boolean;
  limit?: number;
  offset?: number;
}) {
  const archived = opts?.archived ?? false;
  const limit = opts?.limit ?? 50;
  const offset = opts?.offset ?? 0;
  return apiFetch<Conversation[]>(
    `/conversations?archived=${archived}&limit=${limit}&offset=${offset}`,
  );
}
export function createConversation(input: { title?: string; model_name: string }) {
  return apiFetch<Conversation>("/conversations", {
    method: "POST",
    body: JSON.stringify({
      title: input.title,
      model_name: input.model_name,
      generation_config: {},
    }),
  });
}
export function renameConversation(conversationId: string, title: string) {
  const params = new URLSearchParams({ title });
  return apiFetch<Conversation>(
    `/conversations/${conversationId}?${params.toString()}`,
    { method: "PATCH" },
  );
}
export function deleteConversation(conversationId: string) {
  return apiFetch<void>(`/conversations/${conversationId}`, { method: "DELETE" });
}
export function listMessages(conversationId: string) {
  return apiFetch<Message[]>(`/conversations/${conversationId}/messages`);
}
export type StreamHandlers = {
  onToken?: (token: string) => void;
  onFinal?: (payload: Record<string, unknown>) => void;
  signal?: AbortSignal;
};
export async function streamMessage(
  conversationId: string,
  content: string,
  handlers: StreamHandlers = {},
  parentMessageId?: string | null,
) {
  const token = getAccessToken();
  const res = await fetch(
    `${API_BASE_URL}/conversations/${conversationId}/messages`,
    {
      method: "POST",
      headers: {
        Accept: "text/event-stream",
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ content, parent_message_id: parentMessageId ?? null }),
      signal: handlers.signal,
    },
  );
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const payload = await res.json();
      detail = payload.detail ?? detail;
    } catch {
      /* keep status */
    }
    throw new Error(detail);
  }
  if (!res.body) return;
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    // Server-Sent Events framed by blank lines
    const events = buffer.split("\n\n");
    buffer = events.pop() ?? "";
    for (const chunk of events) {
      const lines = chunk.split("\n").filter(Boolean);
      let eventType = "message";
      const dataLines: string[] = [];
      for (const line of lines) {
        if (line.startsWith("event:")) eventType = line.slice(6).trim();
        else if (line.startsWith("data:")) dataLines.push(line.slice(5).trim());
      }
      const dataStr = dataLines.join("\n");
      if (!dataStr) continue;
      try {
        const payload = JSON.parse(dataStr);
        if (eventType === "token" || typeof payload?.token === "string") {
          handlers.onToken?.(payload.token ?? payload.delta ?? "");
        } else if (eventType === "final" || eventType === "done" || payload?.message) {
          handlers.onFinal?.(payload);
        }
      } catch {
        // Fallback: treat raw string as token
        handlers.onToken?.(dataStr);
      }
    }
  }
}