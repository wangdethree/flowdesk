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
        <button :class="{ active: activeView === 'dashboard' }" @click="switchView('dashboard')">统计看板</button>
        <button :class="{ active: activeView === 'tickets' }" @click="switchView('tickets')">工单中心</button>
        <button :class="{ active: activeView === 'assistant' }" @click="switchView('assistant')">智能助手</button>
        <button :class="{ active: activeView === 'notifications' }" @click="switchView('notifications')">
          通知中心
          <span v-if="unreadCount" class="badge">{{ unreadCount }}</span>
        </button>
        <button :class="{ active: activeView === 'tags' }" @click="switchView('tags')">标签管理</button>
        <button :class="{ active: activeView === 'account' }" @click="switchView('account')">账号设置</button>
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

      <p v-if="successMessage" class="notice success-text">{{ successMessage }}</p>
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

        <article class="panel span-2">
          <div class="panel-header">
            <h3>优先级分布</h3>
          </div>
          <div class="bar-list">
            <div v-for="item in priorityChart" :key="item.key" class="bar-row">
              <span>{{ item.label }}</span>
              <div class="bar-track">
                <div class="bar-fill danger" :style="{ width: item.percent + '%' }"></div>
              </div>
              <b>{{ item.value }}</b>
            </div>
          </div>
        </article>

        <article class="panel span-2">
          <div class="panel-header">
            <h3>分类分布</h3>
          </div>
          <div class="bar-list">
            <div v-for="item in categoryChart" :key="item.key" class="bar-row">
              <span>{{ item.label }}</span>
              <div class="bar-track">
                <div class="bar-fill muted-fill" :style="{ width: item.percent + '%' }"></div>
              </div>
              <b>{{ item.value }}</b>
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

          <form class="filter-row wide-filter" @submit.prevent="applyTicketFilters">
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
            <select v-model="ticketFilters.priority">
              <option value="">全部优先级</option>
              <option value="low">低</option>
              <option value="medium">中</option>
              <option value="high">高</option>
              <option value="urgent">紧急</option>
            </select>
            <select v-model="ticketFilters.category">
              <option value="">全部分类</option>
              <option value="bug">故障问题</option>
              <option value="feature">功能需求</option>
              <option value="consult">咨询支持</option>
              <option value="other">其他</option>
            </select>
            <select v-model="ticketFilters.tag">
              <option value="">全部标签</option>
              <option v-for="tag in tags" :key="tag.id" :value="tag.id">{{ tag.name }}</option>
            </select>
            <select v-model="ticketFilters.overdue">
              <option value="">不限超时</option>
              <option value="true">只看超时</option>
              <option value="false">只看未超时</option>
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
            <label>
              截止时间
              <input v-model="ticketForm.due_at" type="datetime-local" />
            </label>
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
                <small v-for="tag in ticket.tag_names" :key="tag">{{ tag }}</small>
              </span>
            </button>
          </div>
          <div class="pagination-row">
            <span>共 {{ ticketPagination.count }} 条 · 第 {{ ticketFilters.page }} 页</span>
            <div class="button-group">
              <button class="secondary-button small-button" :disabled="!ticketPagination.previous" @click="changeTicketPage(-1)">
                上一页
              </button>
              <button class="secondary-button small-button" :disabled="!ticketPagination.next" @click="changeTicketPage(1)">
                下一页
              </button>
            </div>
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
              <span>分类：{{ categoryLabel(selectedTicket.category) }}</span>
              <span>截止：{{ selectedTicket.due_at ? formatDate(selectedTicket.due_at) : '未设置' }}</span>
              <span>关注人：{{ selectedTicket.watcher_usernames?.join('、') || '暂无' }}</span>
              <span>标签：{{ selectedTicket.tag_names?.join('、') || '暂无' }}</span>
            </div>

            <div class="action-row wrap">
              <button class="secondary-button" @click="toggleWatch">
                {{ isWatching ? '取消关注' : '关注工单' }}
              </button>
              <button class="secondary-button" @click="loadTicketAssistantSuggestion">智能建议</button>
              <button class="secondary-button" @click="showEditForm = !showEditForm">编辑工单</button>
              <button
                v-for="action in statusActions"
                :key="action.status"
                class="secondary-button"
                @click="advanceTicketStatus(action.status)"
              >
                {{ action.label }}
              </button>
              <button class="secondary-button" @click="showAssignForm = !showAssignForm">分配处理人</button>
              <button class="secondary-button" @click="showPriorityForm = !showPriorityForm">调整优先级</button>
              <button class="secondary-button" @click="showTagForm = !showTagForm">设置标签</button>
              <button class="secondary-button" @click="showReminderForm = !showReminderForm">催办</button>
              <button v-if="selectedTicket.status !== 'closed'" class="secondary-button" @click="showCloseForm = !showCloseForm">
                关闭工单
              </button>
              <button v-if="selectedTicket.status === 'closed'" class="secondary-button" @click="showReopenForm = !showReopenForm">
                重开工单
              </button>
              <button v-if="selectedTicket.status === 'closed'" class="secondary-button" @click="showFeedbackForm = !showFeedbackForm">
                评价工单
              </button>
            </div>

            <section v-if="ticketAssistantSuggestion" class="assistant-panel">
              <div class="panel-header">
                <h4>智能处理建议</h4>
                <small>可信度：{{ Math.round(ticketAssistantSuggestion.confidence * 100) }}%</small>
              </div>
              <p>{{ ticketAssistantSuggestion.summary }}</p>
              <div class="suggestion-list">
                <span v-for="action in ticketAssistantSuggestion.next_actions" :key="action">{{ action }}</span>
              </div>
              <textarea :value="ticketAssistantSuggestion.reply_template" readonly></textarea>
              <div v-if="ticketAssistantSuggestion.recent_comments.length" class="mini-list">
                <small v-for="comment in ticketAssistantSuggestion.recent_comments" :key="comment">{{ comment }}</small>
              </div>
            </section>

            <form v-if="showEditForm" class="inline-form" @submit.prevent="updateSelectedTicket">
              <input v-model.trim="editTicketForm.title" placeholder="工单标题" required />
              <textarea v-model.trim="editTicketForm.description" placeholder="问题描述" required></textarea>
              <div class="form-grid">
                <select v-model="editTicketForm.category">
                  <option value="bug">故障问题</option>
                  <option value="feature">功能需求</option>
                  <option value="consult">咨询支持</option>
                  <option value="other">其他</option>
                </select>
                <input v-model="editTicketForm.due_at" type="datetime-local" />
              </div>
              <button class="primary-button" type="submit">保存工单</button>
            </form>

            <form v-if="showAssignForm" class="inline-form compact-form" @submit.prevent="assignSelectedTicket">
              <label>
                处理人用户 ID
                <input v-model.number="assignForm.assignee" min="1" placeholder="例如 2" type="number" />
              </label>
              <button class="primary-button" type="submit">保存分配</button>
              <button class="secondary-button" type="button" @click="clearAssignee">取消分配</button>
            </form>

            <form v-if="showPriorityForm" class="inline-form compact-form" @submit.prevent="setSelectedPriority">
              <label>
                新优先级
                <select v-model="priorityForm.priority">
                  <option value="low">低</option>
                  <option value="medium">中</option>
                  <option value="high">高</option>
                  <option value="urgent">紧急</option>
                </select>
              </label>
              <button class="primary-button" type="submit">保存优先级</button>
            </form>

            <form v-if="showTagForm" class="inline-form" @submit.prevent="setSelectedTags">
              <div class="checkbox-grid">
                <label v-for="tag in tags" :key="tag.id" class="check-option">
                  <input v-model="tagForm.ids" type="checkbox" :value="tag.id" />
                  <span class="tag-swatch" :style="{ backgroundColor: tag.color }"></span>
                  {{ tag.name }}
                </label>
              </div>
              <p v-if="!tags.length" class="muted">暂无标签，可以先到标签管理里创建。</p>
              <button class="primary-button" type="submit">保存标签</button>
            </form>

            <form v-if="showReminderForm" class="inline-form" @submit.prevent="remindSelectedTicket">
              <textarea v-model.trim="reminderForm.message" placeholder="催办说明，可不填"></textarea>
              <button class="primary-button" type="submit">发送催办</button>
            </form>

            <form v-if="showCloseForm" class="inline-form" @submit.prevent="closeSelectedTicket">
              <textarea v-model.trim="closeReason" placeholder="填写关闭原因" required></textarea>
              <button class="primary-button" type="submit">确认关闭</button>
            </form>

            <form v-if="showReopenForm" class="inline-form" @submit.prevent="reopenSelectedTicket">
              <textarea v-model.trim="reopenReason" placeholder="填写重开原因" required></textarea>
              <button class="primary-button" type="submit">确认重开</button>
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

            <section class="subsection">
              <div class="panel-header">
                <h4>附件</h4>
                <label class="file-button">
                  上传附件
                  <input type="file" @change="uploadAttachment" />
                </label>
              </div>
              <div v-if="attachments.length" class="attachment-list">
                <a v-for="file in attachments" :key="file.id" :href="file.file" target="_blank" rel="noreferrer">
                  {{ file.original_filename }}
                  <small>{{ formatFileSize(file.size) }} · {{ file.uploaded_by_username }}</small>
                </a>
              </div>
              <p v-else class="muted">暂无附件。</p>
            </section>

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

            <section class="subsection">
              <div class="panel-header">
                <h4>审计日志</h4>
                <div class="button-group">
                  <button class="secondary-button small-button" :disabled="!auditPagination.previous" @click="changeAuditPage(-1)">
                    上一页
                  </button>
                  <button class="secondary-button small-button" :disabled="!auditPagination.next" @click="changeAuditPage(1)">
                    下一页
                  </button>
                </div>
              </div>
              <div class="audit-list">
                <article v-for="log in auditLogs" :key="log.id" class="audit-item">
                  <strong>{{ log.action_display }}</strong>
                  <p>{{ log.description }}</p>
                  <small>{{ log.actor_username || '系统' }} · {{ formatDate(log.created_at) }}</small>
                </article>
              </div>
              <p v-if="!auditLogs.length" class="muted">暂无审计日志。</p>
            </section>
          </template>
          <div v-else class="empty-state">选择一张工单查看详情。</div>
        </section>
      </section>

      <section v-if="activeView === 'assistant'" class="assistant-grid">
        <form class="panel account-form" @submit.prevent="generateTicketDraft">
          <div class="panel-header">
            <h3>生成工单草稿</h3>
          </div>
          <textarea
            v-model.trim="assistantDraftForm.raw_text"
            placeholder="例如：线上支付全部失败，客户无法完成订单，已经影响多个用户。"
            required
          ></textarea>
          <button class="primary-button" type="submit">生成建议</button>
        </form>

        <section class="panel">
          <div class="panel-header">
            <h3>草稿建议</h3>
            <small v-if="assistantDraftSuggestion">
              可信度：{{ Math.round(assistantDraftSuggestion.confidence * 100) }}%
            </small>
          </div>
          <template v-if="assistantDraftSuggestion">
            <div class="draft-preview">
              <label>
                标题
                <input :value="assistantDraftSuggestion.title" readonly />
              </label>
              <div class="form-grid">
                <label>
                  分类
                  <input :value="categoryLabel(assistantDraftSuggestion.category)" readonly />
                </label>
                <label>
                  优先级
                  <input :value="priorityLabel(assistantDraftSuggestion.priority)" readonly />
                </label>
              </div>
              <label>
                描述
                <textarea :value="assistantDraftSuggestion.description" readonly></textarea>
              </label>
              <div class="suggestion-list">
                <span v-for="tag in assistantDraftSuggestion.suggested_tags" :key="tag">{{ tag }}</span>
              </div>
              <div class="mini-list">
                <small v-for="item in assistantDraftSuggestion.checklist" :key="item">{{ item }}</small>
              </div>
              <button class="primary-button" @click="applyDraftSuggestion" type="button">应用到新建工单</button>
            </div>
          </template>
          <div v-else class="empty-state compact-empty">输入问题描述后生成草稿建议。</div>
        </section>
      </section>

      <section v-if="activeView === 'notifications'" class="panel">
        <div class="panel-header">
          <h3>通知中心</h3>
          <div class="button-group">
            <button class="secondary-button" @click="markAllRead">全部已读</button>
            <button class="secondary-button" @click="clearReadNotifications">清理已读</button>
          </div>
        </div>
        <form class="filter-row notification-filter" @submit.prevent="applyNotificationFilters">
          <input v-model.trim="notificationFilters.search" placeholder="搜索通知标题或内容" />
          <select v-model="notificationFilters.is_read">
            <option value="">全部状态</option>
            <option value="false">未读</option>
            <option value="true">已读</option>
          </select>
          <select v-model="notificationFilters.notification_type">
            <option value="">全部类型</option>
            <option value="ticket_assigned">工单分配</option>
            <option value="ticket_commented">工单评论</option>
            <option value="ticket_status_changed">状态变更</option>
            <option value="ticket_reminded">工单催办</option>
            <option value="ticket_priority_changed">优先级变更</option>
            <option value="ticket_feedback_submitted">工单评价</option>
          </select>
          <button class="secondary-button" type="submit">筛选</button>
        </form>
        <div class="notification-list">
          <article v-for="item in notifications" :key="item.id" class="notification-item" :class="{ unread: !item.is_read }">
            <div>
              <strong>{{ item.title }}</strong>
              <p>{{ item.message }}</p>
              <small>{{ notificationTypeLabel(item.notification_type) }}</small>
            </div>
            <div class="notification-side">
              <small>{{ formatDate(item.created_at) }}</small>
              <button v-if="!item.is_read" class="secondary-button small-button" @click="markNotificationRead(item.id)">已读</button>
            </div>
          </article>
        </div>
        <div class="pagination-row">
          <span>共 {{ notificationPagination.count }} 条 · 第 {{ notificationFilters.page }} 页</span>
          <div class="button-group">
            <button class="secondary-button small-button" :disabled="!notificationPagination.previous" @click="changeNotificationPage(-1)">
              上一页
            </button>
            <button class="secondary-button small-button" :disabled="!notificationPagination.next" @click="changeNotificationPage(1)">
              下一页
            </button>
          </div>
        </div>
      </section>

      <section v-if="activeView === 'tags'" class="tags-layout">
        <form class="panel account-form" @submit.prevent="createTag">
          <div class="panel-header">
            <h3>新建标签</h3>
          </div>
          <label>
            标签名称
            <input v-model.trim="tagCreateForm.name" maxlength="40" placeholder="例如 线上故障" required />
          </label>
          <label>
            标签颜色
            <input v-model="tagCreateForm.color" type="color" />
          </label>
          <button class="primary-button" type="submit">创建标签</button>
        </form>

        <section class="panel">
          <div class="panel-header">
            <h3>标签列表</h3>
            <button class="secondary-button" @click="loadTags">刷新</button>
          </div>
          <div class="tag-list">
            <article v-for="tag in tags" :key="tag.id" class="tag-card">
              <span class="tag-swatch large" :style="{ backgroundColor: tag.color }"></span>
              <div>
                <strong>{{ tag.name }}</strong>
                <small>ID：{{ tag.id }} · {{ formatDate(tag.created_at) }}</small>
              </div>
            </article>
          </div>
        </section>
      </section>

      <section v-if="activeView === 'account'" class="account-grid">
        <form class="panel account-form" @submit.prevent="updateProfile">
          <div class="panel-header">
            <h3>个人资料</h3>
          </div>
          <label>
            用户名
            <input :value="currentUser?.username" disabled />
          </label>
          <label>
            邮箱
            <input v-model.trim="profileForm.email" autocomplete="email" placeholder="你的邮箱" type="email" />
          </label>
          <div class="form-grid">
            <label>
              名
              <input v-model.trim="profileForm.first_name" autocomplete="given-name" />
            </label>
            <label>
              姓
              <input v-model.trim="profileForm.last_name" autocomplete="family-name" />
            </label>
          </div>
          <button class="primary-button" type="submit">保存资料</button>
        </form>

        <form class="panel account-form" @submit.prevent="changePassword">
          <div class="panel-header">
            <h3>修改密码</h3>
          </div>
          <label>
            旧密码
            <input v-model="passwordForm.old_password" autocomplete="current-password" required type="password" />
          </label>
          <label>
            新密码
            <input v-model="passwordForm.new_password" autocomplete="new-password" required type="password" />
          </label>
          <label>
            确认新密码
            <input v-model="passwordForm.new_password_confirm" autocomplete="new-password" required type="password" />
          </label>
          <button class="primary-button" type="submit">修改密码</button>
        </form>
      </section>
    </section>
  </main>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue';
