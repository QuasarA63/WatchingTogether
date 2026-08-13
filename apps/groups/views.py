from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db.models import Q
from .models import Group, GroupMembership, GroupInvitation, GroupMessage
from .serializers import (
    GroupSerializer, GroupCreateSerializer, GroupMembershipSerializer,
    GroupInvitationSerializer, GroupInvitationCreateSerializer,
    GroupMessageSerializer, GroupMessageCreateSerializer,
)
from apps.notifications.models import Notification


def _notify_invitation(invitation):
    """Создать уведомление о приглашении в группу."""
    Notification.objects.create(
        user=invitation.to_user,
        notification_type='group_invite',
        title=f'Приглашение в группу «{invitation.group.name}»',
        message=(
            f'{invitation.from_user.username} приглашает вас в группу '
            f'«{invitation.group.name}».'
            + (f'\n{invitation.message}' if invitation.message else '')
        ),
        link='/notifications/',
        invitation=invitation,
    )


class GroupViewSet(viewsets.ModelViewSet):
    """
    ViewSet для управления группами.
    """
    queryset = Group.objects.all()
    serializer_class = GroupSerializer

    def get_serializer_class(self):
        if self.action == 'create':
            return GroupCreateSerializer
        return GroupSerializer

    def create(self, request, *args, **kwargs):
        """Создание группы с возвратом полного объекта."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        group = serializer.save()
        output_serializer = GroupSerializer(group)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)

    def get_permissions(self):
        if self.action in ['create', 'join', 'leave', 'invite', 'messages']:
            return [IsAuthenticated()]
        return super().get_permissions()

    def partial_update(self, request, *args, **kwargs):
        """Только владелец или админ группы может её редактировать."""
        group = self.get_object()
        membership = GroupMembership.objects.filter(
            user=request.user, group=group, role__in=['owner', 'admin']
        ).first()
        if not membership:
            return Response(
                {'detail': 'Только владелец или администратор может редактировать группу.'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """Только владелец может удалить группу."""
        group = self.get_object()
        if group.owner != request.user:
            return Response(
                {'detail': 'Только владелец может удалить группу.'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def join(self, request, pk=None):
        """Вступить в группу. В приватную — только по приглашению."""
        group = self.get_object()
        if GroupMembership.objects.filter(user=request.user, group=group).exists():
            return Response(
                {'detail': 'Вы уже являетесь участником этой группы.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if group.is_private:
            return Response(
                {'detail': 'Вступление в приватную группу возможно только по приглашению.'},
                status=status.HTTP_403_FORBIDDEN
            )
        membership = GroupMembership.objects.create(
            user=request.user, group=group, role='member'
        )
        serializer = GroupMembershipSerializer(membership)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def leave(self, request, pk=None):
        """Покинуть группу."""
        group = self.get_object()
        membership = GroupMembership.objects.filter(user=request.user, group=group).first()
        if not membership:
            return Response(
                {'detail': 'Вы не являетесь участником этой группы.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if membership.role == 'owner':
            return Response(
                {'detail': 'Владелец не может покинуть группу. Передайте права или удалите группу.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        membership.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['get'])
    def members(self, request, pk=None):
        """Список участников группы."""
        group = self.get_object()
        memberships = GroupMembership.objects.filter(group=group).select_related('user')
        page = self.paginate_queryset(memberships)
        if page is not None:
            serializer = GroupMembershipSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = GroupMembershipSerializer(memberships, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def reviews(self, request, pk=None):
        """Отзывы группы."""
        group = self.get_object()
        reviews = group.reviews.all()
        from apps.reviews.serializers import ReviewSerializer
        page = self.paginate_queryset(reviews)
        if page is not None:
            serializer = ReviewSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = ReviewSerializer(reviews, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def invite(self, request, pk=None):
        """Пригласить пользователя в группу (владелец/админ)."""
        group = self.get_object()
        membership = GroupMembership.objects.filter(
            user=request.user, group=group, role__in=['owner', 'admin']
        ).first()
        if not membership:
            return Response(
                {'detail': 'Приглашать могут только владелец или администратор группы.'},
                status=status.HTTP_403_FORBIDDEN
            )
        serializer = GroupInvitationCreateSerializer(
            data=request.data,
            context={'request': request, 'group': group}
        )
        serializer.is_valid(raise_exception=True)
        invitation = serializer.save()
        _notify_invitation(invitation)
        return Response(
            GroupInvitationSerializer(invitation).data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def invitations(self, request, pk=None):
        """Приглашения группы (владелец/админ)."""
        group = self.get_object()
        membership = GroupMembership.objects.filter(
            user=request.user, group=group, role__in=['owner', 'admin']
        ).first()
        if not membership:
            return Response(
                {'detail': 'Просматривать приглашения могут только владелец или администратор.'},
                status=status.HTTP_403_FORBIDDEN
            )
        invitations = group.invitations.select_related('from_user', 'to_user')
        invitation_status = request.query_params.get('status')
        if invitation_status:
            invitations = invitations.filter(status=invitation_status)
        page = self.paginate_queryset(invitations)
        if page is not None:
            serializer = GroupInvitationSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = GroupInvitationSerializer(invitations, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get', 'post'], permission_classes=[IsAuthenticated])
    def messages(self, request, pk=None):
        """Сообщения группового чата (только участники). GET поддерживает ?after_id=."""
        group = self.get_object()
        if not GroupMembership.objects.filter(user=request.user, group=group).exists():
            return Response(
                {'detail': 'Чат доступен только участникам группы.'},
                status=status.HTTP_403_FORBIDDEN
            )

        if request.method == 'POST':
            serializer = GroupMessageCreateSerializer(
                data=request.data,
                context={'request': request, 'group': group}
            )
            serializer.is_valid(raise_exception=True)
            message = serializer.save()
            return Response(
                GroupMessageSerializer(message).data,
                status=status.HTTP_201_CREATED
            )

        messages_qs = group.messages.select_related('user')
        after_id = request.query_params.get('after_id')
        if after_id and after_id.isdigit():
            messages_qs = messages_qs.filter(id__gt=int(after_id)).order_by('id')
            serializer = GroupMessageSerializer(messages_qs[:100], many=True)
            return Response(serializer.data)
        page = self.paginate_queryset(messages_qs)
        if page is not None:
            serializer = GroupMessageSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = GroupMessageSerializer(messages_qs, many=True)
        return Response(serializer.data)


class GroupInvitationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet приглашений текущего пользователя (входящие и исходящие).
    """
    serializer_class = GroupInvitationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = GroupInvitation.objects.filter(
            Q(to_user=self.request.user) | Q(from_user=self.request.user)
        ).select_related('group', 'from_user', 'to_user')
        invitation_status = self.request.query_params.get('status')
        if invitation_status:
            qs = qs.filter(status=invitation_status)
        return qs

    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        """Принять приглашение (только получатель)."""
        invitation = self.get_object()
        if invitation.to_user != request.user:
            return Response(
                {'detail': 'Принять приглашение может только его получатель.'},
                status=status.HTTP_403_FORBIDDEN
            )
        if invitation.status != 'pending':
            return Response(
                {'detail': 'Приглашение уже обработано.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        invitation.status = 'accepted'
        invitation.save(update_fields=['status', 'updated_at'])
        GroupMembership.objects.get_or_create(
            user=request.user, group=invitation.group, defaults={'role': 'member'}
        )
        Notification.objects.filter(invitation=invitation, user=request.user).update(is_read=True)
        Notification.objects.create(
            user=invitation.from_user,
            notification_type='group_invite_accepted',
            title=f'{request.user.username} принял приглашение',
            message=f'{request.user.username} вступил в группу «{invitation.group.name}».',
            link=f'/groups/{invitation.group.pk}/',
        )
        return Response(GroupInvitationSerializer(invitation).data)

    @action(detail=True, methods=['post'])
    def decline(self, request, pk=None):
        """Отклонить приглашение (только получатель)."""
        invitation = self.get_object()
        if invitation.to_user != request.user:
            return Response(
                {'detail': 'Отклонить приглашение может только его получатель.'},
                status=status.HTTP_403_FORBIDDEN
            )
        if invitation.status != 'pending':
            return Response(
                {'detail': 'Приглашение уже обработано.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        invitation.status = 'declined'
        invitation.save(update_fields=['status', 'updated_at'])
        Notification.objects.filter(invitation=invitation, user=request.user).update(is_read=True)
        Notification.objects.create(
            user=invitation.from_user,
            notification_type='group_invite_declined',
            title=f'{request.user.username} отклонил приглашение',
            message=f'{request.user.username} отклонил приглашение в группу «{invitation.group.name}».',
            link=f'/groups/{invitation.group.pk}/',
        )
        return Response(GroupInvitationSerializer(invitation).data)
