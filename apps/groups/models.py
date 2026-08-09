from django.db import models
from django.conf import settings
from apps.core.models import TimeStampedModel


class Group(TimeStampedModel):
    """
    Группа для обсуждения контента.
    """
    name = models.CharField(
        max_length=255,
        verbose_name='Название'
    )
    description = models.TextField(
        blank=True,
        verbose_name='Описание'
    )
    avatar = models.ImageField(
        upload_to='group_avatars/',
        blank=True,
        verbose_name='Аватар группы'
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='owned_groups',
        verbose_name='Владелец'
    )
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through='GroupMembership',
        related_name='member_groups',
        verbose_name='Участники'
    )
    is_private = models.BooleanField(
        default=False,
        verbose_name='Приватная группа'
    )

    class Meta:
        verbose_name = 'Группа'
        verbose_name_plural = 'Группы'
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class GroupMembership(TimeStampedModel):
    """
    Членство пользователя в группе.
    """
    ROLE_CHOICES = [
        ('owner', 'Владелец'),
        ('admin', 'Администратор'),
        ('member', 'Участник'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name='Пользователь'
    )
    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        verbose_name='Группа'
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='member',
        verbose_name='Роль'
    )
    joined_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата вступления'
    )

    class Meta:
        verbose_name = 'Членство в группе'
        verbose_name_plural = 'Членство в группах'
        unique_together = ['user', 'group']
        ordering = ['-joined_at']

    def __str__(self):
        return f'{self.user.username} в {self.group.name} ({self.get_role_display()})'
