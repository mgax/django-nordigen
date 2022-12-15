from django.contrib import admin

from .models import Account, Institution, Integration, Requisition, Token


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
    ]


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
        'nordigen_id',
        'institution',
        'currency',
        'created_at',
    ]
