<template>
  <main v-if="!token" class="login-page">
    <section class="login-panel">
      <div>
        <p class="eyebrow">FlowDesk</p>
        <h1>企业工单流转后台</h1>
        <p class="muted">登录后可以查看工单、处理动态、通知和统计摘要。</p>
      </div>

      <form class="login-form" @submit.prevent="login">
        <label>
          用户名
          <input v-model.trim="loginForm.username" autocomplete="username" required />
        </label>
        <label>
          密码
          <input v-model="loginForm.password" autocomplete="current-password" required type="password" />
        </label>
        <button class="primary-button" :disabled="loading" type="submit">
          {{ loading ? '登录中' : '登录' }}
        </button>
        <p v-if="errorMessage" class="error-text">{{ errorMessage }}</p>
      </form>
    </section>
  </main>

  <main v-else class="app-shell">
    <aside class="sidebar">
      <div class="brand">
        <span class="brand-mark">F</span>
        <div>
          <strong>FlowDesk</strong>
          <small>工单管理后台</small>
        </div>
      </div>

      <nav class="nav-list">
        <button :class="{ active: activeView === 'dashboard' }" @click="activeView = 'dashboard'">统计看板</button>
        <button :class="{ active: activeView === 'tickets' }" @click="activeView = 'tickets'">工单中心</button>
        <button :class="{ active: activeView === 'notifications' }" @click="activeView = 'notifications'">
          通知中心
          <span v-if="unreadCount" class="badge">{{ unreadCount }}</span>
        </button>
      </nav>

      <div class="user-box">
        <span>{{ currentUser?.username }}</span>
        <button class="ghost-button" @click="logout">退出</button>
      </div>
    </aside>

    <section class="workspace">
      <header class="topbar">
        <div>
          <h2>{{ pageTitle }}</h2>
          <p class="muted">{{ pageSubtitle }}</p>
        </div>
        <button class="secondary-button" :disabled="loading" @click="refreshCurrentView">刷新</button>
      </header>

      <p v-if="errorMessage" class="notice error-text">{{ errorMessage }}</p>

      <section v-if="activeView === 'dashboard'" class="dashboard-grid">
        <article class="metric-card">
          <span>工单总数</span>
          <strong>{{ summary?.total ?? 0 }}</strong>
        </article>
        <article class="metric-card">
          <span>分配给我</span>
          <strong>{{ summary?.assigned_to_me ?? 0 }}</strong>
        </article>
        <article class="metric-card warning">
          <span>超时工单</span>
          <strong>{{ summary?.overdue ?? 0 }}</strong>
        </article>
        <article class="metric-card success">
          <span>平均评分</span>
          <strong>{{ summary?.feedback?.average_rating ?? 0 }}</strong>
        </article>

        <article class="panel span-2">
          <div class="panel-header">
            <h3>状态分布</h3>
          </div>
          <div class="bar-list">
            <div v-for="item in statusChart" :key="item.key" class="bar-row">
              <span>{{ item.label }}</span>
              <div class="bar-track">
                <div class="bar-fill" :style="{ width: item.percent + '%' }"></div>
              </div>
              <b>{{ item.value }}</b>
            </div>
          </div>
        </article>

        <article class="panel span-2">
          <div class="panel-header">
            <h3>评价摘要</h3>
          </div>
          <div class="feedback-summary">
            <div>
              <span>评价数</span>
              <strong>{{ summary?.feedback?.feedback_count ?? 0 }}</strong>
            </div>
            <div>
              <span>满意率</span>
              <strong>{{ satisfactionText }}</strong>
            </div>
          </div>
          <div class="rating-list">
            <div v-for="rating in [5, 4, 3, 2, 1]" :key="rating">
              <span>{{ rating }} 星</span>
              <strong>{{ summary?.feedback?.by_rating?.[rating] ?? 0 }}</strong>
            </div>
          </div>
        </article>
      </section>

      <section v-if="activeView === 'tickets'" class="tickets-layout">
        <section class="panel list-panel">
          <div class="panel-header">
            <h3>工单列表</h3>
            <button class="secondary-button" @click="showCreateTicket = !showCreateTicket">
              {{ showCreateTicket ? '收起' : '新建' }}
            </button>
          </div>

          <form class="filter-row" @submit.prevent="loadTickets">
            <input v-model.trim="ticketFilters.search" placeholder="搜索标题或描述" />
            <select v-model="ticketFilters.status">
              <option value="">全部状态</option>
              <option value="open">待处理</option>
              <option value="in_progress">处理中</option>
              <option value="resolved">已解决</option>
              <option value="closed">已关闭</option>
            </select>
            <select v-model="ticketFilters.mine">
              <option value="">全部可见</option>
              <option value="created">我创建的</option>
              <option value="assigned">分配给我的</option>
              <option value="watched">我关注的</option>
            </select>
            <button class="secondary-button" type="submit">筛选</button>
          </form>

          <form v-if="showCreateTicket" class="create-form" @submit.prevent="createTicket">
            <input v-model.trim="ticketForm.title" placeholder="工单标题" required />
            <textarea v-model.trim="ticketForm.description" placeholder="问题描述" required></textarea>
            <div class="form-grid">
              <select v-model="ticketForm.category">
                <option value="bug">故障问题</option>
                <option value="feature">功能需求</option>
                <option value="consult">咨询支持</option>
                <option value="other">其他</option>
              </select>
              <select v-model="ticketForm.priority">
                <option value="low">低</option>
                <option value="medium">中</option>
                <option value="high">高</option>
                <option value="urgent">紧急</option>
              </select>
            </div>
            <button class="primary-button" type="submit">创建工单</button>
          </form>

          <div class="ticket-list">
            <button
              v-for="ticket in tickets"
              :key="ticket.id"
              :class="{ selected: selectedTicket?.id === ticket.id }"
              class="ticket-row"
              @click="openTicket(ticket.id)"
            >
              <span class="ticket-title">{{ ticket.title }}</span>
              <span class="tag-row">
                <small>{{ statusLabel(ticket.status) }}</small>
                <small>{{ priorityLabel(ticket.priority) }}</small>
              </span>
            </button>
          </div>
        </section>

        <section class="panel detail-panel">
          <template v-if="selectedTicket">
            <div class="detail-heading">
              <div>
                <h3>{{ selectedTicket.title }}</h3>
                <p>{{ selectedTicket.description }}</p>
              </div>
              <span class="status-pill">{{ statusLabel(selectedTicket.status) }}</span>
            </div>

            <div class="detail-meta">
              <span>创建人：{{ selectedTicket.creator_username }}</span>
              <span>处理人：{{ selectedTicket.assignee_username || '未分配' }}</span>
              <span>优先级：{{ priorityLabel(selectedTicket.priority) }}</span>
            </div>

            <div class="action-row">
              <button v-if="selectedTicket.status !== 'closed'" class="secondary-button" @click="showCloseForm = !showCloseForm">
                关闭工单
              </button>
              <button v-if="selectedTicket.status === 'closed'" class="secondary-button" @click="showFeedbackForm = !showFeedbackForm">
                评价工单
              </button>
            </div>

            <form v-if="showCloseForm" class="inline-form" @submit.prevent="closeSelectedTicket">
              <textarea v-model.trim="closeReason" placeholder="填写关闭原因" required></textarea>
              <button class="primary-button" type="submit">确认关闭</button>
            </form>

            <form v-if="showFeedbackForm" class="inline-form" @submit.prevent="submitFeedback">
              <select v-model.number="feedbackForm.rating">
                <option :value="5">5 星</option>
                <option :value="4">4 星</option>
                <option :value="3">3 星</option>
                <option :value="2">2 星</option>
                <option :value="1">1 星</option>
              </select>
              <textarea v-model.trim="feedbackForm.content" placeholder="评价内容"></textarea>
              <button class="primary-button" type="submit">提交评价</button>
            </form>

            <form class="inline-form" @submit.prevent="addComment">
              <textarea v-model.trim="commentForm.content" placeholder="补充评论或处理记录" required></textarea>
              <select v-model="commentForm.comment_type">
                <option value="comment">普通评论</option>
                <option value="handling">处理记录</option>
              </select>
              <button class="secondary-button" type="submit">添加记录</button>
            </form>

            <div class="timeline">
              <h4>工单时间线</h4>
              <article v-for="item in timeline" :key="`${item.event_type}-${item.object_id}`" class="timeline-item">
                <span>{{ item.title }}</span>
                <p>{{ item.content || eventTypeLabel(item.event_type) }}</p>
                <small>{{ item.actor_username || '系统' }} · {{ formatDate(item.created_at) }}</small>
              </article>
            </div>
          </template>
          <div v-else class="empty-state">选择一张工单查看详情。</div>
        </section>
      </section>

      <section v-if="activeView === 'notifications'" class="panel">
        <div class="panel-header">
          <h3>通知中心</h3>
          <button class="secondary-button" @click="markAllRead">全部已读</button>
        </div>
        <div class="notification-list">
          <article v-for="item in notifications" :key="item.id" class="notification-item" :class="{ unread: !item.is_read }">
            <div>
              <strong>{{ item.title }}</strong>
              <p>{{ item.message }}</p>
            </div>
            <small>{{ formatDate(item.created_at) }}</small>
          </article>
        </div>
      </section>
    </section>
  </main>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue';
