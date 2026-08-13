from django.contrib import admin
from .models import Group, GroupMembership, GroupInvitation, GroupMessage


class GroupMembershipInline(admin.TabularInline):
    model = GroupMembership
    extra = 1
    raw_id_fields = ['user']


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ['name', 'owner', 'is_private', 'created_at']
    list_filter = ['is_private', 'created_at']
    search_fields = ['name', 'description', 'owner__username']
    raw_id_fields = ['owner']
    inlines = [GroupMembershipInline]
    ordering = ['-created_at']


@admin.register(GroupMembership)
class GroupMembershipAdmin(admin.ModelAdmin):
    list_display = ['user', 'group', 'role', 'joined_at']
    list_filter = ['role', 'joined_at']
    search_fields = ['user__username', 'group__name']
    raw_id_fields = ['user', 'group']
    ordering = ['-joined_at']


@admin.register(GroupInvitation)
class GroupInvitationAdmin(admin.ModelAdmin):
    list_display = ['group', 'from_user', 'to_user', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['group__name', 'from_user__username', 'to_user__username']
    raw_id_fields = ['group', 'from_user', 'to_user']
    ordering = ['-created_at']


@admin.register(GroupMessage)
class GroupMessageAdmin(admin.ModelAdmin):
    list_display = ['group', 'user', 'text', 'created_at']
    list_filter = ['created_at']
    search_fields = ['group__name', 'user__username', 'text']
    raw_id_fields = ['group', 'user']
    ordering = ['-created_at']
