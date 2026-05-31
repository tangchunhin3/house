const BASE = '/api';

async function fetchJson(url, options = {}) {
  const res = await fetch(`${BASE}${url}`, options)
  if (!res.ok) throw new Error(`API error: ${res.status}`)
  return res.json()
}

export function getTransactions(params = {}) {
  const q = new URLSearchParams()
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '') q.set(k, v)
  })
  return fetchJson(`/transactions?${q}`)
}

export function getProperties(params = {}) {
  const q = new URLSearchParams()
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '') q.set(k, v)
  })
  return fetchJson(`/properties?${q}`)
}

export function getSources() {
  return fetchJson('/sources')
}

export function getStats() {
  return fetchJson('/stats')
}

export function triggerScrape() {
  return fetchJson('/scrape', { method: 'POST' })
}

export function triggerSearch(q) {
  return fetchJson(`/search?q=${encodeURIComponent(q)}`, { method: 'POST' })
}

export function getSessions(limit = 5) {
  return fetchJson(`/sessions?limit=${limit}`)
}

export function getCurrentSession() {
  return fetchJson('/sessions/current')
}

export function getEstates(search = '') {
  const q = search ? `?search=${encodeURIComponent(search)}` : ''
  return fetchJson(`/estates${q}`)
}

export function getEstateAnalysis(name) {
  return fetchJson(`/estates/${encodeURIComponent(name)}/analysis`)
}
