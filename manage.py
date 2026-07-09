#!/usr/bin/env python
"""Django 项目管理命令入口。"""
import os
import sys


def main():
    """执行 Django 管理命令。"""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "无法导入 Django。请确认依赖已经安装，并且当前命令运行在正确的虚拟环境中。"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
