# RAG Chatbot - Simplified System Architecture

This document breaks down the core concepts behind the RAG Chatbot's architecture in simple, non-technical terms.

## 1. Why We Use "Tokens" (JWT) Instead of Traditional Sessions
When you log in, we don't want to force the database to check your ID every single time you send a message, load a chat, or click a button. 
Instead, we give your browser a secure, mathematically signed "Access Token" (like a digital passport). The server can instantly verify this token mathematically, without ever looking at the database, making the app incredibly fast.

## 2. Managing Conversation History
If a conversation gets too long, we can't send the entire history to the AI because it will run out of memory (and it costs more money). 
To solve this, the system automatically drops or summarizes older messages as the conversation grows. This ensures the AI only reads what's most relevant to your current topic.

## 3. How Document Search Works (Vector Search)
When you ask a question, we don't just search for exact keywords (like using Ctrl+F). We use **Vector Embeddings**. 
Think of this as plotting concepts on a map. Words like "Puppy" and "Dog" will be plotted very close to each other. When you ask a question, the system finds the text chunks that are mathematically "closest" on the map, meaning they share the same context or meaning, even if the exact words are different.

## 4. Re-ranking (Finding the Best Answer)
Sometimes, the map search brings back too many results that are only loosely related to your question. 
To fix this, we use a second, more precise AI model (a "Re-ranker") to double-check the results. It scores each paragraph based on how perfectly it answers your specific question, and only sends the absolute best ones to the main chat AI.

## 5. Keeping Things Clean (Background Cleanup)
When you delete a conversation, the system doesn't just hide it. It automatically "cascades" that deletion to permanently clean up all the associated messages and file links in the database, ensuring no wasted space or orphaned data is left behind.
