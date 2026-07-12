from __future__ import annotations

from dataclasses import dataclass

from django.utils import timezone

from apps.tickets.models import Ticket, TicketCategory, TicketPriority, TicketStatus


@dataclass(frozen=True)
class KeywordRule:
    """智能助手的关键词规则。

    当前版本先用可离线运行的规则引擎，方便本地演示和自动化测试。
    后续接入大模型时，可以保留这里的输入输出结构，只把内部实现替换成 LLM 调用。
    """

    keywords: tuple[str, ...]
    category: str | None = None
    priority: str | None = None
    tag: str | None = None


KEYWORD_RULES = (
    KeywordRule(
        keywords=('线上', '宕机', '生产', '全部用户', '大面积'),
        category=TicketCategory.BUG,
        priority=TicketPriority.URGENT,
        tag='线上故障',
    ),
    KeywordRule(
        keywords=('支付', '订单', '退款', '账单'),
        category=TicketCategory.BUG,
        priority=TicketPriority.HIGH,
        tag='支付模块',
    ),
    KeywordRule(
        keywords=('登录', '权限', '验证码', '认证'),
        category=TicketCategory.BUG,
        priority=TicketPriority.HIGH,
        tag='账号权限',
    ),
    KeywordRule(
        keywords=('慢', '卡顿', '超时', '性能'),
        category=TicketCategory.BUG,
        priority=TicketPriority.MEDIUM,
        tag='性能问题',
    ),
    KeywordRule(
        keywords=('希望', '新增', '支持', '优化', '需求'),
        category=TicketCategory.FEATURE,
        priority=TicketPriority.MEDIUM,
        tag='功能需求',
    ),
    KeywordRule(
        keywords=('如何', '怎么', '咨询', '说明', '文档'),
        category=TicketCategory.CONSULT,
        priority=TicketPriority.LOW,
        tag='咨询支持',
    ),
)


CATEGORY_CHECKLIST = {
    TicketCategory.BUG: [
        '确认影响范围：单个用户、部分用户还是全部用户。',
        '收集复现步骤、截图、报错信息和发生时间。',
        '排查最近发布、配置变更或第三方服务异常。',
    ],
    TicketCategory.FEATURE: [
        '确认需求目标、使用场景和验收标准。',
        '评估是否已有相近功能可以复用。',
        '拆分最小可交付范围，避免第一版需求过大。',
    ],
    TicketCategory.CONSULT: [
        '确认用户真正想完成的业务动作。',
        '给出操作路径、注意事项和可参考文档。',
        '如果咨询暴露产品缺口，转成需求工单继续跟进。',
    ],
    TicketCategory.OTHER: [
        '补充更多上下文，先判断问题属于故障、需求还是咨询。',
        '确认联系人、期望完成时间和业务影响。',
        '必要时分配给一线支持先做信息收集。',
    ],
}


def normalize_text(value: str) -> str:
    """整理用户输入文本，避免规则匹配被多余空格影响。"""

    return ' '.join((value or '').strip().split())


def find_matched_rules(text: str) -> list[KeywordRule]:
    """根据输入文本命中关键词规则。"""

    normalized_text = text.lower()
    return [
        rule
        for rule in KEYWORD_RULES
        if any(keyword.lower() in normalized_text for keyword in rule.keywords)
    ]


def choose_category(matched_rules: list[KeywordRule]) -> str:
    """根据规则推断工单分类。

    分类比优先级更偏业务语义，所以取第一条命中规则的分类即可。
    规则顺序从更严重、更明确的场景排到更宽泛的场景。
    """

    for rule in matched_rules:
        if rule.category:
            return rule.category
    return TicketCategory.OTHER


def choose_priority(matched_rules: list[KeywordRule], category: str) -> str:
    """根据规则推断优先级。"""

    priority_order = {
        TicketPriority.LOW: 1,
        TicketPriority.MEDIUM: 2,
        TicketPriority.HIGH: 3,
        TicketPriority.URGENT: 4,
    }
    priorities = [rule.priority for rule in matched_rules if rule.priority]
    if priorities:
        return max(priorities, key=lambda priority: priority_order[priority])
    if category == TicketCategory.CONSULT:
        return TicketPriority.LOW
    return TicketPriority.MEDIUM


def build_title(raw_text: str) -> str:
    """从用户原始描述里生成一个短标题。"""

    text = normalize_text(raw_text)
    if not text:
        return '待补充工单标题'

    # 先取第一句，避免把完整长描述塞进标题。
    first_sentence = text.replace('。', '\n').replace('！', '\n').replace('？', '\n').split('\n')[0]
    return first_sentence[:36] if len(first_sentence) > 36 else first_sentence


