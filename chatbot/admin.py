from django.contrib import admin
from .models import BanditArm, ChatLog


@admin.register(BanditArm)
class BanditArmAdmin(admin.ModelAdmin):
    list_display = ('context', 'action', 'count', 'avg_reward')
    ordering = ('context', '-avg_reward')


@admin.register(ChatLog)
class ChatLogAdmin(admin.ModelAdmin):
    list_display = ('session_key', 'role', 'message', 'created_at')
    list_filter = ('role',)
    search_fields = ('session_key', 'message')
