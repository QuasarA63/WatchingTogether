from rest_framework import serializers
from .models import Group, GroupMembership


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
