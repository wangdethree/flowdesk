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

function normalizeErrorMessage(data) {
  // DRF 的错误响应有多种形态：
  // - { detail: '...' } 常见于权限、认证和 404
  // - { non_field_errors: ['...'] } 常见于整体表单校验
  // - { field: ['...'] } 常见于字段校验，例如密码太短、标题不能为空
  // 前端统一整理成一句话，用户才知道具体哪里填错了。
  if (!data) return '请求失败，请稍后重试。';
  if (typeof data.detail === 'string') return data.detail;
  if (Array.isArray(data.non_field_errors) && data.non_field_errors.length) {
    return data.non_field_errors[0];
  }

  const fieldError = Object.entries(data).find(([, value]) => {
    return Array.isArray(value) && value.length > 0;
  });
  if (fieldError) {
    const [field, messages] = fieldError;
    return `${field}: ${messages[0]}`;
  }

  return '请求失败，请稍后重试。';
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
    const message = normalizeErrorMessage(data);
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

export const assistantApi = {
  draftTicket(token, rawText) {
    // 根据自然语言描述生成工单草稿，当前后端是规则引擎，后续可以替换成大模型。
    return request('/api/ai/ticket-draft/', { token, method: 'POST', body: { raw_text: rawText } });
  },
  ticketSuggestion(token, id) {
    return request(`/api/ai/tickets/${id}/suggestion/`, { token });
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
  update(token, id, payload) {
    // 工单基础信息和合法状态流转走 PATCH，由后端统一校验权限和状态流转规则。
    return request(`/api/tickets/${id}/`, { token, method: 'PATCH', body: payload });
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

export const tagApi = {
  list(token, params = {}) {
    const search = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== '' && value !== null && value !== undefined) {
        search.set(key, value);
      }
    });
    const query = search.toString();
    return request(`/api/ticket-tags/${query ? `?${query}` : ''}`, { token });
  },
  create(token, payload) {
    // 标签是可复用资源，创建后可以绑定到多张工单上。
    return request('/api/ticket-tags/', { token, method: 'POST', body: payload });
  },
};

export const notificationApi = {
  unreadCount(token) {
    return request('/api/notifications/unread-count/', { token });
  },
  list(token, params = {}) {
    const search = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== '' && value !== null && value !== undefined) {
        search.set(key, value);
      }
    });
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