import { assistantApi, authApi, dashboardApi, notificationApi, tagApi, ticketApi } from './api';

const token = ref(localStorage.getItem('flowdesk_access') || '');
const currentUser = ref(null);
const activeView = ref('dashboard');
const loading = ref(false);
const errorMessage = ref('');
const successMessage = ref('');

const summary = ref(null);
const tickets = ref([]);
const selectedTicket = ref(null);
const timeline = ref([]);
const auditLogs = ref([]);
const attachments = ref([]);
const notifications = ref([]);
const tags = ref([]);
const assistantDraftSuggestion = ref(null);
const ticketAssistantSuggestion = ref(null);
const unreadCount = ref(0);

const showCreateTicket = ref(false);
const showEditForm = ref(false);
const showAssignForm = ref(false);
const showPriorityForm = ref(false);
const showTagForm = ref(false);
const showReminderForm = ref(false);
const showCloseForm = ref(false);
const showReopenForm = ref(false);
const showFeedbackForm = ref(false);
const closeReason = ref('');
const reopenReason = ref('');

const loginForm = reactive({
  username: '',
  password: '',
});

const profileForm = reactive({
  email: '',
  first_name: '',
  last_name: '',
});

const passwordForm = reactive({
  old_password: '',
  new_password: '',
  new_password_confirm: '',
});

