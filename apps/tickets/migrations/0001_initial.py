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
            name='Ticket',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=120, verbose_name='标题')),
                ('description', models.TextField(verbose_name='描述')),
                ('category', models.CharField(choices=[('bug', '故障问题'), ('feature', '功能需求'), ('consult', '咨询支持'), ('other', '其他')], default='other', max_length=20, verbose_name='分类')),
                ('priority', models.CharField(choices=[('low', '低'), ('medium', '中'), ('high', '高'), ('urgent', '紧急')], default='medium', max_length=20, verbose_name='优先级')),
                ('status', models.CharField(choices=[('open', '待处理'), ('in_progress', '处理中'), ('resolved', '已解决'), ('closed', '已关闭')], default='open', max_length=20, verbose_name='状态')),
                ('due_at', models.DateTimeField(blank=True, null=True, verbose_name='截止时间')),
                ('resolved_at', models.DateTimeField(blank=True, null=True, verbose_name='解决时间')),
                ('closed_at', models.DateTimeField(blank=True, null=True, verbose_name='关闭时间')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('assignee', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='assigned_tickets', to=settings.AUTH_USER_MODEL, verbose_name='处理人')),
                ('creator', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='created_tickets', to=settings.AUTH_USER_MODEL, verbose_name='创建人')),
            ],
            options={
                'verbose_name': '工单',
                'verbose_name_plural': '工单',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='TicketComment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('content', models.TextField(verbose_name='内容')),
                ('comment_type', models.CharField(choices=[('comment', '普通评论'), ('handling', '处理记录')], default='comment', max_length=20, verbose_name='记录类型')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('author', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ticket_comments', to=settings.AUTH_USER_MODEL, verbose_name='作者')),
                ('ticket', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='comments', to='tickets.ticket', verbose_name='所属工单')),
            ],
            options={
                'verbose_name': '工单记录',
                'verbose_name_plural': '工单记录',
                'ordering': ['created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='ticket',
            index=models.Index(fields=['status', 'priority', '-created_at'], name='tickets_tic_status_dc2200_idx'),
        ),
        migrations.AddIndex(
            model_name='ticket',
            index=models.Index(fields=['creator', '-created_at'], name='tickets_tic_creator_0ef914_idx'),
        ),
        migrations.AddIndex(
            model_name='ticket',
            index=models.Index(fields=['assignee', '-created_at'], name='tickets_tic_assigne_68e4f7_idx'),
        ),
        migrations.AddIndex(
            model_name='ticketcomment',
            index=models.Index(fields=['ticket', 'created_at'], name='tickets_tic_ticket__254c10_idx'),
        ),
        migrations.AddIndex(
            model_name='ticketcomment',
            index=models.Index(fields=['author', '-created_at'], name='tickets_tic_author__f11131_idx'),
        ),
    ]
