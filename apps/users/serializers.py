from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.conf import settings
from .models import User
from apps.core.turnstile import verify_turnstile


class UserSerializer(serializers.ModelSerializer):
    """
    Сериализатор для отображения профиля пользователя.
    """
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'avatar', 'bio', 'created_at']
        read_only_fields = ['id', 'created_at']


class UserUpdateSerializer(serializers.ModelSerializer):
    """
    Сериализатор для обновления профиля пользователя.
    """
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'avatar', 'bio']


class AccountUpdateSerializer(serializers.ModelSerializer):
    """
    Сериализатор для обновления учётных данных (логин, email, пароль).
    """
    new_password = serializers.CharField(
        write_only=True,
        required=False,
        validators=[validate_password],
        style={'input_type': 'password'},
        label='Новый пароль'
    )
    password_confirm = serializers.CharField(
        write_only=True,
        required=False,
        style={'input_type': 'password'},
        label='Подтверждение пароля'
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'new_password', 'password_confirm']

    def validate(self, attrs):
        new_password = attrs.get('new_password')
        password_confirm = attrs.get('password_confirm')

        if new_password or password_confirm:
            if new_password != password_confirm:
                raise serializers.ValidationError({
                    'password_confirm': 'Пароли не совпадают.'
                })

        return attrs

    def update(self, instance, validated_data):
        new_password = validated_data.pop('new_password', None)
        validated_data.pop('password_confirm', None)

        instance = super().update(instance, validated_data)

        if new_password:
            instance.set_password(new_password)
            instance.save()

        return instance


class RegisterSerializer(serializers.ModelSerializer):
    """
    Сериализатор для регистрации нового пользователя.
    """
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'},
        label='Пароль'
    )
    password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        label='Подтверждение пароля'
    )
    turnstile_token = serializers.CharField(
        write_only=True,
        required=False,
        label='Turnstile токен'
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password_confirm', 'turnstile_token']

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({
                'password_confirm': 'Пароли не совпадают.'
            })
        if settings.TURNSTILE_ENABLED:
            token = attrs.get('turnstile_token', '')
            if not verify_turnstile(token):
                raise serializers.ValidationError({
                    'turnstile_token': 'Проверка защиты от ботов не пройдена.'
                })
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        validated_data.pop('turnstile_token', None)
        user = User.objects.create_user(**validated_data)
        return user
