from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Review, Comment
from .serializers import (
    ReviewSerializer, ReviewCreateSerializer, ReviewUpdateSerializer,
    CommentSerializer, CommentCreateSerializer
)


class ReviewViewSet(viewsets.ModelViewSet):
    """
    ViewSet для управления отзывами.
    """
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer

    def get_serializer_class(self):
        if self.action == 'create':
            return ReviewCreateSerializer
        if self.action == 'partial_update':
            return ReviewUpdateSerializer
        return ReviewSerializer

    def get_permissions(self):
        if self.action == 'create':
            return [IsAuthenticated()]
        return super().get_permissions()

    def create(self, request, *args, **kwargs):
        """Создание отзыва с возвратом полного объекта."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        review = serializer.save()
        output_serializer = ReviewSerializer(review)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)

    def get_queryset(self):
        queryset = super().get_queryset()
        content_item = self.request.query_params.get('content_item')
        group = self.request.query_params.get('group')
        user = self.request.query_params.get('user')

        if content_item:
            queryset = queryset.filter(content_item_id=content_item)
        if group:
            queryset = queryset.filter(group_id=group)
        if user:
            queryset = queryset.filter(user_id=user)

        return queryset.select_related('user', 'content_item', 'group')

    def partial_update(self, request, *args, **kwargs):
        """Только автор может редактировать отзыв."""
        review = self.get_object()
        if review.user != request.user:
            return Response(
                {'detail': 'Вы можете редактировать только свои отзывы.'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """Только автор может удалить отзыв."""
        review = self.get_object()
        if review.user != request.user:
            return Response(
                {'detail': 'Вы можете удалять только свои отзывы.'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=['get', 'post'])
    def comments(self, request, pk=None):
        """Получить или добавить комментарии к отзыву."""
        review = self.get_object()

        if request.method == 'GET':
            comments = review.comments.all().select_related('user')
            page = self.paginate_queryset(comments)
            if page is not None:
                serializer = CommentSerializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            serializer = CommentSerializer(comments, many=True)
            return Response(serializer.data)

        elif request.method == 'POST':
            if not request.user.is_authenticated:
                return Response(
                    {'detail': 'Необходима авторизация.'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            serializer = CommentCreateSerializer(
                data=request.data,
                context={'request': request, 'review_id': review.id}
            )
            serializer.is_valid(raise_exception=True)
            comment = serializer.save()
            output_serializer = CommentSerializer(comment)
            return Response(output_serializer.data, status=status.HTTP_201_CREATED)
