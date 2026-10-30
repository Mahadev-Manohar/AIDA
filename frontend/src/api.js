import { API_BASE } from './config';

async function errorFrom(res, fallback) {
  try {
    const body = await res.json();
    return body.detail || fallback;
  } catch {
    return fallback;
  }
}

/** Absolute chart URL; the version param busts the cache when a chart is regenerated. */
export function plotUrl(path) {
  return `${API_BASE}${path}?v=${Date.now()}`;
}

export async function fetchConfig() {
  const res = await fetch(`${API_BASE}/api/config`);
  if (!res.ok) throw new Error('Config request failed');
  return res.json();
}

export async function fetchDataset() {
  const res = await fetch(`${API_BASE}/api/dataset`);
  if (!res.ok) throw new Error('Dataset request failed');
  return res.json();
}

export async function clearDataset() {
  const res = await fetch(`${API_BASE}/api/dataset`, { method: 'DELETE' });
  if (!res.ok) throw new Error(await errorFrom(res, 'Failed to clear dataset'));
}

/** Uploads a CSV with progress reporting (fetch cannot report upload progress). */
export function uploadCsv(file, onProgress) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', `${API_BASE}/api/upload`);
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) onProgress?.(e.loaded / e.total);
    };
    xhr.onload = () => {
      let body = null;
      try {
        body = JSON.parse(xhr.responseText);
      } catch {
        /* non-JSON response */
      }
      if (xhr.status >= 200 && xhr.status < 300) resolve(body);
      else reject(new Error(body?.detail || `Upload failed (${xhr.status})`));
    };
    xhr.onerror = () => reject(new Error('Cannot reach the backend. Is it running?'));
    const form = new FormData();
    form.append('file', file);
    xhr.send(form);
  });
}

/** Streams agent steps (Server-Sent Events) as an async generator of parsed events. */
export async function* streamQuery(query, signal) {
  const res = await fetch(`${API_BASE}/api/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query }),
    signal,
  });
  if (!res.ok) throw new Error(await errorFrom(res, 'Query execution failed'));

  const reader = res.body.getReader();
  const decoder = new TextDecoder('utf-8');
  let buffer = '';

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const events = buffer.split('\n\n');
    buffer = events.pop();

    for (const evt of events) {
      const line = evt.trim();
      if (!line.startsWith('data:')) continue;
      const payload = line.slice(5).trim();
      if (!payload) continue;
      try {
        yield JSON.parse(payload);
      } catch (err) {
        console.error('Failed to parse stream event:', payload, err);
      }
    }
  }
}
