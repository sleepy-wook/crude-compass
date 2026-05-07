// FastAPI client — fetch helpers
// Vite dev: /api/* proxied to http://127.0.0.1:8000 (vite.config.ts)
// Apps prod: same FastAPI prefix, no proxy needed

const BASE = ''  // same origin

async function jsonFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(BASE + path, {
    headers: { 'content-type': 'application/json', ...(init?.headers ?? {}) },
    ...init,
  })
  if (!res.ok) {
    throw new Error(`API ${path} failed: ${res.status} ${res.statusText}`)
  }
  return res.json() as Promise<T>
}

export const api = {
  health: () => jsonFetch<{ status: string }>('/api/health'),
  feed: () => jsonFetch('/api/feed'),
  mission: (id: string) => jsonFetch(`/api/mission/${id}`),
  genie: (query: string, missionId?: string) =>
    jsonFetch('/api/genie', {
      method: 'POST',
      body: JSON.stringify({ query, mission_id: missionId }),
    }),
  decision: (payload: unknown) =>
    jsonFetch('/api/decision', { method: 'POST', body: JSON.stringify(payload) }),
  dashboardToken: () => jsonFetch<{ token: string; expires_in: number }>('/api/dashboard/token'),
}
