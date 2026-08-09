from django.contrib.auth.models import AbstractUser
from django.db import models
from apps.core.models import TimeStampedModel


class User(AbstractUser, TimeStampedModel):
    """
    Расширенная модель пользователя.
    """
    avatar = models.ImageField(
        upload_to='avatars/',
        blank=True,
        verbose_name='Аватар'
    )
    bio = models.TextField(
        blank=True,
        verbose_name='О себе'
    )

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ['-created_at']

    def __str__(self):
        return self.username
