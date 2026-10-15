// Every call goes to a relative /api path. nginx (docker compose) or the
// Kubernetes Ingress routes it to the backend, so the browser never needs
// to know the backend's address.

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

function describe(data, response) {
  const detail = data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail.map((err) => `${err.loc?.at(-1) ?? 'field'}: ${err.msg}`).join('; ');
  }
  return `Request failed with status ${response.status}`;
}

function toQuery(params = {}) {
  const query = new URLSearchParams(
    Object.entries(params).filter(([, value]) => value !== '' && value != null),
  );
  return query.size ? `?${query}` : '';
}

async function request(path, { method = 'GET', body } = {}) {
  let response;
  try {
    response = await fetch(`/api${path}`, {
      method,
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError('Cannot reach the ClinicCare API', 0);
  }
  if (response.status === 204) return null;
  const data = await response.json().catch(() => null);
  if (!response.ok) throw new ApiError(describe(data, response), response.status);
  return data;
}

export const api = {
  info: () => request('/info'),
  stats: () => request('/stats'),

  appointments: (filters) => request(`/appointments${toQuery(filters)}`),
  bookAppointment: (body) => request('/appointments', { method: 'POST', body }),
  setAppointmentStatus: (id, status) =>
    request(`/appointments/${id}/status`, { method: 'PATCH', body: { status } }),
  deleteAppointment: (id) => request(`/appointments/${id}`, { method: 'DELETE' }),

  patients: (filters) => request(`/patients${toQuery(filters)}`),
  createPatient: (body) => request('/patients', { method: 'POST', body }),
  deletePatient: (id) => request(`/patients/${id}`, { method: 'DELETE' }),

  doctors: (filters) => request(`/doctors${toQuery(filters)}`),
  createDoctor: (body) => request('/doctors', { method: 'POST', body }),
  updateDoctor: (id, body) => request(`/doctors/${id}`, { method: 'PUT', body }),
};
