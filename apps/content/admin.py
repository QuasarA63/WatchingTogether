from django.contrib import admin
from .models import Category, ContentItem


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'icon', 'created_at']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['name']


@admin.register(ContentItem)
class ContentItemAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'year', 'external_id', 'created_at']
    list_filter = ['category', 'year', 'created_at']
    search_fields = ['title', 'original_title', 'description', 'external_id']
    raw_id_fields = ['category']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('category', 'title', 'original_title', 'description', 'year')
        }),
        ('Медиа', {
            'fields': ('poster',)
        }),
        ('Внешние данные', {
            'fields': ('external_id', 'metadata'),
            'classes': ('collapse',)
        }),
    )
