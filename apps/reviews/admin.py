from django.contrib import admin
from .models import Review, Comment


class CommentInline(admin.TabularInline):
    model = Comment
    extra = 0
    raw_id_fields = ['user', 'parent']


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['user', 'content_item', 'group', 'rating', 'is_spoiler', 'created_at']
    list_filter = ['rating', 'is_spoiler', 'created_at', 'content_item__category']
    search_fields = ['user__username', 'content_item__title', 'title', 'text']
    raw_id_fields = ['user', 'content_item', 'group']
    inlines = [CommentInline]
    ordering = ['-created_at']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('user', 'content_item', 'group')
        }),
        ('Отзыв', {
            'fields': ('rating', 'title', 'text', 'is_spoiler')
        }),
    )


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['user', 'review', 'parent', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'review__title', 'text']
    raw_id_fields = ['review', 'user', 'parent']
    ordering = ['-created_at']
