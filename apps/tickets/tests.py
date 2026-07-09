from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.audit.models import AuditAction, AuditLog
from apps.tickets.models import Ticket, TicketCategory, TicketComment, TicketPriority, TicketStatus


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
