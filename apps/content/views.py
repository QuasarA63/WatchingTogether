from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Category, Genre, ContentItem, UserContentItem
from .serializers import (
    CategorySerializer,
    GenreSerializer,
    ContentItemSerializer,
    ContentItemCreateSerializer,
    UserContentItemSerializer,
)


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet для просмотра категорий контента.
    """
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class GenreViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet для просмотра жанров/стилей контента.
    """
    queryset = Genre.objects.all()
    serializer_class = GenreSerializer


class ContentItemViewSet(viewsets.ModelViewSet):
    """
    ViewSet для управления элементами контента.
    """
    queryset = ContentItem.objects.all()
    serializer_class = ContentItemSerializer
    http_method_names = ['get', 'post', 'patch', 'head', 'options']
    search_fields = ['title', 'original_title', 'description']
    ordering_fields = ['title', 'year', 'created_at']

    def get_serializer_class(self):
        if self.action == 'create':
            return ContentItemCreateSerializer
        return ContentItemSerializer

    def create(self, request, *args, **kwargs):
        """Создание контента с возвратом полного объекта."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        content_item = serializer.save()
        output_serializer = ContentItemSerializer(content_item)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)

    def get_permissions(self):
        if self.action == 'create':
            return [IsAuthenticated()]
        return super().get_permissions()

    def get_queryset(self):
        queryset = super().get_queryset().filter(is_active=True)
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category__slug=category)
        genre = self.request.query_params.get('genre')
        if genre:
            queryset = queryset.filter(genres__slug=genre)
        return queryset.select_related('category').prefetch_related('genres').distinct()

    @action(detail=True, methods=['get'])
    def reviews(self, request, pk=None):
        """Отзывы на элемент контента."""
        content_item = self.get_object()
        reviews = content_item.reviews.all()
        from apps.reviews.serializers import ReviewSerializer
        page = self.paginate_queryset(reviews)
        if page is not None:
            serializer = ReviewSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = ReviewSerializer(reviews, many=True)
        return Response(serializer.data)


class UserContentItemViewSet(viewsets.ModelViewSet):
    """
    ViewSet личных объектов пользователя.

    DELETE выполняет мягкое удаление: личная привязка удаляется,
    а сам объект помечается is_active=False, если к нему
    не привязаны другие пользователи и отзывы.
    """
    serializer_class = UserContentItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = UserContentItem.objects.filter(
            user=self.request.user,
            content_item__is_active=True,
        ).select_related('content_item', 'content_item__category').prefetch_related(
            'content_item__genres'
        )
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(content_item__category__slug=category)
        genre = self.request.query_params.get('genre')
        if genre:
            queryset = queryset.filter(content_item__genres__slug=genre)
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset.distinct()

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def destroy(self, request, *args, **kwargs):
        entry = self.get_object()
        content_item = entry.content_item
        entry.delete()

        has_other_entries = content_item.user_entries.exists()
        has_reviews = content_item.reviews.exists()
        if not has_other_entries and not has_reviews:
            content_item.is_active = False
            content_item.save(update_fields=['is_active', 'updated_at'])

        return Response(status=status.HTTP_204_NO_CONTENT)
