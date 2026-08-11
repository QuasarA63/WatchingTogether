from rest_framework import serializers
from .models import Category, ContentItem, UserContentItem


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


class ContentItemSerializer(serializers.ModelSerializer):
    """
    Сериализатор для элемента контента.
    """
    category_name = serializers.CharField(source='category.name', read_only=True)
    reviews_count = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()

    class Meta:
        model = ContentItem
        fields = [
            'id', 'category', 'category_name', 'title', 'original_title',
            'description', 'year', 'poster', 'external_id', 'metadata',
            'reviews_count', 'average_rating', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_reviews_count(self, obj):
        return obj.reviews.count()

    def get_average_rating(self, obj):
        reviews = obj.reviews.all()
        if not reviews:
            return None
        return round(sum(r.rating for r in reviews) / len(reviews), 1)


class ContentItemCreateSerializer(serializers.ModelSerializer):
    """
    Сериализатор для создания элемента контента.
    """
    class Meta:
        model = ContentItem
        fields = [
            'category', 'title', 'original_title', 'description',
            'year', 'poster', 'external_id', 'metadata'
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

    class Meta:
        model = UserContentItem
        fields = ['id', 'content_item', 'content_item_id', 'comment', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
