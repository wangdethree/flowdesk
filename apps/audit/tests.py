from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.audit.models import AuditAction, AuditLog


User = get_user_model()


class AuditLogModelTests(TestCase):
    def test_create_audit_log(self):
        user = User.objects.create_user(username='audit_user', password='TestPass123')

        log = AuditLog.objects.create(
            actor=user,
            action=AuditAction.CREATE,
            target_type='ticket',
            target_id='1',
            description='创建工单',
            metadata={'title': '测试工单'},
        )

        self.assertEqual(log.actor, user)
        self.assertEqual(log.action, AuditAction.CREATE)
        self.assertEqual(log.metadata['title'], '测试工单')
        self.assertEqual(str(log), 'audit_user 创建 ticket#1')

    def test_audit_log_can_be_created_without_actor(self):
        log = AuditLog.objects.create(
            actor=None,
            action=AuditAction.UPDATE,
            target_type='ticket',
            target_id='1',
            description='系统更新工单',
        )

        self.assertEqual(str(log), '系统 更新 ticket#1')
