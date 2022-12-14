from django.contrib import admin

from .models import Integration, Token


class NoAddChange:
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Integration)
class IntegrationAdmin(NoAddChange, admin.ModelAdmin):
    list_display = [
        'nordigen_id',
    ]


@admin.register(Token)
class TokenAdmin(NoAddChange, admin.ModelAdmin):
    list_display = [
        'integration',
        'type',
        'updated_at',
        'expires',
    ]

    exclude = [
        'value',
    ]
