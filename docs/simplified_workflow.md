# RAG Chatbot - Simplified Workflow

This document provides a simple, easy-to-understand breakdown of how the RAG (Retrieval-Augmented Generation) Chatbot works behind the scenes.

## 1. User Accounts & Login
- **Sign Up**: When a new user registers, we securely scramble (hash) their password so it's never stored as plain text. 
- **Login**: We verify the password and give the user a temporary "Access Badge" (JWT Token) for quick access, and a long-lasting "Refresh Key" to stay logged in without typing their password constantly.
- **Logout**: We invalidate the "Refresh Key", forcing the user to log in again next time.

## 2. Conversations (Chat Threads)
- **Starting a Chat**: When you start a chat, we create a new thread. 
- **Auto-Naming**: After the first few messages, the system secretly asks the AI to read the messages and come up with a short, descriptive title for the chat (e.g., "Discussing Q3 Policies").
- **Search & History**: All messages are securely saved. You can scroll back through old chats or use a search bar to find past topics.

## 3. Uploading & Processing Documents
This is how the chatbot learns about your specific files.
- **Upload**: You upload a file (PDF, Word doc, Image). The system checks if anyone has uploaded this exact file before to save space (deduplication).
- **Processing**: 
  1. **Extraction**: The system extracts all the raw text from your file.
  2. **Chunking**: It chops the text into smaller, readable paragraphs.
  3. **Understanding (Embedding)**: It uses an AI model to convert these chunks into mathematical coordinates so the system can understand the *meaning* of the text, not just the exact words.

## 4. Sending a Message (The Core Chat Loop)
When you type a question into the chat, here is what happens:
1. **Understand the Question**: We convert your question into mathematical coordinates, just like we did with the documents.
2. **Find the Answers (Retrieval)**: We compare your question's coordinates to all the document chunks we saved earlier. The system fetches the paragraphs that are most relevant to your question.
3. **Ask the AI (Generation)**: We send your original question, the recent chat history, AND the relevant document paragraphs to the main AI model.
4. **Stream the Response**: The AI reads the paragraphs and types out an answer to you in real-time.
5. **Citations**: The system remembers exactly which paragraphs the AI read, and attaches them to the bottom of the message as sources so you can verify the facts.

## 5. Security & Protections
- **Safety Guards**: We explicitly tell the AI to treat your documents as "reference material only," so a malicious document can't trick the AI into breaking the rules.
- **Rate Limiting**: To prevent abuse and control costs, the system limits how many messages a single user can send in a short amount of time.
