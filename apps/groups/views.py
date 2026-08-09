from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from .models import Group, GroupMembership
from .serializers import GroupSerializer, GroupCreateSerializer, GroupMembershipSerializer


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
        if self.action in ['create', 'join', 'leave']:
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
        """Вступить в группу."""
        group = self.get_object()
        if GroupMembership.objects.filter(user=request.user, group=group).exists():
            return Response(
                {'detail': 'Вы уже являетесь участником этой группы.'},
                status=status.HTTP_400_BAD_REQUEST
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
