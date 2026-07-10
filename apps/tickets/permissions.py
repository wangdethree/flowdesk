from rest_framework import permissions


class IsTicketParticipantOrStaff(permissions.BasePermission):
    """工单对象权限。

    第一版先采用一个简单规则：
    - 管理员可以查看和修改所有工单。
    - 创建人可以查看、修改、删除自己的工单。
    - 处理人可以查看和处理分配给自己的工单，但不能删除工单。
    - 关注人可以查看工单，但不能修改工单。

    更复杂的角色权限会放到后续 Day 5 继续演进。
    """

    def has_object_permission(self, request, view, obj):
        # is_staff 是 Django 内置用户字段，通常用于表示后台管理员或内部管理人员。
        if request.user.is_staff:
            return True

        # SAFE_METHODS 包含 GET、HEAD、OPTIONS，表示“只读请求”。
        # 创建人、处理人和关注人都可以查看工单详情。
        if request.method in permissions.SAFE_METHODS:
            return (
                obj.creator_id == request.user.id
                or obj.assignee_id == request.user.id
                or obj.watchers.filter(id=request.user.id).exists()
            )

        # 删除工单属于比较危险的操作，普通用户里只允许创建人删除。
        if request.method == 'DELETE':
            return obj.creator_id == request.user.id

        # 非只读请求包括 PUT、PATCH、DELETE。
        # 创建人可以补充和调整工单，处理人可以更新处理状态和写处理记录。
        return obj.creator_id == request.user.id or obj.assignee_id == request.user.id