import { authApi, dashboardApi, notificationApi, ticketApi } from './api';

const token = ref(localStorage.getItem('flowdesk_access') || '');
const currentUser = ref(null);
const activeView = ref('dashboard');
const loading = ref(false);
const errorMessage = ref('');

const summary = ref(null);
const tickets = ref([]);
const selectedTicket = ref(null);
const timeline = ref([]);
const notifications = ref([]);
const unreadCount = ref(0);

const showCreateTicket = ref(false);
const showCloseForm = ref(false);
const showFeedbackForm = ref(false);
const closeReason = ref('');

const loginForm = reactive({
  username: '',
  password: '',
});

const ticketFilters = reactive({
  search: '',
  status: '',
  mine: '',
});

const ticketForm = reactive({
  title: '',
  description: '',
  category: 'bug',
  priority: 'medium',
});

const commentForm = reactive({
  content: '',
  comment_type: 'comment',
});

const feedbackForm = reactive({
  rating: 5,
  content: '',
});

const pageTitle = computed(() => {
  if (activeView.value === 'tickets') return '工单中心';
  if (activeView.value === 'notifications') return '通知中心';
  return '统计看板';
});

const pageSubtitle = computed(() => {
  if (activeView.value === 'tickets') return '查看、创建和跟进工单。';
  if (activeView.value === 'notifications') return '查看系统提醒和协作动态。';
  return '查看工单数量、状态分布和评价指标。';
});

