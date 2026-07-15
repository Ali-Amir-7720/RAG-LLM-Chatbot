# Fieldforce Database Guide

This document explains the Fieldforce PostgreSQL schema and how it powers auth, chat, documents, and RAG.

## Current live database (what your app uses now)

Your **running Postgres** is currently a **hybrid** of the old detailed schema and the newer simplified document tables:

### Present tables
1. `users`
2. `user_sessions`
3. `conversations`
4. `messages`
5. `documents`
6. `user_documents`
7. `conversation_documents` (auto-created at startup if missing)
8. `document_chunks`
9. `chunk_embeddings`
10. `embedding_models` (legacy/registry table still present)

### Important reality check
- `users`, `conversations`, and `messages` still contain richer columns from earlier design
  (example: `conversations.model_name`, `users.profile_picture`, `messages.parent_message_id`)
- `documents`, `document_chunks`, and `chunk_embeddings` already match the newer simplified shape
- File `database/schema.sql` describes a fully simplified target schema and is **not identical** to the live DB yet

The API was aligned to the **live DB**, so create-conversation / auth / messaging work against your current Postgres.

---

## Target simplified schema (`database/schema.sql`)

The SQL file describes a cleaned 8-table design:

1. `users`
2. `user_sessions`
3. `conversations`
4. `messages`
5. `documents`
6. `user_documents`
7. `conversation_documents`
8. `document_chunks`
9. `chunk_embeddings`

### Why simplify?
- Faster to implement and reason about
- Clear ownership boundaries
- Enough structure for RAG retrieval without extra metadata tables

---

## How the pieces fit together

```text
users
  ├── user_sessions                 # refresh-token sessions for JWT hybrid auth
  ├── conversations                 # chat threads
  │     ├── messages                # user/assistant transcript
  │     └── conversation_documents  # docs in scope for this chat's RAG
  └── user_documents                # docs owned/accessible by user

documents
  └── document_chunks
        └── chunk_embeddings        # vector(1536) for similarity search
```

---

## Thorough table explanations

### 1) `users`
Stores identity and password hash.

Typical columns in live DB:
- `id`, `username`, `email`, `password_hash`
- optional `profile_picture`, `created_at`, `updated_at`

Used by: signup/login, `/users/me`

### 2) `user_sessions`
Tracks refresh tokens for logout, logout-everywhere, and rotation.

Why JWT access + server refresh sessions?
- Access JWT is short-lived and verified without DB lookup (fast for chat requests)
- Refresh token is stored here so revocation is possible

### 3) `conversations`
One chat thread.

Live DB still includes model/config fields:
- `model_name` (required)
- `system_prompt`
- `generation_config`
- `is_archived`
- plus `title`, timestamps

### 4) `messages`
Transcript rows with `role` (`user`/`assistant`/`system`) and `content`.

Live DB still includes optional branching/feedback fields:
- `parent_message_id`
- `model_name`, `token_count`, `generation_time`
- `is_helpful`, `feedback_text`

### 5) `documents`
Canonical file metadata (`name`, `storage_path`, `mime_type`, `file_size`).

### 6) `user_documents`
Many-to-many ownership/access map: user ↔ document.

### 7) `conversation_documents`
Many-to-many RAG scope map: conversation ↔ document.
This is the key leak-prevention boundary for retrieval.

### 8) `document_chunks`
Text passages extracted from a document (`chunk_number`, `chunk_text`).

### 9) `chunk_embeddings`
Vector embedding per chunk (`VECTOR(1536)`).
Query time uses cosine distance (`<=>`) via pgvector.

---

## Feature → table map

| Feature | Tables |
|---|---|
| Signup/login/refresh/logout | `users`, `user_sessions` |
| Create/list/rename/delete chats | `conversations` |
| Send/list/stream messages | `messages` (+ retrieval join path) |
| Upload docs | `documents`, `user_documents`, optional `conversation_documents` |
| Chunk + embed | `document_chunks`, `chunk_embeddings` |
| RAG retrieval | `conversation_documents` → `document_chunks` → `chunk_embeddings` |

---

## End-to-end flows

### Auth
1. Insert `users`
2. Insert `user_sessions` refresh token
3. Return access JWT + refresh token

### Create conversation
1. Insert into `conversations` (including required `model_name` on live DB)
2. Return conversation id/title

### Ask a question
1. Insert user `messages` row
2. Retrieve top chunks for attached docs
3. Stream LLM tokens
4. Insert assistant `messages` row
5. Optionally update conversation title

### Upload a document
1. Store file bytes
2. Insert `documents`
3. Link via `user_documents` / `conversation_documents`
4. Background: chunk + embed

---

## What broke before (and what we fixed)

Create conversation returned **500** because:
- Live DB required `conversations.model_name NOT NULL`
- API insert omitted `model_name`

Fixed by writing `model_name` (default `"default"`) again and aligning auth/user queries to live columns.

Backend is running at `http://127.0.0.1:8000` and create-conversation was verified successfully.

---

## Recommendation next

If you want a fully simplified DB:
1. Take a backup
2. Apply a migration from live hybrid → `database/schema.sql`
3. Keep API and frontend in sync with the final shape

Until then, treat **live Postgres columns** as source of truth for runtime behavior, and treat `schema.sql` as the intended clean target.