const ticketFilters = reactive({
  search: '',
  status: '',
  mine: '',
  priority: '',
  category: '',
  tag: '',
  overdue: '',
  page: 1,
});

const ticketPagination = reactive({
  count: 0,
  next: null,
  previous: null,
});

const auditPagination = reactive({
  page: 1,
  count: 0,
  next: null,
  previous: null,
});

const assistantDraftForm = reactive({
  raw_text: '',
});

const notificationFilters = reactive({
  search: '',
  is_read: '',
  notification_type: '',
  page: 1,
});

const notificationPagination = reactive({
  count: 0,
  next: null,
  previous: null,
});

const ticketForm = reactive({
  title: '',
  description: '',
  category: 'bug',
  priority: 'medium',
  due_at: '',
});

const editTicketForm = reactive({
  title: '',
  description: '',
  category: 'bug',
  due_at: '',
});

const assignForm = reactive({
  assignee: '',
});

const priorityForm = reactive({
  priority: 'medium',
});

const tagForm = reactive({
  ids: [],
});

const tagCreateForm = reactive({
  name: '',
  color: '#64748b',
});

const reminderForm = reactive({
  message: '',
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
  if (activeView.value === 'assistant') return '智能助手';
  if (activeView.value === 'notifications') return '通知中心';
  if (activeView.value === 'tags') return '标签管理';
  if (activeView.value === 'account') return '账号设置';
  return '统计看板';
});

