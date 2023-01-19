from django.contrib import admin
from django.utils.html import format_html

from .models import (
    Account,
    Balance,
    Institution,
    Integration,
    Requisition,
    Token,
    Transaction
)


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


@admin.register(Institution)
class InstitutionAdmin(NoAddChange, admin.ModelAdmin):
    list_display = [
        'nordigen_id',
        'name',
        'logo_image',
    ]

    def logo_image(self, obj):
        return format_html('<img width=30 src="{}">', obj.logo)


@admin.register(Requisition)
class RequisitionAdmin(NoAddChange, admin.ModelAdmin):
    list_display = [
        'nordigen_id',
        'institution',
        'created_at',
    ]


@admin.register(Account)
class AccountAdmin(NoAddChange, admin.ModelAdmin):
    list_display = [
        '__str__',
        'currency',
        'institution',
        'synced_at',
    ]


@admin.register(Balance)
class BalanceAdmin(NoAddChange, admin.ModelAdmin):
    list_display = [
        '__str__',
        'account',
        'synced_at',
    ]


@admin.register(Transaction)
class TransactionAdmin(NoAddChange, admin.ModelAdmin):
    search_fields = [
        'api_data',
    ]

    date_hierarchy = 'booking_date'

    list_display = [
        '__str__',
        'booking_date',
        'account',
    ]

    list_filter = [
        'account',
    ]
