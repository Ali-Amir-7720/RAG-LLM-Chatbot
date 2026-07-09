import { apiFetch, clearTokens, setTokens } from './api'
import type { AuthResponse } from './types'

export async function signup(input: { username: string; email: string; password: string }) {
  const res = await apiFetch<AuthResponse>('/auth/signup', {
    method: 'POST',
    body: JSON.stringify(input),
    auth: false,
  })
  setTokens(res.tokens)
  return res.user
}

export async function login(input: { email: string; password: string; device?: string }) {
  const res = await apiFetch<AuthResponse>('/auth/login', {
    method: 'POST',
    body: JSON.stringify(input),
    auth: false,
  })
  setTokens(res.tokens)
  return res.user
}

export async function logout() {
  const refreshToken = localStorage.getItem('refresh_token')
  if (!refreshToken) return
  try {
    await apiFetch('/auth/logout', {
      method: 'POST',
      body: JSON.stringify({ refresh_token: refreshToken }),
      auth: false,
    })
  } finally {
    clearTokens()
  }
}

