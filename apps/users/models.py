from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.core.models import TimeStampedModel


class User(AbstractUser, TimeStampedModel):
    """
    Расширенная модель пользователя.
    """
    avatar = models.ImageField(
        upload_to='avatars/',
        blank=True,
        verbose_name=_('Аватар')
    )
    bio = models.TextField(
        blank=True,
        verbose_name=_('О себе')
    )

    class Meta:
        verbose_name = _('Пользователь')
        verbose_name_plural = _('Пользователи')
        ordering = ['-created_at']

    def __str__(self):
        return self.username
