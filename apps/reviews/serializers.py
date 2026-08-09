from rest_framework import serializers
from .models import Review, Comment


class CommentSerializer(serializers.ModelSerializer):
    """
    Сериализатор для комментария к отзыву.
    """
    username = serializers.CharField(source='user.username', read_only=True)
    avatar = serializers.ImageField(source='user.avatar', read_only=True)

    class Meta:
        model = Comment
        fields = ['id', 'review', 'user', 'username', 'avatar', 'text', 'parent', 'created_at']
        read_only_fields = ['id', 'user', 'created_at']


class CommentCreateSerializer(serializers.ModelSerializer):
    """
    Сериализатор для создания комментария.
    """
    class Meta:
        model = Comment
        fields = ['text', 'parent']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        validated_data['review_id'] = self.context['review_id']
        return super().create(validated_data)


class ReviewSerializer(serializers.ModelSerializer):
    """
    Сериализатор для отображения отзыва.
    """
    username = serializers.CharField(source='user.username', read_only=True)
    avatar = serializers.ImageField(source='user.avatar', read_only=True)
    content_title = serializers.CharField(source='content_item.title', read_only=True)
    group_name = serializers.CharField(source='group.name', read_only=True, default=None)
    comments_count = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = [
            'id', 'user', 'username', 'avatar', 'content_item', 'content_title',
            'group', 'group_name', 'rating', 'title', 'text', 'is_spoiler',
            'comments_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']

    def get_comments_count(self, obj):
        return obj.comments.count()


class ReviewCreateSerializer(serializers.ModelSerializer):
    """
    Сериализатор для создания отзыва.
    """
    class Meta:
        model = Review
        fields = ['content_item', 'group', 'rating', 'title', 'text', 'is_spoiler']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class ReviewUpdateSerializer(serializers.ModelSerializer):
    """
    Сериализатор для обновления отзыва.
    """
    class Meta:
        model = Review
        fields = ['rating', 'title', 'text', 'is_spoiler']
