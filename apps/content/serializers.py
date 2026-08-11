from rest_framework import serializers
from .models import Category, Genre, ContentItem, UserContentItem


class CategorySerializer(serializers.ModelSerializer):
    """
    Сериализатор для категории контента.
    """
    items_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description', 'icon', 'items_count', 'created_at']
        read_only_fields = ['id', 'created_at']

    def get_items_count(self, obj):
        return obj.items.count()


class GenreSerializer(serializers.ModelSerializer):
    """
    Сериализатор для жанра/стиля контента.
    """
    items_count = serializers.SerializerMethodField()

    class Meta:
        model = Genre
        fields = ['id', 'name', 'slug', 'items_count', 'created_at']
        read_only_fields = ['id', 'created_at']

    def get_items_count(self, obj):
        return obj.items.count()


class ContentItemSerializer(serializers.ModelSerializer):
    """
    Сериализатор для элемента контента.
    """
    category_name = serializers.CharField(source='category.name', read_only=True)
    genres = GenreSerializer(many=True, read_only=True)
    genre_ids = serializers.PrimaryKeyRelatedField(
        queryset=Genre.objects.all(),
        source='genres',
        many=True,
        write_only=True,
        required=False
    )
    reviews_count = serializers.SerializerMethodField()

    class Meta:
        model = ContentItem
        fields = [
            'id', 'category', 'category_name', 'title', 'original_title',
            'description', 'year', 'poster', 'external_id', 'metadata',
            'external_rating', 'genres', 'genre_ids',
            'reviews_count', 'average_rating', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_reviews_count(self, obj):
        return obj.reviews.count()


class ContentItemCreateSerializer(serializers.ModelSerializer):
    """
    Сериализатор для создания элемента контента.
    """
    genre_ids = serializers.PrimaryKeyRelatedField(
        queryset=Genre.objects.all(),
        source='genres',
        many=True,
        required=False
    )

    class Meta:
        model = ContentItem
        fields = [
            'category', 'title', 'original_title', 'description',
            'year', 'poster', 'external_id', 'metadata', 'external_rating', 'genre_ids'
        ]


class UserContentItemSerializer(serializers.ModelSerializer):
    """
    Сериализатор личного объекта пользователя.
    """
    content_item = ContentItemSerializer(read_only=True)
    content_item_id = serializers.PrimaryKeyRelatedField(
        queryset=ContentItem.objects.filter(is_active=True),
        source='content_item',
        write_only=True
    )
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = UserContentItem
        fields = ['id', 'content_item', 'content_item_id', 'status', 'status_display', 'personal_rating', 'comment', 'is_public', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
