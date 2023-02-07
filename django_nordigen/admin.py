from django.contrib import admin
from django.db import models
from django.urls import reverse
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


class BaseAdmin(admin.ModelAdmin):
    readonly_fields = [
        'created_at',
        'updated_at',
    ]


@admin.register(Integration)
class IntegrationAdmin(NoAddChange, BaseAdmin):
    list_display = [
        'nordigen_id',
    ]


@admin.register(Token)
class TokenAdmin(NoAddChange, BaseAdmin):
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
class InstitutionAdmin(NoAddChange, BaseAdmin):
    list_display = [
        'nordigen_id',
        'name',
        'logo_image',
    ]

    def logo_image(self, obj):
        return format_html('<img width=30 src="{}">', obj.logo)


@admin.register(Requisition)
class RequisitionAdmin(NoAddChange, BaseAdmin):
    list_display = [
        'nordigen_id',
        'institution',
        'created_at',
    ]


@admin.register(Account)
class AccountAdmin(NoAddChange, BaseAdmin):
    list_display = [
        '__str__',
        'currency',
        'transactions',
        'institution',
        'synced_at',
    ]

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.annotate(transaction_count=models.Count('transaction'))

    def transactions(self, obj):
        return format_html(
            '<a href="{}?account_id={}">{}</a>',
            reverse('admin:django_nordigen_transaction_changelist'),
            obj.pk,
            obj.transaction_count,
        )


@admin.register(Balance)
class BalanceAdmin(NoAddChange, BaseAdmin):
    list_display = [
        '__str__',
        'account',
        'synced_at',
    ]


@admin.register(Transaction)
class TransactionAdmin(NoAddChange, BaseAdmin):
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