def build_suggested_tags(category: str, matched_rules: list[KeywordRule]) -> list[str]:
    """生成建议标签名称。

    返回标签名称而不是标签 ID，是为了让前端可以先展示建议；
    真正绑定标签时仍然走已有的标签管理和 set-tags 接口。
    """

    tags = [rule.tag for rule in matched_rules if rule.tag]
    if category == TicketCategory.BUG:
        tags.append('故障问题')
    elif category == TicketCategory.FEATURE:
        tags.append('功能需求')
    elif category == TicketCategory.CONSULT:
        tags.append('咨询支持')

    # dict.fromkeys 可以在保持顺序的同时去重。
    return list(dict.fromkeys(tag for tag in tags if tag))


def build_confidence(matched_rules: list[KeywordRule]) -> float:
    """给出一个简单可信度，用于提示用户建议是否可靠。"""

    if not matched_rules:
        return 0.45
    return min(0.95, 0.55 + len(matched_rules) * 0.12)


def build_ticket_draft(raw_text: str) -> dict:
    """根据一段自然语言描述生成工单草稿建议。"""

    text = normalize_text(raw_text)
    matched_rules = find_matched_rules(text)
    category = choose_category(matched_rules)
    priority = choose_priority(matched_rules, category)

    return {
        'title': build_title(text),
        'description': text,
        'category': category,
        'priority': priority,
        'suggested_tags': build_suggested_tags(category, matched_rules),
        'checklist': CATEGORY_CHECKLIST[category],
        'confidence': build_confidence(matched_rules),
    }


def build_ticket_summary(ticket: Ticket) -> str:
    """生成已有工单摘要。"""

    status_text = ticket.get_status_display()
    priority_text = ticket.get_priority_display()
    category_text = ticket.get_category_display()
    assignee = ticket.assignee.username if ticket.assignee else '未分配'
    return f'#{ticket.id} {ticket.title}，当前状态：{status_text}，优先级：{priority_text}，分类：{category_text}，处理人：{assignee}。'


def build_next_actions(ticket: Ticket) -> list[str]:
    """根据工单当前状态生成下一步处理建议。"""

    actions: list[str] = []
    now = timezone.now()

    if ticket.due_at and ticket.due_at < now and not ticket.is_finished:
        actions.append('工单已经超时，建议先确认影响范围并进行催办。')
    if ticket.assignee_id is None and ticket.status != TicketStatus.CLOSED:
        actions.append('当前还没有处理人，建议尽快分配负责人。')
    if ticket.status == TicketStatus.OPEN:
        actions.append('建议先补充复现信息，然后将状态推进到处理中。')
    elif ticket.status == TicketStatus.IN_PROGRESS:
        actions.append('建议补充处理记录；如果问题已经修复，可以标记为已解决。')
    elif ticket.status == TicketStatus.RESOLVED:
        actions.append('建议由创建人确认结果，确认无误后关闭工单。')
    elif ticket.status == TicketStatus.CLOSED:
        actions.append('工单已关闭，如用户反馈未解决，可以填写原因后重开。')

    if ticket.priority in {TicketPriority.HIGH, TicketPriority.URGENT}:
        actions.append('高优先级工单建议同步通知相关关注人，避免信息断层。')

    return list(dict.fromkeys(actions))


def build_reply_template(ticket: Ticket) -> str:
    """生成一段可复制的回复模板。"""

    if ticket.status == TicketStatus.CLOSED:
        return '您好，当前工单已关闭。如问题仍未解决，请补充现象和影响范围，我们会重新打开并继续跟进。'
    if ticket.assignee_id is None:
        return '您好，我们已经收到反馈，接下来会先分配处理人，并在确认影响范围后同步处理进展。'
    return f'您好，工单已由 {ticket.assignee.username} 跟进处理中。请补充截图、报错信息或复现步骤，方便我们更快定位问题。'


def build_ticket_assistant_suggestion(ticket: Ticket) -> dict:
    """生成已有工单的智能处理建议。"""

    recent_comments = list(ticket.comments.select_related('author').order_by('-created_at')[:3])
    comment_summaries = [
        f'{comment.author.username}：{normalize_text(comment.content)[:80]}'
        for comment in recent_comments
    ]

    return {
        'summary': build_ticket_summary(ticket),
        'next_actions': build_next_actions(ticket),
        'reply_template': build_reply_template(ticket),
        'recent_comments': comment_summaries,
        'attachment_count': ticket.attachments.count(),
        'confidence': 0.78 if recent_comments else 0.68,
    }
