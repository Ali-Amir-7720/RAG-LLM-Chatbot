export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? '/api/v1'

export type ApiError = {
  detail?: string
}

export function getAccessToken(): string | null {
  return localStorage.getItem('access_token')
}

export function getRefreshToken(): string | null {
  return localStorage.getItem('refresh_token')
}

export function setTokens(tokens: { access_token: string; refresh_token: string }) {
  localStorage.setItem('access_token', tokens.access_token)
  localStorage.setItem('refresh_token', tokens.refresh_token)
}

export function clearTokens() {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
}

async function parseJsonSafe(res: Response) {
  const text = await res.text()
  if (!text) return null
  try {
    return JSON.parse(text)
  } catch {
    return null
  }
}

let refreshPromise: Promise<boolean> | null = null

async function tryRefreshToken(): Promise<boolean> {
  const refreshToken = getRefreshToken()
  if (!refreshToken) return false

  // De-dupe concurrent 401s (e.g. several requests firing at once) into one refresh call.
  if (!refreshPromise) {
    refreshPromise = (async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/auth/refresh`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
          body: JSON.stringify({ refresh_token: refreshToken }),
        })
        if (!res.ok) return false
        const data = (await parseJsonSafe(res)) as { access_token?: string; refresh_token?: string } | null
        if (!data?.access_token || !data?.refresh_token) return false
        setTokens({ access_token: data.access_token, refresh_token: data.refresh_token })
        return true
      } catch {
        return false
      } finally {
        refreshPromise = null
      }
    })()
  }
  return refreshPromise
}

function buildHeaders(init: RequestInit & { auth?: boolean }): Headers {
  const headers = new Headers(init.headers)
  headers.set('Accept', 'application/json')

  if (init.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }

  if (init.auth !== false) {
    const token = getAccessToken()
    if (token) headers.set('Authorization', `Bearer ${token}`)
  }

  return headers
}

export async function apiFetch<T>(
  path: string,
  init: RequestInit & { auth?: boolean } = {},
): Promise<T> {
  const url = path.startsWith('http') ? path : `${API_BASE_URL}${path}`

  let res = await fetch(url, { ...init, headers: buildHeaders(init) })

  // Access tokens expire after 15 minutes (see jwt_access_token_ttl_seconds).
  // On a 401, try the refresh token once before giving up.
  if (res.status === 401 && init.auth !== false) {
    const refreshed = await tryRefreshToken()
    if (refreshed) {
      res = await fetch(url, { ...init, headers: buildHeaders(init) })
    } else {
      clearTokens()
      if (typeof window !== 'undefined' && window.location.pathname !== '/auth') {
        window.location.href = '/auth'
      }
      throw new Error('Session expired. Please log in again.')
    }
  }

  if (res.ok) {
    return (await parseJsonSafe(res)) as T
  }

  const err = (await parseJsonSafe(res)) as ApiError | null
  const detail = err?.detail ?? `${res.status} ${res.statusText}`
  throw new Error(detail)
}