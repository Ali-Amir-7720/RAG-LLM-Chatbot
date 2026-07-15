# Chatbot Workflow - Simple Version

This document explains how the chatbot works in simple steps.

## 1. User Signs Up Or Logs In

- The user creates an account with a username, email, and password.
- The password is saved safely in a scrambled form, not as plain text.
- When the user logs in, the backend gives the browser two keys:
  - a short-time key for normal requests
  - a longer-time key so the user can stay logged in
- When the user logs out, the longer-time key is marked as no longer valid.

## 2. User Starts A Chat

- The user opens a new chat.
- The backend creates a new conversation record.
- Messages in that chat are saved so the user can come back later.
- The chat can be renamed automatically after the first few messages.

## 3. User Uploads A Document

- The user uploads a file, such as a PDF, Word document, or text file.
- The backend checks the file type and size.
- The file is saved on the server.
- The backend reads the text from the file.
- The text is split into smaller pieces so the chatbot can use the right part later.

## 4. System Prepares The Document For Search

- Each small piece of text is converted into a searchable form.
- This helps the backend find which part of the document is related to a user's question.
- The original text pieces are still saved, so the chatbot can read and use them in the answer.

## 5. User Asks A Question

- The user sends a message in the chat.
- The backend saves the user's message.
- The backend looks through the uploaded document pieces.
- It picks the pieces that best match the question.
- It sends the question, recent chat messages, and matching document pieces to the AI model.
- The AI writes an answer and sends it back to the user.
- The assistant message is saved in the conversation.

## 6. User Can Continue The Chat

- The user can ask follow-up questions.
- The backend keeps the conversation history.
- The chatbot can use the recent messages to understand the next question better.

## 7. User Can Manage The Chat

- The user can view old conversations.
- The user can delete conversations.
- The user can export a conversation.
- The user can give feedback on an answer.
- The user can regenerate an answer if needed.

## 8. What The Backend Does Overall

In short:

```text
User logs in
-> User uploads documents
-> Backend reads and splits the documents
-> User asks a question
-> Backend finds useful document parts
-> AI creates an answer
-> Backend saves the chat
```

The main goal is simple: let users chat with their own documents in a safe and organized way.
