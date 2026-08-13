from rest_framework import serializers
from .models import Group, GroupMembership, GroupInvitation, GroupMessage, GroupContentComment


class GroupMembershipSerializer(serializers.ModelSerializer):
    """
    Сериализатор для отображения членства в группе.
    """
    username = serializers.CharField(source='user.username', read_only=True)
    avatar = serializers.ImageField(source='user.avatar', read_only=True)

    class Meta:
        model = GroupMembership
        fields = ['id', 'user', 'username', 'avatar', 'role', 'joined_at']
        read_only_fields = ['id', 'joined_at']


class GroupSerializer(serializers.ModelSerializer):
    """
    Сериализатор для отображения группы.
    """
    owner_username = serializers.CharField(source='owner.username', read_only=True)
    members_count = serializers.SerializerMethodField()

    class Meta:
        model = Group
        fields = [
            'id', 'name', 'description', 'avatar', 'owner', 'owner_username',
            'is_private', 'members_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'owner', 'created_at', 'updated_at']

    def get_members_count(self, obj):
        return obj.members.count()


class GroupCreateSerializer(serializers.ModelSerializer):
    """
    Сериализатор для создания группы.
    """
    class Meta:
        model = Group
        fields = ['name', 'description', 'avatar', 'is_private']

    def create(self, validated_data):
        user = self.context['request'].user
        group = Group.objects.create(owner=user, **validated_data)
        # Автоматически добавляем владельца как участника с ролью owner
        GroupMembership.objects.create(user=user, group=group, role='owner')
        return group


class GroupInvitationSerializer(serializers.ModelSerializer):
    """
    Сериализатор приглашения в группу.
    """
    group_name = serializers.CharField(source='group.name', read_only=True)
    from_username = serializers.CharField(source='from_user.username', read_only=True)
    to_username = serializers.CharField(source='to_user.username', read_only=True)

    class Meta:
        model = GroupInvitation
        fields = [
            'id', 'group', 'group_name', 'from_user', 'from_username',
            'to_user', 'to_username', 'status', 'message', 'created_at'
        ]
        read_only_fields = ['id', 'group', 'from_user', 'to_user', 'status', 'created_at']


class GroupInvitationCreateSerializer(serializers.ModelSerializer):
    """
    Сериализатор создания приглашения (to_user + message).
    """
    class Meta:
        model = GroupInvitation
        fields = ['to_user', 'message']

    def validate_to_user(self, value):
        group = self.context['group']
        if GroupMembership.objects.filter(user=value, group=group).exists():
            raise serializers.ValidationError('Пользователь уже является участником группы.')
        if GroupInvitation.objects.filter(group=group, to_user=value, status='pending').exists():
            raise serializers.ValidationError('Пользователю уже отправлено приглашение.')
        return value

    def create(self, validated_data):
        return GroupInvitation.objects.create(
            group=self.context['group'],
            from_user=self.context['request'].user,
            **validated_data
        )


class GroupMessageSerializer(serializers.ModelSerializer):
    """
    Сериализатор сообщения группового чата.
    """
    username = serializers.CharField(source='user.username', read_only=True)
    avatar = serializers.ImageField(source='user.avatar', read_only=True)

    class Meta:
        model = GroupMessage
        fields = ['id', 'user', 'username', 'avatar', 'text', 'created_at']
        read_only_fields = ['id', 'user', 'created_at']


class GroupMessageCreateSerializer(serializers.ModelSerializer):
    """
    Сериализатор создания сообщения чата.
    """
    class Meta:
        model = GroupMessage
        fields = ['text']

    def create(self, validated_data):
        return GroupMessage.objects.create(
            group=self.context['group'],
            user=self.context['request'].user,
            **validated_data
        )


class GroupContentCommentReplySerializer(serializers.ModelSerializer):
    """
    Сериализатор ответа на комментарий обсуждения (без дальнейшей вложенности).
    """
    username = serializers.CharField(source='user.username', read_only=True)
    avatar = serializers.ImageField(source='user.avatar', read_only=True)

    class Meta:
        model = GroupContentComment
        fields = ['id', 'user', 'username', 'avatar', 'text', 'parent', 'created_at']
        read_only_fields = fields


class GroupContentCommentSerializer(serializers.ModelSerializer):
    """
    Сериализатор комментария обсуждения с вложенными ответами.
    """
    username = serializers.CharField(source='user.username', read_only=True)
    avatar = serializers.ImageField(source='user.avatar', read_only=True)
    replies = GroupContentCommentReplySerializer(many=True, read_only=True)

    class Meta:
        model = GroupContentComment
        fields = ['id', 'user', 'username', 'avatar', 'text', 'parent', 'replies', 'created_at']
        read_only_fields = fields


class GroupContentCommentCreateSerializer(serializers.ModelSerializer):
    """
    Сериализатор создания комментария обсуждения.
    """
    class Meta:
        model = GroupContentComment
        fields = ['text', 'parent']

    def validate_parent(self, value):
        if value is not None:
            group = self.context['group']
            content_item = self.context['content_item']
            if value.group_id != group.id or value.content_item_id != content_item.id:
                raise serializers.ValidationError(
                    'Родительский комментарий не относится к этому обсуждению.'
                )
        return value

    def create(self, validated_data):
        return GroupContentComment.objects.create(
            group=self.context['group'],
            content_item=self.context['content_item'],
            user=self.context['request'].user,
            **validated_data
        )
