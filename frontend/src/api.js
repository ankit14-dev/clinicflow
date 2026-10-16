// The browser only ever talks to /api on its own origin: nginx (compose) or the
// Kubernetes Ingress routes it to the backend, so no backend hostname is baked in.
const BASE = '/api';

function errorMessage(detail, status) {
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail.map((d) => `${d.loc?.slice(-1)[0] ?? 'field'}: ${d.msg}`).join('; ');
  }
  return `Request failed (${status})`;
}

async function request(path, { method = 'GET', body } = {}) {
  const response = await fetch(BASE + path, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (response.status === 204) return null;
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(errorMessage(data.detail, response.status));
  return data;
}

function resource(name) {
  return {
    list: (params = {}) => {
      const query = new URLSearchParams(Object.entries(params).filter(([, v]) => v !== '' && v != null));
      return request(`/${name}${query.size ? `?${query}` : ''}`);
    },
    create: (payload) => request(`/${name}`, { method: 'POST', body: payload }),
    update: (id, payload) => request(`/${name}/${id}`, { method: 'PUT', body: payload }),
    remove: (id) => request(`/${name}/${id}`, { method: 'DELETE' }),
  };
}

export const api = {
  info: () => request('/info'),
  stats: () => request('/stats'),
  doctors: resource('doctors'),
  patients: resource('patients'),
  appointments: resource('appointments'),
};
