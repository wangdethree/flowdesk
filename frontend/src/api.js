const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

export class ApiError extends Error {
  constructor(message, status, data) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

function buildHeaders(token, extraHeaders = {}) {
  const headers = {
    ...extraHeaders,
  };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  return headers;
}

async function parseResponse(response) {
  const contentType = response.headers.get('content-type') || '';
  if (!contentType.includes('application/json')) {
    return null;
  }
  return response.json();
}

export async function request(path, { token, method = 'GET', body, headers } = {}) {
  const isFormData = body instanceof FormData;
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers: buildHeaders(token, {
      ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
      ...headers,
    }),
    body: body ? (isFormData ? body : JSON.stringify(body)) : undefined,
  });
  const data = await parseResponse(response);

  if (!response.ok) {
    const message = data?.detail || data?.non_field_errors?.[0] || '请求失败，请稍后重试。';
    throw new ApiError(message, response.status, data);
  }

  return data;
}

export const authApi = {
  login(payload) {
    return request('/api/users/login/', { method: 'POST', body: payload });
  },
  me(token) {
    return request('/api/users/me/', { token });
  },
};

export const dashboardApi = {
  summary(token) {
    return request('/api/analytics/tickets/summary/', { token });
  },
};

export const ticketApi = {
  list(token, params = {}) {
    const search = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== '' && value !== null && value !== undefined) {
        search.set(key, value);
      }
    });
    const query = search.toString();
    return request(`/api/tickets/${query ? `?${query}` : ''}`, { token });
  },
  detail(token, id) {
    return request(`/api/tickets/${id}/`, { token });
  },
  create(token, payload) {
    return request('/api/tickets/', { token, method: 'POST', body: payload });
  },
  timeline(token, id) {
    return request(`/api/tickets/${id}/timeline/`, { token });
  },
  comments(token, id) {
    return request(`/api/tickets/${id}/comments/`, { token });
  },
  addComment(token, id, payload) {
    return request(`/api/tickets/${id}/comments/`, { token, method: 'POST', body: payload });
  },
  close(token, id, reason) {
    return request(`/api/tickets/${id}/close/`, { token, method: 'POST', body: { reason } });
  },
  feedback(token, id) {
    return request(`/api/tickets/${id}/feedback/`, { token });
  },
  submitFeedback(token, id, payload) {
    return request(`/api/tickets/${id}/feedback/`, { token, method: 'POST', body: payload });
  },
};

export const notificationApi = {
  unreadCount(token) {
    return request('/api/notifications/unread-count/', { token });
  },
  list(token, params = {}) {
    const search = new URLSearchParams(params);
    const query = search.toString();
    return request(`/api/notifications/${query ? `?${query}` : ''}`, { token });
  },
  markAllRead(token) {
    return request('/api/notifications/mark-all-read/', { token, method: 'POST' });
  },
};