const statusChart = computed(() => {
  const statusMap = summary.value?.by_status || {};
  const rows = [
    ['open', '待处理'],
    ['in_progress', '处理中'],
    ['resolved', '已解决'],
    ['closed', '已关闭'],
  ].map(([key, label]) => ({ key, label, value: statusMap[key] || 0 }));
  const max = Math.max(...rows.map((item) => item.value), 1);
  return rows.map((item) => ({ ...item, percent: Math.round((item.value / max) * 100) }));
});

const satisfactionText = computed(() => {
  const rate = summary.value?.feedback?.satisfaction_rate || 0;
  return `${Math.round(rate * 100)}%`;
});

function setError(error) {
  errorMessage.value = error?.message || '操作失败，请稍后重试。';
}

async function login() {
  loading.value = true;
  errorMessage.value = '';
  try {
    const data = await authApi.login(loginForm);
    token.value = data.access;
    localStorage.setItem('flowdesk_access', data.access);
    localStorage.setItem('flowdesk_refresh', data.refresh);
    await bootstrap();
  } catch (error) {
    setError(error);
  } finally {
    loading.value = false;
  }
}

function logout() {
  token.value = '';
  currentUser.value = null;
  localStorage.removeItem('flowdesk_access');
  localStorage.removeItem('flowdesk_refresh');
}

