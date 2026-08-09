from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Category, ContentItem
from .serializers import CategorySerializer, ContentItemSerializer, ContentItemCreateSerializer


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet для просмотра категорий контента.
    """
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


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
        queryset = super().get_queryset()
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category__slug=category)
        return queryset.select_related('category')

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
