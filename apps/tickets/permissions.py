from rest_framework import permissions


class IsTicketParticipantOrStaff(permissions.BasePermission):
    """工单对象权限。

    第一版先采用一个简单规则：
    - 管理员可以查看和修改所有工单。
    - 创建人可以查看、修改、删除自己的工单。
    - 处理人可以查看分配给自己的工单。

    更复杂的角色权限会放到后续 Day 5 继续演进。
    """

    def has_object_permission(self, request, view, obj):
        # is_staff 是 Django 内置用户字段，通常用于表示后台管理员或内部管理人员。
        if request.user.is_staff:
            return True

        # SAFE_METHODS 包含 GET、HEAD、OPTIONS，表示“只读请求”。
        # 创建人和处理人都可以查看工单详情，但不能都修改。
        if request.method in permissions.SAFE_METHODS:
            return obj.creator_id == request.user.id or obj.assignee_id == request.user.id

        # 非只读请求包括 PUT、PATCH、DELETE。
        # 第一版先限制只有创建人可以修改或删除自己的工单。
        return obj.creator_id == request.user.id
