from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import UserProfile, UserSubscription


@admin.register(UserProfile)
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


@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):

    list_display = ('subscriber', 'author')
    search_fields = ('subscriber__email', 'author__email')
    list_filter = ('subscriber',)