const pageSubtitle = computed(() => {
  if (activeView.value === 'tickets') return '查看、创建和跟进工单。';
  if (activeView.value === 'assistant') return '用规则引擎生成工单草稿和处理建议，后续可替换成大模型。';
  if (activeView.value === 'notifications') return '查看系统提醒和协作动态。';
  if (activeView.value === 'tags') return '维护工单标签，方便筛选和归类。';
  if (activeView.value === 'account') return '维护个人资料和账号密码。';
  return '查看工单数量、状态分布和评价指标。';
});

function buildChartRows(source, rows) {
  const values = source || {};
  const normalizedRows = rows.map(([key, label]) => ({ key, label, value: values[key] || 0 }));
  const max = Math.max(...normalizedRows.map((item) => item.value), 1);
  return normalizedRows.map((item) => ({ ...item, percent: Math.round((item.value / max) * 100) }));
}

const statusChart = computed(() => {
  return buildChartRows(summary.value?.by_status, [
    ['open', '待处理'],
    ['in_progress', '处理中'],
    ['resolved', '已解决'],
    ['closed', '已关闭'],
  ]);
});

const priorityChart = computed(() => {
  return buildChartRows(summary.value?.by_priority, [
    ['low', '低'],
    ['medium', '中'],
    ['high', '高'],
    ['urgent', '紧急'],
  ]);
});

