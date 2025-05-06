from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Follow


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = (
        'id',
        'email',
        'username',
        'first_name',
        'last_name',
        'is_active',
    )
    search_fields = ('email', 'username', 'first_name', 'last_name')
    ordering = ('id',)


@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = ('follower', 'following')
    search_fields = ('follower__email', 'following__email')
    list_filter = ('follower',)
