from django.contrib import admin
from .models import Category, Genre, ContentItem, UserContentItem


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'icon', 'created_at']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['name']


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'created_at']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['name']


@admin.register(ContentItem)
class ContentItemAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'year', 'external_id', 'is_active', 'created_at']
    list_filter = ['category', 'genres', 'is_active', 'year', 'created_at']
    search_fields = ['title', 'original_title', 'description', 'external_id']
    raw_id_fields = ['category']
    filter_horizontal = ['genres']
    ordering = ['-created_at']

    fieldsets = (
        ('Основная информация', {
            'fields': ('category', 'title', 'original_title', 'description', 'year', 'genres')
        }),
        ('Медиа', {
            'fields': ('poster',)
        }),
        ('Внешние данные', {
            'fields': ('external_id', 'metadata'),
            'classes': ('collapse',)
        }),
        ('Статус', {
            'fields': ('is_active',)
        }),
    )


@admin.register(UserContentItem)
class UserContentItemAdmin(admin.ModelAdmin):
    list_display = ['user', 'content_item', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'content_item__title', 'comment']
    raw_id_fields = ['user', 'content_item']
    ordering = ['-created_at']