const categoryChart = computed(() => {
  return buildChartRows(summary.value?.by_category, [
    ['bug', '故障问题'],
    ['feature', '功能需求'],
    ['consult', '咨询支持'],
    ['other', '其他'],
  ]);
});

const satisfactionText = computed(() => {
  const rate = summary.value?.feedback?.satisfaction_rate || 0;
  return `${Math.round(rate * 100)}%`;
});

const isWatching = computed(() => {
  const names = selectedTicket.value?.watcher_usernames || [];
  return names.includes(currentUser.value?.username);
});

const statusActions = computed(() => {
  // 关闭工单需要填写原因，所以不在这里直接 PATCH 成 closed，而是继续走关闭表单。
  const status = selectedTicket.value?.status;
  if (status === 'open') return [{ status: 'in_progress', label: '开始处理' }];
  if (status === 'in_progress') return [{ status: 'resolved', label: '标记解决' }];
  return [];
});

function resetMessages() {
  errorMessage.value = '';
  successMessage.value = '';
}

function setError(error) {
  successMessage.value = '';
  errorMessage.value = error?.message || '操作失败，请稍后重试。';
}

function setSuccess(message) {
  errorMessage.value = '';
  successMessage.value = message;
}

function syncProfileForm() {
  // 后端的 me 接口是账号资料唯一可信来源，进入账号页或刷新后都用它回填表单。
  profileForm.email = currentUser.value?.email || '';
  profileForm.first_name = currentUser.value?.first_name || '';
  profileForm.last_name = currentUser.value?.last_name || '';
}

function resetTicketForms() {
  // 切换工单时收起所有动作表单，避免把上一张工单的操作误提交到下一张工单。
  showEditForm.value = false;
  showAssignForm.value = false;
  showPriorityForm.value = false;
  showTagForm.value = false;
  showReminderForm.value = false;
  showCloseForm.value = false;
  showReopenForm.value = false;
  showFeedbackForm.value = false;
  closeReason.value = '';
  reopenReason.value = '';
  reminderForm.message = '';
}

