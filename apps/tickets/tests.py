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
    TicketPriority,
    TicketStatus,
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
