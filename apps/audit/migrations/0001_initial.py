# 由 Django 5.2.16 于 2026-07-09 生成。

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AuditLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(choices=[('create', '创建'), ('update', '更新'), ('delete', '删除'), ('comment', '评论'), ('status_change', '状态流转')], max_length=30, verbose_name='动作')),
                ('target_type', models.CharField(max_length=80, verbose_name='目标类型')),
                ('target_id', models.CharField(max_length=80, verbose_name='目标 ID')),
                ('description', models.CharField(max_length=255, verbose_name='描述')),
                ('metadata', models.JSONField(blank=True, default=dict, verbose_name='扩展数据')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('actor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='audit_logs', to=settings.AUTH_USER_MODEL, verbose_name='操作人')),
            ],
            options={
                'verbose_name': '审计日志',
                'verbose_name_plural': '审计日志',
                'ordering': ['-created_at'],
                'indexes': [models.Index(fields=['target_type', 'target_id', '-created_at'], name='audit_audit_target__edb7ad_idx'), models.Index(fields=['actor', '-created_at'], name='audit_audit_actor_i_1175ab_idx'), models.Index(fields=['action', '-created_at'], name='audit_audit_action_0c6a84_idx')],
            },
        ),
    ]