function fillTicketActionForms(ticket) {
  assignForm.assignee = ticket.assignee || '';
  priorityForm.priority = ticket.priority || 'medium';
  tagForm.ids = [...(ticket.tags || [])];
  editTicketForm.title = ticket.title || '';
  editTicketForm.description = ticket.description || '';
  editTicketForm.category = ticket.category || 'other';
  editTicketForm.due_at = toDateTimeLocal(ticket.due_at);
}

function buildTicketPayload(form) {
  // datetime-local 没有时区信息，提交前统一转成 ISO 字符串，让后端 DateTimeField 稳定解析。
  return {
    title: form.title,
    description: form.description,
    category: form.category,
    priority: form.priority,
    due_at: form.due_at ? new Date(form.due_at).toISOString() : null,
  };
}

function toDateTimeLocal(value) {
  if (!value) return '';
  const date = new Date(value);
  const offset = date.getTimezoneOffset();
  const localDate = new Date(date.getTime() - offset * 60 * 1000);
  return localDate.toISOString().slice(0, 16);
}

async function login() {
  loading.value = true;
  resetMessages();
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
  selectedTicket.value = null;
  localStorage.removeItem('flowdesk_access');
  localStorage.removeItem('flowdesk_refresh');
}

function switchView(view) {
  activeView.value = view;
  resetMessages();
  if (view === 'account') {
    syncProfileForm();
  }
}

async function bootstrap() {
  if (!token.value) return;
  currentUser.value = await authApi.me(token.value);
  syncProfileForm();
  await Promise.all([loadSummary(), loadTags(), loadTickets(), loadNotifications()]);
}

