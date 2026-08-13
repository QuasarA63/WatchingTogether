from django.db import models
from django.conf import settings
from apps.core.models import TimeStampedModel


class GroupInvitation(TimeStampedModel):
    """
    Приглашение пользователя в группу.
    """
    STATUS_CHOICES = [
        ('pending', 'Ожидает ответа'),
        ('accepted', 'Принято'),
        ('declined', 'Отклонено'),
    ]

    group = models.ForeignKey(
        'Group',
        on_delete=models.CASCADE,
        related_name='invitations',
        verbose_name='Группа'
    )
    from_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_group_invitations',
        verbose_name='Кто пригласил'
    )
    to_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='received_group_invitations',
        verbose_name='Кого пригласили'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='Статус'
    )
    message = models.TextField(
        blank=True,
        verbose_name='Сообщение'
    )

    class Meta:
        verbose_name = 'Приглашение в группу'
        verbose_name_plural = 'Приглашения в группы'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['group', 'to_user'],
                condition=models.Q(status='pending'),
                name='unique_pending_group_invitation'
            )
        ]

    def __str__(self):
        return f'{self.from_user.username} → {self.to_user.username} в {self.group.name} ({self.get_status_display()})'


class GroupMessage(TimeStampedModel):
    """
    Сообщение в групповом чате.
    """
    group = models.ForeignKey(
        'Group',
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name='Группа'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='group_messages',
        verbose_name='Автор'
    )
    text = models.TextField(
        max_length=2000,
        verbose_name='Текст сообщения'
    )

    class Meta:
        verbose_name = 'Сообщение группы'
        verbose_name_plural = 'Сообщения групп'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['group', 'id']),
        ]

    def __str__(self):
        return f'{self.user.username} в {self.group.name}: {self.text[:50]}'


class GroupContentComment(TimeStampedModel):
    """
    Комментарий к обсуждению объекта контента внутри группы (с вложенностью).
    """
    group = models.ForeignKey(
        'Group',
        on_delete=models.CASCADE,
        related_name='content_comments',
        verbose_name='Группа'
    )
    content_item = models.ForeignKey(
        'content.ContentItem',
        on_delete=models.CASCADE,
        related_name='group_comments',
        verbose_name='Элемент контента'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='group_content_comments',
        verbose_name='Автор'
    )
    text = models.TextField(
        max_length=2000,
        verbose_name='Текст комментария'
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='replies',
        verbose_name='Родительский комментарий'
    )

    class Meta:
        verbose_name = 'Комментарий обсуждения'
        verbose_name_plural = 'Комментарии обсуждений'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['group', 'content_item']),
        ]

    def __str__(self):
        return f'{self.user.username} о {self.content_item.title} в {self.group.name}: {self.text[:50]}'


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
