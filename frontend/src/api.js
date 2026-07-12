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
  updateMe(token, payload) {
    // 个人资料只允许改邮箱、名和姓，用户名一般作为登录标识不让前端随便改。
    return request('/api/users/me/', { token, method: 'PATCH', body: payload });
  },
  changePassword(token, payload) {
    // 修改密码是明确的业务动作，所以后端单独提供了 change-password 接口。
    return request('/api/users/change-password/', { token, method: 'POST', body: payload });
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
  assign(token, id, assignee) {
    // assignee 传用户 ID；传 null 表示取消当前处理人。
    return request(`/api/tickets/${id}/assign/`, { token, method: 'POST', body: { assignee } });
  },
  remind(token, id, message) {
    // 催办不会改变工单状态，只负责通知当前处理人。
    return request(`/api/tickets/${id}/remind/`, { token, method: 'POST', body: { message } });
  },
  close(token, id, reason) {
    return request(`/api/tickets/${id}/close/`, { token, method: 'POST', body: { reason } });
  },
  reopen(token, id, reason) {
    return request(`/api/tickets/${id}/reopen/`, { token, method: 'POST', body: { reason } });
  },
  setPriority(token, id, priority) {
    return request(`/api/tickets/${id}/set-priority/`, { token, method: 'POST', body: { priority } });
  },
  setTags(token, id, tags) {
    // 后端接收标签 ID 数组，例如 { tags: [1, 2] }。
    return request(`/api/tickets/${id}/set-tags/`, { token, method: 'POST', body: { tags } });
  },
  watch(token, id) {
    return request(`/api/tickets/${id}/watch/`, { token, method: 'POST' });
  },
  unwatch(token, id) {
    return request(`/api/tickets/${id}/unwatch/`, { token, method: 'POST' });
  },
  attachments(token, id) {
    return request(`/api/tickets/${id}/attachments/`, { token });
  },
  uploadAttachment(token, id, file) {
    const formData = new FormData();
    formData.append('file', file);
    return request(`/api/tickets/${id}/attachments/`, { token, method: 'POST', body: formData });
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
  markRead(token, id) {
    return request(`/api/notifications/${id}/mark-read/`, { token, method: 'POST' });
  },
  clearRead(token) {
    return request('/api/notifications/clear-read/', { token, method: 'DELETE' });
  },
};
