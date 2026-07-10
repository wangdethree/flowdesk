import tempfile
from datetime import timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.audit.models import AuditAction, AuditLog
from apps.notifications.models import Notification, NotificationType
from apps.tickets.models import (
    Ticket,
    TicketAttachment,
    TicketCategory,
    TicketComment,
    TicketFeedback,
    TicketPriority,
    TicketStatus,
    TicketTag,
)


User = get_user_model()


class TicketModelTests(TestCase):
    def setUp(self):
        self.creator = User.objects.create_user(username='creator', password='TestPass123')
        self.assignee = User.objects.create_user(username='assignee', password='TestPass123')

    def test_create_ticket_with_default_values(self):
        ticket = Ticket.objects.create(
            title='电脑无法连接公司网络',
            description='连接公司 Wi-Fi 后无法访问内部系统。',
            creator=self.creator,
        )

        self.assertEqual(ticket.category, TicketCategory.OTHER)
        self.assertEqual(ticket.priority, TicketPriority.MEDIUM)
        self.assertEqual(ticket.status, TicketStatus.OPEN)
        self.assertEqual(str(ticket), f'#{ticket.id} 电脑无法连接公司网络')

    def test_ticket_can_have_assignee(self):
        ticket = Ticket.objects.create(
            title='测试环境接口报错',
            description='调用测试环境接口时返回 500。',
            category=TicketCategory.BUG,
            priority=TicketPriority.HIGH,
            creator=self.creator,
            assignee=self.assignee,
        )

        self.assertEqual(ticket.assignee, self.assignee)
        self.assertIn(ticket, self.assignee.assigned_tickets.all())

    def test_finished_ticket_status(self):
        resolved_ticket = Ticket.objects.create(
            title='已解决工单',
            description='问题已经处理完成。',
            creator=self.creator,
            status=TicketStatus.RESOLVED,
            resolved_at=timezone.now(),
        )
        open_ticket = Ticket.objects.create(
            title='待处理工单',
            description='问题还没有开始处理。',
            creator=self.creator,
        )

        self.assertTrue(resolved_ticket.is_finished)
        self.assertFalse(open_ticket.is_finished)

    def test_overdue_ticket(self):
        ticket = Ticket.objects.create(
            title='超时工单',
            description='截止时间已经过去。',
            creator=self.creator,
            due_at=timezone.now() - timedelta(hours=1),
        )

        self.assertTrue(ticket.is_overdue)

    def test_create_ticket_comment(self):
        ticket = Ticket.objects.create(
            title='需要补充截图',
            description='用户反馈页面异常。',
            creator=self.creator,
            assignee=self.assignee,
        )

        comment = TicketComment.objects.create(
            ticket=ticket,
            author=self.assignee,
            content='请补充浏览器控制台截图。',
            comment_type=TicketComment.CommentType.HANDLING,
        )

        self.assertEqual(comment.ticket, ticket)
        self.assertEqual(comment.author, self.assignee)
        self.assertEqual(ticket.comments.count(), 1)
        self.assertEqual(str(comment), f'处理记录 - {ticket.id}')

    def test_create_ticket_tag(self):
        tag = TicketTag.objects.create(name='线上故障', color='#ef4444')

        self.assertEqual(str(tag), '线上故障')
        self.assertEqual(tag.color, '#ef4444')