async function refreshCurrentView() {
  resetMessages();
  try {
    if (activeView.value === 'dashboard') await loadSummary();
    if (activeView.value === 'tickets') await loadTickets();
    if (activeView.value === 'notifications') await loadNotifications();
    if (activeView.value === 'tags') await loadTags();
    if (activeView.value === 'account') {
      currentUser.value = await authApi.me(token.value);
      syncProfileForm();
    }
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
  ticketPagination.count = data.count || 0;
  ticketPagination.next = data.next;
  ticketPagination.previous = data.previous;

  // 重新筛选后，当前详情可能已经不在左侧列表里。
  // 这时主动切到第一条结果，避免出现“列表是 A 条件，详情还是旧工单”的错位感。
  const selectedStillVisible = tickets.value.some((ticket) => ticket.id === selectedTicket.value?.id);
  if (selectedTicket.value && !selectedStillVisible) {
    selectedTicket.value = null;
    timeline.value = [];
    auditLogs.value = [];
    attachments.value = [];
  }

  if (!selectedTicket.value && tickets.value.length) {
    await openTicket(tickets.value[0].id);
  }
}

async function applyTicketFilters() {
  // 条件变化后回到第一页，避免用户在第 3 页筛选时误以为没有数据。
  ticketFilters.page = 1;
  await loadTickets();
}

async function changeTicketPage(offset) {
  const nextPage = ticketFilters.page + offset;
  if (nextPage < 1) return;
  ticketFilters.page = nextPage;
  await loadTickets();
}

async function loadTags() {
  const data = await tagApi.list(token.value, { ordering: 'name' });
  tags.value = data.results || [];
}

async function openTicket(id) {
  resetMessages();
  ticketAssistantSuggestion.value = null;
  selectedTicket.value = await ticketApi.detail(token.value, id);
  auditPagination.page = 1;
  const [timelineData, attachmentData, auditData] = await Promise.all([
    ticketApi.timeline(token.value, id),
    ticketApi.attachments(token.value, id),
    ticketApi.auditLogs(token.value, id, { page: auditPagination.page }),
  ]);
  timeline.value = timelineData.results || [];
  attachments.value = attachmentData.results || [];
  setAuditData(auditData);
  resetTicketForms();
  fillTicketActionForms(selectedTicket.value);
}

function setAuditData(data) {
  auditLogs.value = data.results || [];
  auditPagination.count = data.count || 0;
  auditPagination.next = data.next;
  auditPagination.previous = data.previous;
}

async function loadAuditLogs() {
  if (!selectedTicket.value) return;
  const data = await ticketApi.auditLogs(token.value, selectedTicket.value.id, {
    page: auditPagination.page,
  });
  setAuditData(data);
}

async function changeAuditPage(offset) {
  const nextPage = auditPagination.page + offset;
  if (nextPage < 1) return;
  auditPagination.page = nextPage;
  await loadAuditLogs();
}

async function generateTicketDraft() {
  try {
    assistantDraftSuggestion.value = await assistantApi.draftTicket(
      token.value,
      assistantDraftForm.raw_text,
    );
    setSuccess('草稿建议已生成。');
  } catch (error) {
    setError(error);
  }
}

function applyDraftSuggestion() {
  if (!assistantDraftSuggestion.value) return;

  // 这里只把 AI 建议填进新建工单表单，不直接创建工单。
  // 这样用户还有机会人工确认标题、描述和优先级，避免自动化建议误写入业务数据。
  ticketForm.title = assistantDraftSuggestion.value.title;
  ticketForm.description = assistantDraftSuggestion.value.description;
  ticketForm.category = assistantDraftSuggestion.value.category;
  ticketForm.priority = assistantDraftSuggestion.value.priority;
  showCreateTicket.value = true;
  switchView('tickets');
  setSuccess('已填入新建工单表单，请确认后提交。');
}

async function loadTicketAssistantSuggestion() {
  if (!selectedTicket.value) return;
  try {
    ticketAssistantSuggestion.value = await assistantApi.ticketSuggestion(
      token.value,
      selectedTicket.value.id,
    );
    setSuccess('智能建议已生成。');
  } catch (error) {
    setError(error);
  }
}

async function createTicket() {
  try {
    await ticketApi.create(token.value, buildTicketPayload(ticketForm));
    ticketForm.title = '';
    ticketForm.description = '';
    ticketForm.category = 'bug';
    ticketForm.priority = 'medium';
    ticketForm.due_at = '';
    showCreateTicket.value = false;
    await loadTickets();
    await loadSummary();
    setSuccess('工单创建成功。');
  } catch (error) {
    setError(error);
  }
}

async function updateSelectedTicket() {
  if (!selectedTicket.value) return;
  try {
    await ticketApi.update(token.value, selectedTicket.value.id, buildTicketPayload({
      ...editTicketForm,
      priority: selectedTicket.value.priority,
    }));
    showEditForm.value = false;
    await refreshSelectedTicket('工单信息已更新。');
  } catch (error) {
    setError(error);
  }
}

async function advanceTicketStatus(status) {
  if (!selectedTicket.value) return;
  try {
    await ticketApi.update(token.value, selectedTicket.value.id, { status });
    await refreshSelectedTicket('工单状态已更新。');
  } catch (error) {
    setError(error);
  }
}

async function refreshSelectedTicket(message = '') {
  if (!selectedTicket.value) return;
  const id = selectedTicket.value.id;
  selectedTicket.value = await ticketApi.detail(token.value, id);
  const [timelineData, attachmentData, auditData] = await Promise.all([
    ticketApi.timeline(token.value, id),
    ticketApi.attachments(token.value, id),
    ticketApi.auditLogs(token.value, id, { page: auditPagination.page }),
  ]);
  timeline.value = timelineData.results || [];
  attachments.value = attachmentData.results || [];
  setAuditData(auditData);
  fillTicketActionForms(selectedTicket.value);
  await loadTickets();
  await loadSummary();
  if (message) setSuccess(message);
}

async function addComment() {
  if (!selectedTicket.value) return;
  try {
    await ticketApi.addComment(token.value, selectedTicket.value.id, commentForm);
    commentForm.content = '';
    commentForm.comment_type = 'comment';
    await refreshSelectedTicket('记录添加成功。');
  } catch (error) {
    setError(error);
  }
}

async function assignSelectedTicket() {
  if (!selectedTicket.value) return;
  try {
    const assignee = assignForm.assignee ? Number(assignForm.assignee) : null;
    await ticketApi.assign(token.value, selectedTicket.value.id, assignee);
    showAssignForm.value = false;
    await refreshSelectedTicket('处理人已更新。');
  } catch (error) {
    setError(error);
  }
}

async function clearAssignee() {
  assignForm.assignee = '';
  await assignSelectedTicket();
}

async function setSelectedPriority() {
  if (!selectedTicket.value) return;
  try {
    await ticketApi.setPriority(token.value, selectedTicket.value.id, priorityForm.priority);
    showPriorityForm.value = false;
    await refreshSelectedTicket('优先级已更新。');
  } catch (error) {
    setError(error);
  }
}

async function setSelectedTags() {
  if (!selectedTicket.value) return;
  try {
    await ticketApi.setTags(token.value, selectedTicket.value.id, tagForm.ids.map(Number));
    showTagForm.value = false;
    await refreshSelectedTicket('标签已更新。');
  } catch (error) {
    setError(error);
  }
}

async function createTag() {
  try {
    await tagApi.create(token.value, tagCreateForm);
    tagCreateForm.name = '';
    tagCreateForm.color = '#64748b';
    await loadTags();
    setSuccess('标签创建成功。');
  } catch (error) {
    setError(error);
  }
}

async function remindSelectedTicket() {
  if (!selectedTicket.value) return;
  try {
    await ticketApi.remind(token.value, selectedTicket.value.id, reminderForm.message);
    reminderForm.message = '';
    showReminderForm.value = false;
    await refreshSelectedTicket('催办已发送。');
  } catch (error) {
    setError(error);
  }
}

async function toggleWatch() {
  if (!selectedTicket.value) return;
  try {
    if (isWatching.value) {
      await ticketApi.unwatch(token.value, selectedTicket.value.id);
      await refreshSelectedTicket('已取消关注。');
    } else {
      await ticketApi.watch(token.value, selectedTicket.value.id);
      await refreshSelectedTicket('已关注工单。');
    }
  } catch (error) {
    setError(error);
  }
}

async function closeSelectedTicket() {
  if (!selectedTicket.value) return;
  try {
    await ticketApi.close(token.value, selectedTicket.value.id, closeReason.value);
    closeReason.value = '';
    await refreshSelectedTicket('工单已关闭。');
  } catch (error) {
    setError(error);
  }
}

async function reopenSelectedTicket() {
  if (!selectedTicket.value) return;
  try {
    await ticketApi.reopen(token.value, selectedTicket.value.id, reopenReason.value);
    reopenReason.value = '';
    await refreshSelectedTicket('工单已重开。');
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
    await refreshSelectedTicket('评价提交成功。');
  } catch (error) {
    setError(error);
  }
}

async function uploadAttachment(event) {
  if (!selectedTicket.value) return;
  const [file] = event.target.files || [];
  if (!file) return;
  try {
    await ticketApi.uploadAttachment(token.value, selectedTicket.value.id, file);
    event.target.value = '';
    await refreshSelectedTicket('附件上传成功。');
  } catch (error) {
    setError(error);
  }
}

async function loadNotifications() {
  const [list, count] = await Promise.all([
    notificationApi.list(token.value, { ...notificationFilters, ordering: '-created_at' }),
    notificationApi.unreadCount(token.value),
  ]);
  notifications.value = list.results || [];
  notificationPagination.count = list.count || 0;
  notificationPagination.next = list.next;
  notificationPagination.previous = list.previous;
  unreadCount.value = count.unread_count || 0;
}

async function applyNotificationFilters() {
  // 通知筛选和工单筛选一样，条件变化后回到第一页。
  notificationFilters.page = 1;
  await loadNotifications();
}

async function changeNotificationPage(offset) {
  const nextPage = notificationFilters.page + offset;
  if (nextPage < 1) return;
  notificationFilters.page = nextPage;
  await loadNotifications();
}

async function markAllRead() {
  try {
    await notificationApi.markAllRead(token.value);
    await loadNotifications();
    setSuccess('全部通知已标记为已读。');
  } catch (error) {
    setError(error);
  }
}

async function markNotificationRead(id) {
  try {
    await notificationApi.markRead(token.value, id);
    await loadNotifications();
  } catch (error) {
    setError(error);
  }
}

async function clearReadNotifications() {
  try {
    await notificationApi.clearRead(token.value);
    await loadNotifications();
    setSuccess('已读通知已清理。');
  } catch (error) {
    setError(error);
  }
}

async function updateProfile() {
  try {
    currentUser.value = await authApi.updateMe(token.value, profileForm);
    syncProfileForm();
    setSuccess('个人资料已保存。');
  } catch (error) {
    setError(error);
  }
}

async function changePassword() {
  try {
    await authApi.changePassword(token.value, passwordForm);
    passwordForm.old_password = '';
    passwordForm.new_password = '';
    passwordForm.new_password_confirm = '';
    setSuccess('密码修改成功。');
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

function categoryLabel(value) {
  return {
    bug: '故障问题',
    feature: '功能需求',
    consult: '咨询支持',
    other: '其他',
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

function notificationTypeLabel(value) {
  return {
    ticket_assigned: '工单分配',
    ticket_commented: '工单评论',
    ticket_status_changed: '状态变更',
    ticket_reminded: '工单催办',
    ticket_priority_changed: '优先级变更',
    ticket_feedback_submitted: '工单评价',
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

function formatFileSize(size) {
  if (!size) return '0 KB';
  if (size < 1024 * 1024) return `${Math.ceil(size / 1024)} KB`;
  return `${(size / 1024 / 1024).toFixed(1)} MB`;
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