async function bootstrap() {
  if (!token.value) return;
  currentUser.value = await authApi.me(token.value);
  await Promise.all([loadSummary(), loadTickets(), loadNotifications()]);
}

async function refreshCurrentView() {
  errorMessage.value = '';
  try {
    if (activeView.value === 'dashboard') await loadSummary();
    if (activeView.value === 'tickets') await loadTickets();
    if (activeView.value === 'notifications') await loadNotifications();
  } catch (error) {
    setError(error);
  }
}

async function loadSummary() {
  summary.value = await dashboardApi.summary(token.value);
}

async function loadTickets() {
  const data = await ticketApi.list(token.value, ticketFilters);
  tickets.value = data.results || [];
  if (!selectedTicket.value && tickets.value.length) {
    await openTicket(tickets.value[0].id);
  }
}

async function openTicket(id) {
  selectedTicket.value = await ticketApi.detail(token.value, id);
  const data = await ticketApi.timeline(token.value, id);
  timeline.value = data.results || [];
  showCloseForm.value = false;
  showFeedbackForm.value = false;
}

async function createTicket() {
  try {
    await ticketApi.create(token.value, ticketForm);
    ticketForm.title = '';
    ticketForm.description = '';
    ticketForm.category = 'bug';
    ticketForm.priority = 'medium';
    showCreateTicket.value = false;
    await loadTickets();
    await loadSummary();
  } catch (error) {
    setError(error);
  }
}

async function addComment() {
  if (!selectedTicket.value) return;
  try {
    await ticketApi.addComment(token.value, selectedTicket.value.id, commentForm);
    commentForm.content = '';
    commentForm.comment_type = 'comment';
    await openTicket(selectedTicket.value.id);
  } catch (error) {
    setError(error);
  }
}

async function closeSelectedTicket() {
  if (!selectedTicket.value) return;
  try {
    await ticketApi.close(token.value, selectedTicket.value.id, closeReason.value);
    closeReason.value = '';
    await openTicket(selectedTicket.value.id);
    await loadSummary();
  } catch (error) {
    setError(error);
  }
}

async function submitFeedback() {
  if (!selectedTicket.value) return;
  try {
    await ticketApi.submitFeedback(token.value, selectedTicket.value.id, feedbackForm);
    feedbackForm.rating = 5;
    feedbackForm.content = '';
    await openTicket(selectedTicket.value.id);
    await loadSummary();
  } catch (error) {
    setError(error);
  }
}

async function loadNotifications() {
  const [list, count] = await Promise.all([
    notificationApi.list(token.value, { ordering: '-created_at' }),
    notificationApi.unreadCount(token.value),
  ]);
  notifications.value = list.results || [];
  unreadCount.value = count.unread_count || 0;
}

async function markAllRead() {
  try {
    await notificationApi.markAllRead(token.value);
    await loadNotifications();
  } catch (error) {
    setError(error);
  }
}

function statusLabel(value) {
  return {
    open: '待处理',
    in_progress: '处理中',
    resolved: '已解决',
    closed: '已关闭',
  }[value] || value;
}

function priorityLabel(value) {
  return {
    low: '低',
    medium: '中',
    high: '高',
    urgent: '紧急',
  }[value] || value;
}

function eventTypeLabel(value) {
  return {
    audit: '审计日志',
    comment: '评论记录',
    attachment: '附件',
    feedback: '评价',
  }[value] || value;
}

function formatDate(value) {
  if (!value) return '';
  return new Intl.DateTimeFormat('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value));
}

onMounted(async () => {
  if (!token.value) return;
  try {
    await bootstrap();
  } catch (error) {
    logout();
    setError(error);
  }
});
</script>