class TicketAPITests(APITestCase):
    def setUp(self):
        # 文件上传测试会真实写入临时文件。
        # 这里把 MEDIA_ROOT 指到临时目录，测试结束后自动清理，避免污染项目本地 media/。
        self.media_root = tempfile.TemporaryDirectory()
        self.addCleanup(self.media_root.cleanup)
        self.media_override = override_settings(MEDIA_ROOT=self.media_root.name)
        self.media_override.enable()
        self.addCleanup(self.media_override.disable)

        self.creator = User.objects.create_user(username='creator_api', password='TestPass123')
        self.assignee = User.objects.create_user(username='assignee_api', password='TestPass123')
        self.other_user = User.objects.create_user(username='other_api', password='TestPass123')
        self.staff_user = User.objects.create_user(
            username='staff_api',
            password='TestPass123',
            is_staff=True,
        )

    def get_results(self, response):
        """读取分页列表里的真实数据。

        开启 DRF 分页后，列表接口返回结构会变成：
        {"count": 2, "next": null, "previous": null, "results": [...]}
        """

        return response.data['results']

    def test_list_requires_authentication(self):
        response = self.client.get(reverse('ticket-list'))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_ticket_sets_current_user_as_creator(self):
        self.client.force_authenticate(user=self.creator)

        response = self.client.post(
            reverse('ticket-list'),
            {
                'title': '电脑无法连接公司网络',
                'description': '连接公司 Wi-Fi 后无法访问内部系统。',
                'category': TicketCategory.BUG,
                'priority': TicketPriority.HIGH,
                'assignee': self.assignee.id,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        ticket = Ticket.objects.get(id=response.data['id'])
        self.assertEqual(ticket.creator, self.creator)
        self.assertEqual(ticket.assignee, self.assignee)
        self.assertTrue(
            AuditLog.objects.filter(
                actor=self.creator,
                action=AuditAction.CREATE,
                target_type='Ticket',
                target_id=str(ticket.id),
            ).exists()
        )

    def test_list_only_returns_visible_tickets_for_normal_user(self):
        own_ticket = Ticket.objects.create(
            title='我创建的工单',
            description='普通用户应该能看到自己创建的工单。',
            creator=self.creator,
        )
        assigned_ticket = Ticket.objects.create(
            title='分配给我的工单',
            description='普通用户应该能看到分配给自己的工单。',
            creator=self.other_user,
            assignee=self.creator,
        )
        Ticket.objects.create(
            title='别人的工单',
            description='普通用户不应该看到无关工单。',
            creator=self.other_user,
        )
        self.client.force_authenticate(user=self.creator)

        response = self.client.get(reverse('ticket-list'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_ids = {item['id'] for item in self.get_results(response)}
        self.assertEqual(returned_ids, {own_ticket.id, assigned_ticket.id})

    def test_watcher_can_list_and_retrieve_watched_ticket(self):
        """关注人可以看到自己关注的工单。"""

        watched_ticket = Ticket.objects.create(
            title='我关注的工单',
            description='关注后应该进入我的可见范围。',
            creator=self.creator,
        )
        watched_ticket.watchers.add(self.other_user)
        self.client.force_authenticate(user=self.other_user)

        list_response = self.client.get(reverse('ticket-list'))
        detail_response = self.client.get(reverse('ticket-detail', args=[watched_ticket.id]))

        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        returned_ids = {item['id'] for item in self.get_results(list_response)}
        self.assertEqual(returned_ids, {watched_ticket.id})
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)

    def test_staff_can_list_all_tickets(self):
        Ticket.objects.create(title='工单一', description='管理员可见。', creator=self.creator)
        Ticket.objects.create(title='工单二', description='管理员可见。', creator=self.other_user)
        self.client.force_authenticate(user=self.staff_user)

        response = self.client.get(reverse('ticket-list'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)

    def test_assignee_can_retrieve_and_update_but_cannot_delete_ticket(self):
        ticket = Ticket.objects.create(
            title='分配给处理人的工单',
            description='处理人可以查看和处理，但不能删除。',
            creator=self.creator,
            assignee=self.assignee,
        )
        self.client.force_authenticate(user=self.assignee)

        detail_url = reverse('ticket-detail', args=[ticket.id])
        retrieve_response = self.client.get(detail_url)
        update_response = self.client.patch(
            detail_url,
            {'status': TicketStatus.IN_PROGRESS},
            format='json',
        )
        delete_response = self.client.delete(detail_url)

        self.assertEqual(retrieve_response.status_code, status.HTTP_200_OK)
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        self.assertEqual(update_response.data['status'], TicketStatus.IN_PROGRESS)
        self.assertEqual(delete_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(
            AuditLog.objects.filter(
                actor=self.assignee,
                action=AuditAction.STATUS_CHANGE,
                target_type='Ticket',
                target_id=str(ticket.id),
            ).exists()
        )

    def test_unrelated_user_cannot_retrieve_ticket(self):
        ticket = Ticket.objects.create(
            title='无关用户不可见工单',
            description='既不是创建人也不是处理人时不能查看。',
            creator=self.creator,
        )
        self.client.force_authenticate(user=self.other_user)

        response = self.client.get(reverse('ticket-detail', args=[ticket.id]))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_creator_can_update_and_delete_ticket(self):
        ticket = Ticket.objects.create(
            title='创建人可管理工单',
            description='创建人可以修改和删除自己的工单。',
            creator=self.creator,
        )
        self.client.force_authenticate(user=self.creator)

        detail_url = reverse('ticket-detail', args=[ticket.id])
        update_response = self.client.patch(
            detail_url,
            {'status': TicketStatus.IN_PROGRESS},
            format='json',
        )
        delete_response = self.client.delete(detail_url)

        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        self.assertEqual(update_response.data['status'], TicketStatus.IN_PROGRESS)
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Ticket.objects.filter(id=ticket.id).exists())
        self.assertTrue(
            AuditLog.objects.filter(
                actor=self.creator,
                action=AuditAction.DELETE,
                target_type='Ticket',
                target_id=str(ticket.id),
            ).exists()
        )

    def test_filter_and_search_tickets(self):
        Ticket.objects.create(
            title='网络故障工单',
            description='公司网络不稳定。',
            category=TicketCategory.BUG,
            priority=TicketPriority.HIGH,
            creator=self.creator,
        )
        Ticket.objects.create(
            title='功能咨询工单',
            description='咨询报表导出功能。',
            category=TicketCategory.CONSULT,
            priority=TicketPriority.LOW,
            creator=self.creator,
        )
        self.client.force_authenticate(user=self.creator)

        response = self.client.get(
            reverse('ticket-list'),
            {
                'category': TicketCategory.BUG,
                'search': '网络',
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(self.get_results(response)[0]['title'], '网络故障工单')

    def test_create_and_list_ticket_tags(self):
        """登录用户可以创建和查询工单标签。"""

        self.client.force_authenticate(user=self.creator)

        create_response = self.client.post(
            reverse('ticket-tag-list'),
            {'name': '线上故障', 'color': '#ef4444'},
            format='json',
        )
        list_response = self.client.get(reverse('ticket-tag-list'), {'search': '线上'})

        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(create_response.data['name'], '线上故障')
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(list_response.data['count'], 1)
        self.assertEqual(list_response.data['results'][0]['color'], '#ef4444')

    def test_creator_can_set_ticket_tags(self):
        """工单创建人可以给自己的工单设置标签。"""

        bug_tag = TicketTag.objects.create(name='线上故障', color='#ef4444')
        vip_tag = TicketTag.objects.create(name='VIP客户', color='#f59e0b')
        ticket = Ticket.objects.create(
            title='设置标签工单',
            description='验证创建人可以维护标签。',
            creator=self.creator,
        )
        self.client.force_authenticate(user=self.creator)

        response = self.client.post(
            reverse('ticket-set-tags', args=[ticket.id]),
            {'tags': [bug_tag.id, vip_tag.id]},
            format='json',
        )
        ticket.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(set(response.data['tags']), {bug_tag.id, vip_tag.id})
        self.assertEqual(set(response.data['tag_names']), {'线上故障', 'VIP客户'})
        self.assertEqual(set(ticket.tags.values_list('id', flat=True)), {bug_tag.id, vip_tag.id})

    def test_non_creator_cannot_set_ticket_tags(self):
        """非创建人不能维护别人工单的标签。"""

        tag = TicketTag.objects.create(name='支付模块')
        ticket = Ticket.objects.create(
            title='别人创建的工单',
            description='处理人不能随便改标签。',
            creator=self.creator,
            assignee=self.assignee,
        )
        self.client.force_authenticate(user=self.assignee)

        response = self.client.post(
            reverse('ticket-set-tags', args=[ticket.id]),
            {'tags': [tag.id]},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(ticket.tags.count(), 0)

    def test_filter_tickets_by_tag(self):
        """工单列表支持按标签 ID 和标签名称筛选。"""

        bug_tag = TicketTag.objects.create(name='线上故障')
        vip_tag = TicketTag.objects.create(name='VIP客户')
        bug_ticket = Ticket.objects.create(
            title='线上故障工单',
            description='带有线上故障标签。',
            creator=self.creator,
        )
        bug_ticket.tags.add(bug_tag)
        vip_ticket = Ticket.objects.create(
            title='VIP 工单',
            description='带有 VIP 标签。',
            creator=self.creator,
        )
        vip_ticket.tags.add(vip_tag)
        self.client.force_authenticate(user=self.creator)

        by_id_response = self.client.get(reverse('ticket-list'), {'tag': bug_tag.id})
        by_name_response = self.client.get(reverse('ticket-list'), {'tag_name': 'VIP客户'})

        self.assertEqual(by_id_response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            {item['id'] for item in self.get_results(by_id_response)},
            {bug_ticket.id},
        )
        self.assertEqual(by_name_response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            {item['id'] for item in self.get_results(by_name_response)},
            {vip_ticket.id},
        )

    def test_filter_tickets_by_mine_created(self):
        """mine=created 只返回当前用户自己创建的工单。"""

        created_by_me = Ticket.objects.create(
            title='我创建的工单',
            description='用于验证 mine=created。',
            creator=self.creator,
        )
        Ticket.objects.create(
            title='分配给我的工单',
            description='这个工单不是我创建的，所以不应该出现在 mine=created 结果里。',
            creator=self.other_user,
            assignee=self.creator,
        )
        self.client.force_authenticate(user=self.creator)

        response = self.client.get(reverse('ticket-list'), {'mine': 'created'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_ids = {item['id'] for item in self.get_results(response)}
        self.assertEqual(returned_ids, {created_by_me.id})

    def test_filter_tickets_by_mine_assigned(self):
        """mine=assigned 只返回分配给当前用户处理的工单。"""

        assigned_to_me = Ticket.objects.create(
            title='分配给我的工单',
            description='用于验证 mine=assigned。',
            creator=self.other_user,
            assignee=self.creator,
        )
        Ticket.objects.create(
            title='我创建但未分配给我的工单',
            description='这个工单不应该出现在 mine=assigned 结果里。',
            creator=self.creator,
        )
        self.client.force_authenticate(user=self.creator)

        response = self.client.get(reverse('ticket-list'), {'mine': 'assigned'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_ids = {item['id'] for item in self.get_results(response)}
        self.assertEqual(returned_ids, {assigned_to_me.id})

    def test_filter_tickets_by_mine_watched(self):
        """mine=watched 只返回当前用户关注的工单。"""

        watched_ticket = Ticket.objects.create(
            title='关注的工单',
            description='用于验证 mine=watched。',
            creator=self.creator,
        )
        watched_ticket.watchers.add(self.other_user)
        Ticket.objects.create(
            title='未关注工单',
            description='这张工单不应该出现在 mine=watched 结果里。',
            creator=self.other_user,
        )
        self.client.force_authenticate(user=self.other_user)

        response = self.client.get(reverse('ticket-list'), {'mine': 'watched'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_ids = {item['id'] for item in self.get_results(response)}
        self.assertEqual(returned_ids, {watched_ticket.id})

    def test_filter_tickets_by_overdue(self):
        """overdue=true 只返回超过截止时间且仍未完成的工单。"""

        overdue_ticket = Ticket.objects.create(
            title='已经超时的工单',
            description='截止时间已经过去，并且状态仍是待处理。',
            creator=self.creator,
            due_at=timezone.now() - timedelta(hours=2),
        )
        Ticket.objects.create(
            title='已经解决的历史工单',
            description='即使截止时间在过去，已解决工单也不算当前超时。',
            creator=self.creator,
            status=TicketStatus.RESOLVED,
            due_at=timezone.now() - timedelta(hours=2),
            resolved_at=timezone.now(),
        )
        Ticket.objects.create(
            title='还没到期的工单',
            description='截止时间在未来，不应该被 overdue=true 查出来。',
            creator=self.creator,
            due_at=timezone.now() + timedelta(hours=2),
        )
        self.client.force_authenticate(user=self.creator)

        response = self.client.get(reverse('ticket-list'), {'overdue': 'true'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_ids = {item['id'] for item in self.get_results(response)}
        self.assertEqual(returned_ids, {overdue_ticket.id})

    def test_filter_tickets_by_has_assignee(self):
        """has_assignee=false 可以查询还没有处理人的工单。"""

        unassigned_ticket = Ticket.objects.create(
            title='未分配工单',
            description='还没有处理人。',
            creator=self.creator,
        )
        Ticket.objects.create(
            title='已分配工单',
            description='已经有处理人。',
            creator=self.creator,
            assignee=self.assignee,
        )
        self.client.force_authenticate(user=self.creator)

        response = self.client.get(reverse('ticket-list'), {'has_assignee': 'false'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_ids = {item['id'] for item in self.get_results(response)}
        self.assertEqual(returned_ids, {unassigned_ticket.id})

    def test_invalid_ticket_filter_returns_bad_request(self):
        """筛选参数非法时返回 400，避免静默忽略错误查询条件。"""

        self.client.force_authenticate(user=self.creator)

        response = self.client.get(reverse('ticket-list'), {'priority': 'not-exists'})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_ticket_list_is_paginated(self):
        for index in range(12):
            Ticket.objects.create(
                title=f'分页测试工单 {index}',
                description='验证列表接口默认分页。',
                creator=self.creator,
            )
        self.client.force_authenticate(user=self.creator)

        response = self.client.get(reverse('ticket-list'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 12)
        self.assertEqual(len(response.data['results']), 10)

    def test_valid_status_transition_sets_timestamp(self):
        ticket = Ticket.objects.create(
            title='状态流转工单',
            description='验证处理中到已解决会记录解决时间。',
            creator=self.creator,
            assignee=self.assignee,
            status=TicketStatus.IN_PROGRESS,
        )
        self.client.force_authenticate(user=self.assignee)

        response = self.client.patch(
            reverse('ticket-detail', args=[ticket.id]),
            {'status': TicketStatus.RESOLVED},
            format='json',
        )
        ticket.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(ticket.status, TicketStatus.RESOLVED)
        self.assertIsNotNone(ticket.resolved_at)

    def test_status_change_creates_notification_for_other_participant(self):
        """处理人变更状态后，创建人会收到状态变化通知。"""

        ticket = Ticket.objects.create(
            title='状态通知工单',
            description='验证状态变化会通知其他参与者。',
            creator=self.creator,
            assignee=self.assignee,
            status=TicketStatus.IN_PROGRESS,
        )
        self.client.force_authenticate(user=self.assignee)

        response = self.client.patch(
            reverse('ticket-detail', args=[ticket.id]),
            {'status': TicketStatus.RESOLVED},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        notification = Notification.objects.get(
            recipient=self.creator,
            notification_type=NotificationType.TICKET_STATUS_CHANGED,
        )
        self.assertEqual(notification.metadata['old_status'], TicketStatus.IN_PROGRESS)
        self.assertEqual(notification.metadata['new_status'], TicketStatus.RESOLVED)

    def test_status_change_creates_notification_for_watcher(self):
        """工单状态变化后，关注人会收到通知。"""

        watcher = User.objects.create_user(username='watcher_status', password='TestPass123')
        ticket = Ticket.objects.create(
            title='关注人状态通知工单',
            description='验证状态变化也会通知关注人。',
            creator=self.creator,
            assignee=self.assignee,
            status=TicketStatus.IN_PROGRESS,
        )
        ticket.watchers.add(watcher)
        self.client.force_authenticate(user=self.assignee)

        response = self.client.patch(
            reverse('ticket-detail', args=[ticket.id]),
            {'status': TicketStatus.RESOLVED},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(
            Notification.objects.filter(
                recipient=watcher,
                notification_type=NotificationType.TICKET_STATUS_CHANGED,
            ).exists()
        )

    def test_invalid_status_transition_returns_bad_request(self):
        ticket = Ticket.objects.create(
            title='已关闭工单',
            description='关闭后的工单不能重新打开。',
            creator=self.creator,
            status=TicketStatus.CLOSED,
            closed_at=timezone.now(),
        )
        self.client.force_authenticate(user=self.creator)

        response = self.client.patch(
            reverse('ticket-detail', args=[ticket.id]),
            {'status': TicketStatus.OPEN},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_patch_cannot_close_ticket_directly(self):
        """普通更新接口不能直接关闭工单，避免绕过关闭原因。"""

        ticket = Ticket.objects.create(
            title='不能直接关闭工单',
            description='关闭工单必须走 close 接口填写原因。',
            creator=self.creator,
            status=TicketStatus.RESOLVED,
            resolved_at=timezone.now(),
        )
        self.client.force_authenticate(user=self.creator)

        response = self.client.patch(
            reverse('ticket-detail', args=[ticket.id]),
            {'status': TicketStatus.CLOSED},
            format='json',
        )
        ticket.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(ticket.status, TicketStatus.RESOLVED)
        self.assertEqual(ticket.close_reason, '')

    def test_creator_can_close_ticket_with_reason(self):
        """创建人可以关闭工单，关闭时会保存原因、写审计日志并通知处理人。"""

        ticket = Ticket.objects.create(
            title='关闭测试工单',
            description='验证关闭动作必须记录原因。',
            creator=self.creator,
            assignee=self.assignee,
            status=TicketStatus.RESOLVED,
            resolved_at=timezone.now(),
        )
        self.client.force_authenticate(user=self.creator)

        response = self.client.post(
            reverse('ticket-close', args=[ticket.id]),
            {'reason': '用户确认问题已经解决，可以关闭。'},
            format='json',
        )
        ticket.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(ticket.status, TicketStatus.CLOSED)
        self.assertEqual(ticket.close_reason, '用户确认问题已经解决，可以关闭。')
        self.assertIsNotNone(ticket.closed_at)
        self.assertTrue(
            AuditLog.objects.filter(
                actor=self.creator,
                action=AuditAction.STATUS_CHANGE,
                target_type='Ticket',
                target_id=str(ticket.id),
                metadata={
                    'old_status': TicketStatus.RESOLVED,
                    'new_status': TicketStatus.CLOSED,
                    'reason': '用户确认问题已经解决，可以关闭。',
                },
            ).exists()
        )
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.assignee,
                notification_type=NotificationType.TICKET_STATUS_CHANGED,
            ).exists()
        )

    def test_close_ticket_requires_reason(self):
        """关闭原因不能为空，避免终态工单没有复盘上下文。"""

        ticket = Ticket.objects.create(
            title='关闭原因必填工单',
            description='没有原因不能关闭。',
            creator=self.creator,
        )
        self.client.force_authenticate(user=self.creator)

        response = self.client.post(
            reverse('ticket-close', args=[ticket.id]),
            {'reason': ''},
            format='json',
        )
        ticket.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(ticket.status, TicketStatus.OPEN)

    def test_assignee_cannot_close_ticket(self):
        """普通处理人不能关闭工单，关闭终态交给创建人或管理员确认。"""

        ticket = Ticket.objects.create(
            title='处理人不可关闭工单',
            description='处理人可以解决问题，但最终关闭由创建人确认。',
            creator=self.creator,
            assignee=self.assignee,
            status=TicketStatus.RESOLVED,
            resolved_at=timezone.now(),
        )
        self.client.force_authenticate(user=self.assignee)

        response = self.client.post(
            reverse('ticket-close', args=[ticket.id]),
            {'reason': '处理人尝试关闭。'},
            format='json',
        )
        ticket.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(ticket.status, TicketStatus.RESOLVED)

    def test_creator_can_reopen_closed_ticket_with_reason(self):
        """创建人可以重开已关闭工单，并保存重开原因。"""

        ticket = Ticket.objects.create(
            title='重开测试工单',
            description='验证已关闭工单可以因问题复现而重开。',
            creator=self.creator,
            assignee=self.assignee,
            status=TicketStatus.CLOSED,
            resolved_at=timezone.now(),
            closed_at=timezone.now(),
            close_reason='用户曾确认问题解决。',
        )
        self.client.force_authenticate(user=self.creator)

        response = self.client.post(
            reverse('ticket-reopen', args=[ticket.id]),
            {'reason': '用户反馈问题再次出现，需要重新处理。'},
            format='json',
        )
        ticket.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(ticket.status, TicketStatus.OPEN)
        self.assertIsNone(ticket.resolved_at)
        self.assertIsNone(ticket.closed_at)
        self.assertEqual(ticket.reopen_reason, '用户反馈问题再次出现，需要重新处理。')
        self.assertTrue(
            AuditLog.objects.filter(
                actor=self.creator,
                action=AuditAction.STATUS_CHANGE,
                target_type='Ticket',
                target_id=str(ticket.id),
                metadata={
                    'old_status': TicketStatus.CLOSED,
                    'new_status': TicketStatus.OPEN,
                    'reason': '用户反馈问题再次出现，需要重新处理。',
                },
            ).exists()
        )

    def test_cannot_reopen_unclosed_ticket(self):
        """只有已关闭工单可以重开。"""

        ticket = Ticket.objects.create(
            title='未关闭不可重开',
            description='还没关闭的工单不应该执行重开动作。',
            creator=self.creator,
            status=TicketStatus.RESOLVED,
            resolved_at=timezone.now(),
        )
        self.client.force_authenticate(user=self.creator)

        response = self.client.post(
            reverse('ticket-reopen', args=[ticket.id]),
            {'reason': '尝试重开未关闭工单。'},
            format='json',
        )
        ticket.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(ticket.status, TicketStatus.RESOLVED)

    def test_timeline_contains_ticket_events(self):
        """工单时间线会聚合审计日志、评论、附件和评价。"""

        ticket = Ticket.objects.create(
            title='时间线测试工单',
            description='验证多种动态可以聚合展示。',
            creator=self.creator,
            assignee=self.assignee,
            status=TicketStatus.CLOSED,
            closed_at=timezone.now(),
        )
        AuditLog.objects.create(
            actor=self.creator,
            action=AuditAction.CREATE,
            target_type='Ticket',
            target_id=str(ticket.id),
            description='创建工单',
            metadata={'title': ticket.title},
        )
        TicketComment.objects.create(
            ticket=ticket,
            author=self.assignee,
            content='已经处理完成。',
            comment_type=TicketComment.CommentType.HANDLING,
        )
        TicketAttachment.objects.create(
            ticket=ticket,
            uploaded_by=self.assignee,
            file=SimpleUploadedFile('result.txt', b'ok', content_type='text/plain'),
            original_filename='result.txt',
            content_type='text/plain',
            size=2,
        )
        TicketFeedback.objects.create(
            ticket=ticket,
            created_by=self.creator,
            rating=5,
            content='处理满意。',
        )
        self.client.force_authenticate(user=self.creator)

        response = self.client.get(reverse('ticket-timeline', args=[ticket.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = self.get_results(response)
        event_types = {item['event_type'] for item in results}
        self.assertEqual(event_types, {'audit', 'comment', 'attachment', 'feedback'})
        feedback_item = next(item for item in results if item['event_type'] == 'feedback')
        self.assertEqual(feedback_item['metadata']['rating'], 5)

    def test_unrelated_user_cannot_view_ticket_timeline(self):
        """无关用户不能查看自己不可见工单的时间线。"""

        ticket = Ticket.objects.create(
            title='不可见时间线工单',
            description='无关用户不能查看。',
            creator=self.creator,
        )
        self.client.force_authenticate(user=self.other_user)

        response = self.client.get(reverse('ticket-timeline', args=[ticket.id]))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_creator_can_submit_feedback_for_closed_ticket(self):
        """工单创建人可以评价已关闭工单，并通知处理人。"""

        ticket = Ticket.objects.create(
            title='评价测试工单',
            description='验证关闭后可以评价处理结果。',
            creator=self.creator,
            assignee=self.assignee,
            status=TicketStatus.CLOSED,
            closed_at=timezone.now(),
            close_reason='用户确认可以关闭。',
        )
        self.client.force_authenticate(user=self.creator)

        response = self.client.post(
            reverse('ticket-feedback', args=[ticket.id]),
            {'rating': 5, 'content': '处理很及时，问题已经解决。'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        feedback = TicketFeedback.objects.get(ticket=ticket)
        self.assertEqual(feedback.created_by, self.creator)
        self.assertEqual(feedback.rating, 5)
        self.assertEqual(feedback.content, '处理很及时，问题已经解决。')
        self.assertTrue(
            AuditLog.objects.filter(
                actor=self.creator,
                action=AuditAction.FEEDBACK,
                target_type='Ticket',
                target_id=str(ticket.id),
                metadata={
                    'feedback_id': feedback.id,
                    'rating': 5,
                    'content': '处理很及时，问题已经解决。',
                    'created': True,
                },
            ).exists()
        )
        notification = Notification.objects.get(
            recipient=self.assignee,
            notification_type=NotificationType.TICKET_FEEDBACK_SUBMITTED,
        )
        self.assertEqual(notification.metadata['feedback_id'], feedback.id)
        self.assertEqual(notification.metadata['rating'], 5)

    def test_creator_can_update_existing_feedback(self):
        """同一张工单重复评价时更新原评价，不创建多条评价。"""

        ticket = Ticket.objects.create(
            title='重复评价测试工单',
            description='验证一张工单只保留一份最终评价。',
            creator=self.creator,
            assignee=self.assignee,
            status=TicketStatus.CLOSED,
            closed_at=timezone.now(),
            close_reason='用户确认可以关闭。',
        )
        TicketFeedback.objects.create(
            ticket=ticket,
            created_by=self.creator,
            rating=3,
            content='第一次评价。',
        )
        self.client.force_authenticate(user=self.creator)

        response = self.client.post(
            reverse('ticket-feedback', args=[ticket.id]),
            {'rating': 4, 'content': '补充评价后更准确。'},
            format='json',
        )
        feedback = TicketFeedback.objects.get(ticket=ticket)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(TicketFeedback.objects.filter(ticket=ticket).count(), 1)
        self.assertEqual(feedback.rating, 4)
        self.assertEqual(feedback.content, '补充评价后更准确。')
        self.assertTrue(
            AuditLog.objects.filter(
                actor=self.creator,
                action=AuditAction.FEEDBACK,
                target_type='Ticket',
                target_id=str(ticket.id),
                metadata={
                    'feedback_id': feedback.id,
                    'rating': 4,
                    'content': '补充评价后更准确。',
                    'created': False,
                },
            ).exists()
        )

    def test_assignee_can_retrieve_ticket_feedback(self):
        """工单参与者可以查看已有评价。"""

        ticket = Ticket.objects.create(
            title='查询评价测试工单',
            description='处理人可以看到创建人的评价反馈。',
            creator=self.creator,
            assignee=self.assignee,
            status=TicketStatus.CLOSED,
            closed_at=timezone.now(),
        )
        feedback = TicketFeedback.objects.create(
            ticket=ticket,
            created_by=self.creator,
            rating=5,
            content='处理结果满意。',
        )
        self.client.force_authenticate(user=self.assignee)

        response = self.client.get(reverse('ticket-feedback', args=[ticket.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], feedback.id)
        self.assertEqual(response.data['rating'], 5)

    def test_feedback_requires_closed_ticket(self):
        """未关闭工单不能评价，避免流程还没结束就提前打分。"""

        ticket = Ticket.objects.create(
            title='未关闭不可评价',
            description='工单还在处理中。',
            creator=self.creator,
            assignee=self.assignee,
            status=TicketStatus.RESOLVED,
            resolved_at=timezone.now(),
        )
        self.client.force_authenticate(user=self.creator)

        response = self.client.post(
            reverse('ticket-feedback', args=[ticket.id]),
            {'rating': 5, 'content': '提前评价。'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(TicketFeedback.objects.filter(ticket=ticket).exists())

    def test_assignee_cannot_submit_ticket_feedback(self):
        """处理人不能给自己处理的工单评价。"""

        ticket = Ticket.objects.create(
            title='处理人不可评价工单',
            description='评价必须来自创建人。',
            creator=self.creator,
            assignee=self.assignee,
            status=TicketStatus.CLOSED,
            closed_at=timezone.now(),
        )
        self.client.force_authenticate(user=self.assignee)

        response = self.client.post(
            reverse('ticket-feedback', args=[ticket.id]),
            {'rating': 5, 'content': '处理人尝试自评。'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(TicketFeedback.objects.filter(ticket=ticket).exists())

    def test_feedback_rating_must_be_between_one_and_five(self):
        """评分只能在 1 到 5 之间。"""

        ticket = Ticket.objects.create(
            title='非法评分测试工单',
            description='验证评分范围校验。',
            creator=self.creator,
            status=TicketStatus.CLOSED,
            closed_at=timezone.now(),
        )
        self.client.force_authenticate(user=self.creator)

        response = self.client.post(
            reverse('ticket-feedback', args=[ticket.id]),
            {'rating': 6, 'content': '非法评分。'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_missing_ticket_feedback_returns_not_found(self):
        """工单还没有评价时，查询评价返回 404。"""

        ticket = Ticket.objects.create(
            title='没有评价的工单',
            description='验证空评价查询。',
            creator=self.creator,
            assignee=self.assignee,
            status=TicketStatus.CLOSED,
            closed_at=timezone.now(),
        )
        self.client.force_authenticate(user=self.assignee)

        response = self.client.get(reverse('ticket-feedback', args=[ticket.id]))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_creator_can_assign_ticket(self):
        """工单创建人可以把工单分配给处理人。"""

        ticket = Ticket.objects.create(
            title='待分配工单',
            description='创建人准备把工单分配给处理人。',
            creator=self.creator,
        )
        self.client.force_authenticate(user=self.creator)

        response = self.client.post(
            reverse('ticket-assign', args=[ticket.id]),
            {'assignee': self.assignee.id},
            format='json',
        )
        ticket.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(ticket.assignee, self.assignee)
        self.assertEqual(response.data['assignee'], self.assignee.id)
        self.assertTrue(
            AuditLog.objects.filter(
                actor=self.creator,
                action=AuditAction.ASSIGN,
                target_type='Ticket',
                target_id=str(ticket.id),
                metadata={
                    'old_assignee_id': None,
                    'new_assignee_id': self.assignee.id,
                },
            ).exists()
        )

    def test_assign_ticket_creates_notification_for_assignee(self):
        """工单分配后，新的处理人会收到站内通知。"""

        ticket = Ticket.objects.create(
            title='分配通知工单',
            description='验证分配工单会生成通知。',
            creator=self.creator,
        )
        self.client.force_authenticate(user=self.creator)

        response = self.client.post(
            reverse('ticket-assign', args=[ticket.id]),
            {'assignee': self.assignee.id},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        notification = Notification.objects.get(
            recipient=self.assignee,
            notification_type=NotificationType.TICKET_ASSIGNED,
        )
        self.assertEqual(notification.target_type, 'Ticket')
        self.assertEqual(notification.target_id, str(ticket.id))
        self.assertEqual(notification.metadata['actor_id'], self.creator.id)

    def test_staff_can_assign_any_visible_ticket(self):
        """管理员可以分配任意工单，不受普通用户可见范围限制。"""

        ticket = Ticket.objects.create(
            title='管理员分配工单',
            description='管理员可以统一调度工单。',
            creator=self.other_user,
        )
        self.client.force_authenticate(user=self.staff_user)

        response = self.client.post(
            reverse('ticket-assign', args=[ticket.id]),
            {'assignee': self.assignee.id},
            format='json',
        )
        ticket.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(ticket.assignee, self.assignee)

    def test_creator_can_clear_ticket_assignee(self):
        """assignee=null 表示取消当前处理人。"""

        ticket = Ticket.objects.create(
            title='取消分配工单',
            description='创建人可以把处理人清空。',
            creator=self.creator,
            assignee=self.assignee,
        )
        self.client.force_authenticate(user=self.creator)

        response = self.client.post(
            reverse('ticket-assign', args=[ticket.id]),
            {'assignee': None},
            format='json',
        )
        ticket.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(ticket.assignee)
        self.assertIsNone(response.data['assignee'])

    def test_assignee_cannot_reassign_ticket(self):
        """当前处理人可以处理工单，但不能把工单转派给别人。"""

        ticket = Ticket.objects.create(
            title='处理人不可转派工单',
            description='避免普通处理人绕过创建人或管理员调度。',
            creator=self.creator,
            assignee=self.assignee,
        )
        self.client.force_authenticate(user=self.assignee)

        response = self.client.post(
            reverse('ticket-assign', args=[ticket.id]),
            {'assignee': self.other_user.id},
            format='json',
        )
        ticket.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(ticket.assignee, self.assignee)

    def test_assign_ticket_with_invalid_assignee_returns_bad_request(self):
        """处理人 ID 不存在时返回 400，避免写入无效用户。"""

        ticket = Ticket.objects.create(
            title='非法处理人测试工单',
            description='验证不存在的用户 ID 会被 Serializer 拦截。',
            creator=self.creator,
        )
        self.client.force_authenticate(user=self.creator)

        response = self.client.post(
            reverse('ticket-assign', args=[ticket.id]),
            {'assignee': 999999},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_creator_can_set_ticket_priority(self):
        """工单创建人可以调整优先级，并记录审计日志和通知处理人。"""

        ticket = Ticket.objects.create(
            title='优先级调整工单',
            description='创建人根据业务紧急程度调整优先级。',
            creator=self.creator,
            assignee=self.assignee,
            priority=TicketPriority.MEDIUM,
        )
        self.client.force_authenticate(user=self.creator)

        response = self.client.post(
            reverse('ticket-set-priority', args=[ticket.id]),
            {'priority': TicketPriority.URGENT},
            format='json',
        )
        ticket.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(ticket.priority, TicketPriority.URGENT)
        self.assertEqual(response.data['priority'], TicketPriority.URGENT)
        self.assertTrue(
            AuditLog.objects.filter(
                actor=self.creator,
                action=AuditAction.UPDATE,
                target_type='Ticket',
                target_id=str(ticket.id),
                metadata={
                    'old_priority': TicketPriority.MEDIUM,
                    'new_priority': TicketPriority.URGENT,
                },
            ).exists()
        )
        notification = Notification.objects.get(
            recipient=self.assignee,
            notification_type=NotificationType.TICKET_PRIORITY_CHANGED,
        )
        self.assertEqual(notification.target_id, str(ticket.id))
        self.assertEqual(notification.metadata['old_priority'], TicketPriority.MEDIUM)
        self.assertEqual(notification.metadata['new_priority'], TicketPriority.URGENT)

    def test_staff_can_set_ticket_priority(self):
        """管理员可以调整任意可见工单的优先级，用于统一调度。"""

        ticket = Ticket.objects.create(
            title='管理员调整优先级工单',
            description='管理员处理跨团队调度时可以提升优先级。',
            creator=self.other_user,
            priority=TicketPriority.LOW,
        )
        self.client.force_authenticate(user=self.staff_user)

        response = self.client.post(
            reverse('ticket-set-priority', args=[ticket.id]),
            {'priority': TicketPriority.HIGH},
            format='json',
        )
        ticket.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(ticket.priority, TicketPriority.HIGH)

    def test_assignee_cannot_set_ticket_priority(self):
        """普通处理人不能自行调整优先级，避免绕过创建人或管理员排期。"""

        ticket = Ticket.objects.create(
            title='处理人不可调整优先级',
            description='处理人只能推进工单，不能自己改排期级别。',
            creator=self.creator,
            assignee=self.assignee,
            priority=TicketPriority.MEDIUM,
        )
        self.client.force_authenticate(user=self.assignee)

        response = self.client.post(
            reverse('ticket-set-priority', args=[ticket.id]),
            {'priority': TicketPriority.URGENT},
            format='json',
        )
        ticket.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(ticket.priority, TicketPriority.MEDIUM)

    def test_set_ticket_priority_with_invalid_choice_returns_bad_request(self):
        """优先级枚举值非法时返回 400，避免接口写入脏数据。"""

        ticket = Ticket.objects.create(
            title='非法优先级测试工单',
            description='验证 Serializer 会拦截不存在的优先级。',
            creator=self.creator,
        )
        self.client.force_authenticate(user=self.creator)

        response = self.client.post(
            reverse('ticket-set-priority', args=[ticket.id]),
            {'priority': 'not-exists'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_priority_change_creates_notification_for_watcher(self):
        """工单优先级变化后，关注人也会收到通知。"""

        watcher = User.objects.create_user(username='watcher_priority', password='TestPass123')
        ticket = Ticket.objects.create(
            title='关注人优先级通知工单',
            description='关注人需要知道优先级变更，便于跟进风险。',
            creator=self.creator,
            priority=TicketPriority.LOW,
        )
        ticket.watchers.add(watcher)
        self.client.force_authenticate(user=self.creator)

        response = self.client.post(
            reverse('ticket-set-priority', args=[ticket.id]),
            {'priority': TicketPriority.HIGH},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(
            Notification.objects.filter(
                recipient=watcher,
                notification_type=NotificationType.TICKET_PRIORITY_CHANGED,
            ).exists()
        )

    def test_participant_can_remind_ticket_assignee(self):
        """工单参与者可以催办未完成且已分配的工单。"""

        ticket = Ticket.objects.create(
            title='催办测试工单',
            description='验证催办会通知处理人并写审计日志。',
            creator=self.creator,
            assignee=self.assignee,
        )
        self.client.force_authenticate(user=self.creator)

        response = self.client.post(
            reverse('ticket-remind', args=[ticket.id]),
            {'message': '客户已经二次催促，请优先处理。'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        notification = Notification.objects.get(
            recipient=self.assignee,
            notification_type=NotificationType.TICKET_REMINDED,
        )
        self.assertEqual(notification.target_id, str(ticket.id))
        self.assertEqual(notification.metadata['message'], '客户已经二次催促，请优先处理。')
        self.assertTrue(
            AuditLog.objects.filter(
                actor=self.creator,
                action=AuditAction.REMIND,
                target_type='Ticket',
                target_id=str(ticket.id),
                metadata={
                    'assignee_id': self.assignee.id,
                    'message': '客户已经二次催促，请优先处理。',
                },
            ).exists()
        )

    def test_cannot_remind_unassigned_ticket(self):
        """未分配处理人的工单不能催办。"""

        ticket = Ticket.objects.create(
            title='未分配不可催办',
            description='没有处理人时不知道提醒谁。',
            creator=self.creator,
        )
        self.client.force_authenticate(user=self.creator)

        response = self.client.post(reverse('ticket-remind', args=[ticket.id]), {}, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Notification.objects.filter(notification_type=NotificationType.TICKET_REMINDED).exists())

    def test_cannot_remind_finished_ticket(self):
        """已解决或已关闭工单不能催办。"""

        ticket = Ticket.objects.create(
            title='已解决不可催办',
            description='终态工单不需要再催办。',
            creator=self.creator,
            assignee=self.assignee,
            status=TicketStatus.RESOLVED,
            resolved_at=timezone.now(),
        )
        self.client.force_authenticate(user=self.creator)

        response = self.client.post(reverse('ticket-remind', args=[ticket.id]), {}, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Notification.objects.filter(notification_type=NotificationType.TICKET_REMINDED).exists())

    def test_unrelated_user_cannot_remind_ticket(self):
        """无关用户不能催办自己不可见的工单。"""

        ticket = Ticket.objects.create(
            title='无关用户不可催办',
            description='不可见工单不能催办。',
            creator=self.creator,
            assignee=self.assignee,
        )
        self.client.force_authenticate(user=self.other_user)

        response = self.client.post(reverse('ticket-remind', args=[ticket.id]), {}, format='json')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_participant_can_watch_and_unwatch_ticket(self):
        """工单参与者可以关注和取消关注工单。"""

        ticket = Ticket.objects.create(
            title='关注接口工单',
            description='验证关注和取消关注。',
            creator=self.creator,
            assignee=self.assignee,
        )
        self.client.force_authenticate(user=self.assignee)

        watch_response = self.client.post(reverse('ticket-watch', args=[ticket.id]))
        unwatch_response = self.client.post(reverse('ticket-unwatch', args=[ticket.id]))
        ticket.refresh_from_db()

        self.assertEqual(watch_response.status_code, status.HTTP_200_OK)
        self.assertIn(self.assignee.id, watch_response.data['watchers'])
        self.assertIn(self.assignee.username, watch_response.data['watcher_usernames'])
        self.assertEqual(unwatch_response.status_code, status.HTTP_200_OK)
        self.assertNotIn(self.assignee, ticket.watchers.all())

    def test_participant_can_list_ticket_audit_logs(self):
        """工单参与者可以查看这张工单的操作历史。"""

        ticket = Ticket.objects.create(
            title='操作历史工单',
            description='用于验证参与者能查看审计日志。',
            creator=self.creator,
            assignee=self.assignee,
        )
        AuditLog.objects.create(
            actor=self.creator,
            action=AuditAction.CREATE,
            target_type='Ticket',
            target_id=str(ticket.id),
            description='创建工单',
            metadata={'title': ticket.title},
        )
        AuditLog.objects.create(
            actor=self.assignee,
            action=AuditAction.STATUS_CHANGE,
            target_type='Ticket',
            target_id=str(ticket.id),
            description='变更工单状态',
            metadata={'old_status': TicketStatus.OPEN, 'new_status': TicketStatus.IN_PROGRESS},
        )
        self.client.force_authenticate(user=self.assignee)

        response = self.client.get(reverse('ticket-audit-logs', args=[ticket.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)
        first_log = response.data['results'][0]
        self.assertEqual(first_log['actor_username'], self.assignee.username)
        self.assertEqual(first_log['action'], AuditAction.STATUS_CHANGE)
        self.assertEqual(first_log['action_display'], '状态流转')
        self.assertEqual(first_log['metadata']['new_status'], TicketStatus.IN_PROGRESS)

    def test_ticket_audit_logs_only_return_current_ticket_logs(self):
        """操作历史接口只返回当前工单的日志，不混入其他工单记录。"""

        ticket = Ticket.objects.create(
            title='当前工单',
            description='只应该返回这张工单的日志。',
            creator=self.creator,
        )
        other_ticket = Ticket.objects.create(
            title='其他工单',
            description='这张工单的日志不能出现在当前工单操作历史里。',
            creator=self.creator,
        )
        AuditLog.objects.create(
            actor=self.creator,
            action=AuditAction.CREATE,
            target_type='Ticket',
            target_id=str(ticket.id),
            description='创建当前工单',
        )
        AuditLog.objects.create(
            actor=self.creator,
            action=AuditAction.CREATE,
            target_type='Ticket',
            target_id=str(other_ticket.id),
            description='创建其他工单',
        )
        self.client.force_authenticate(user=self.creator)

        response = self.client.get(reverse('ticket-audit-logs', args=[ticket.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['description'], '创建当前工单')

    def test_ticket_audit_logs_are_paginated(self):
        """操作历史复用列表分页，避免单张工单历史过多时一次返回太大。"""

        ticket = Ticket.objects.create(
            title='分页操作历史工单',
            description='用于验证操作历史默认分页。',
            creator=self.creator,
        )
        for index in range(12):
            AuditLog.objects.create(
                actor=self.creator,
                action=AuditAction.UPDATE,
                target_type='Ticket',
                target_id=str(ticket.id),
                description=f'更新工单 {index}',
            )
        self.client.force_authenticate(user=self.creator)

        response = self.client.get(reverse('ticket-audit-logs', args=[ticket.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 12)
        self.assertEqual(len(response.data['results']), 10)

    def test_unrelated_user_cannot_list_ticket_audit_logs(self):
        """无关用户不能查看别人工单的操作历史。"""

        ticket = Ticket.objects.create(
            title='无关用户不可见历史',
            description='无关用户不应该知道这张工单发生过什么。',
            creator=self.creator,
        )
        AuditLog.objects.create(
            actor=self.creator,
            action=AuditAction.CREATE,
            target_type='Ticket',
            target_id=str(ticket.id),
            description='创建工单',
        )
        self.client.force_authenticate(user=self.other_user)

        response = self.client.get(reverse('ticket-audit-logs', args=[ticket.id]))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_participant_can_upload_and_list_ticket_attachments(self):
        """工单参与者可以上传并查看这张工单的附件。"""

        ticket = Ticket.objects.create(
            title='附件测试工单',
            description='用于验证附件上传和列表。',
            creator=self.creator,
            assignee=self.assignee,
        )
        upload_file = SimpleUploadedFile(
            'error.log',
            b'Traceback: connection refused',
            content_type='text/plain',
        )
        self.client.force_authenticate(user=self.assignee)

        create_response = self.client.post(
            reverse('ticket-attachments', args=[ticket.id]),
            {'file': upload_file},
            format='multipart',
        )
        list_response = self.client.get(reverse('ticket-attachments', args=[ticket.id]))
        attachment = TicketAttachment.objects.get(ticket=ticket)

        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(create_response.data['uploaded_by'], self.assignee.id)
        self.assertEqual(create_response.data['original_filename'], 'error.log')
        self.assertEqual(create_response.data['content_type'], 'text/plain')
        self.assertEqual(create_response.data['size'], len(b'Traceback: connection refused'))
        self.assertTrue(attachment.file.storage.exists(attachment.file.name))
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(list_response.data['count'], 1)
        self.assertEqual(list_response.data['results'][0]['original_filename'], 'error.log')

    def test_unrelated_user_cannot_upload_ticket_attachment(self):
        """无关用户不能给别人的工单上传附件。"""

        ticket = Ticket.objects.create(
            title='无关用户不可上传附件',
            description='无关用户不应该给这张工单补附件。',
            creator=self.creator,
        )
        upload_file = SimpleUploadedFile('error.log', b'log content', content_type='text/plain')
        self.client.force_authenticate(user=self.other_user)

        response = self.client.post(
            reverse('ticket-attachments', args=[ticket.id]),
            {'file': upload_file},
            format='multipart',
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(TicketAttachment.objects.exists())

    def test_ticket_attachment_size_limit(self):
        """附件超过 5MB 时返回 400，避免接口被大文件打满磁盘。"""

        ticket = Ticket.objects.create(
            title='附件大小限制工单',
            description='用于验证附件大小限制。',
            creator=self.creator,
        )
        oversized_file = SimpleUploadedFile(
            'too-large.log',
            b'x' * (5 * 1024 * 1024 + 1),
            content_type='text/plain',
        )
        self.client.force_authenticate(user=self.creator)

        response = self.client.post(
            reverse('ticket-attachments', args=[ticket.id]),
            {'file': oversized_file},
            format='multipart',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(TicketAttachment.objects.exists())

    def test_participant_can_create_and_list_ticket_comments(self):
        ticket = Ticket.objects.create(
            title='评论测试工单',
            description='验证工单评论和处理记录。',
            creator=self.creator,
            assignee=self.assignee,
        )
        self.client.force_authenticate(user=self.assignee)

        comments_url = reverse('ticket-comments', args=[ticket.id])
        create_response = self.client.post(
            comments_url,
            {
                'content': '已经开始排查网络配置。',
                'comment_type': TicketComment.CommentType.HANDLING,
            },
            format='json',
        )
        list_response = self.client.get(comments_url)

        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(create_response.data['author'], self.assignee.id)
        self.assertEqual(create_response.data['ticket'], ticket.id)
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(list_response.data['count'], 1)
        self.assertEqual(list_response.data['results'][0]['content'], '已经开始排查网络配置。')
        self.assertTrue(
            AuditLog.objects.filter(
                actor=self.assignee,
                action=AuditAction.COMMENT,
                target_type='Ticket',
                target_id=str(ticket.id),
            ).exists()
        )

    def test_comment_creates_notification_for_other_participant(self):
        """处理人新增评论后，创建人会收到评论通知。"""

        ticket = Ticket.objects.create(
            title='评论通知工单',
            description='验证评论会通知其他参与者。',
            creator=self.creator,
            assignee=self.assignee,
        )
        self.client.force_authenticate(user=self.assignee)

        response = self.client.post(
            reverse('ticket-comments', args=[ticket.id]),
            {
                'content': '我已经看到了这个问题，马上处理。',
                'comment_type': TicketComment.CommentType.COMMENT,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        notification = Notification.objects.get(
            recipient=self.creator,
            notification_type=NotificationType.TICKET_COMMENTED,
        )
        self.assertEqual(notification.target_id, str(ticket.id))
        self.assertEqual(notification.metadata['comment_id'], response.data['id'])

    def test_comment_creates_notification_for_watcher(self):
        """工单新增评论后，关注人会收到通知。"""

        watcher = User.objects.create_user(username='watcher_comment', password='TestPass123')
        ticket = Ticket.objects.create(
            title='关注人评论通知工单',
            description='验证评论会通知关注人。',
            creator=self.creator,
            assignee=self.assignee,
        )
        ticket.watchers.add(watcher)
        self.client.force_authenticate(user=self.assignee)

        response = self.client.post(
            reverse('ticket-comments', args=[ticket.id]),
            {
                'content': '这里新增一条给关注人的评论。',
                'comment_type': TicketComment.CommentType.COMMENT,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            Notification.objects.filter(
                recipient=watcher,
                notification_type=NotificationType.TICKET_COMMENTED,
            ).exists()
        )

    def test_unrelated_user_cannot_create_ticket_comment(self):
        ticket = Ticket.objects.create(
            title='无关用户不可评论工单',
            description='只有参与者才能写评论。',
            creator=self.creator,
        )
        self.client.force_authenticate(user=self.other_user)

        response = self.client.post(
            reverse('ticket-comments', args=[ticket.id]),
            {'content': '尝试写入无关评论。'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
