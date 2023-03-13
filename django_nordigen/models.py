from datetime import timedelta

from django.db import models
from django.utils import timezone

TOKEN_GRACE_PERIOD = timedelta(seconds=10)


class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Integration(BaseModel):
    nordigen_id = models.UUIDField(unique=True)

    def __str__(self):
        return str(self.nordigen_id)

    def get_token(self, token_type):
        qs = self.token_set.filter(
            type=token_type,
            expires__gt=timezone.now() - TOKEN_GRACE_PERIOD,
        )
        return qs.first()

    def save_token(self, token_type, expires, value):
        token, _ = self.token_set.update_or_create(
            type=token_type,
            defaults=dict(
                expires=timezone.now() + timedelta(seconds=expires),
                value=value,
            ),
        )
        return token


class Token(BaseModel):
    class TokenType(models.TextChoices):
        REFRESH = 'refresh', 'Refresh token'
        ACCESS = 'access', 'Access token'

    integration = models.ForeignKey(Integration, on_delete=models.CASCADE)
    type = models.CharField(max_length=8, choices=TokenType.choices)
    expires = models.DateTimeField()
    value = models.TextField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['integration', 'type'],
                name='nordigen_unique_integration_type',
            ),
        ]

    def __str__(self):
        return f'{self.type} for {self.integration}'


class Institution(BaseModel):
    nordigen_id = models.CharField(max_length=100, unique=True)
    api_data = models.JSONField()

    def __str__(self):
        return self.name

    @property
    def name(self):
        return self.api_data['name']

    @property
    def logo(self):
        return self.api_data['logo']


class Requisition(BaseModel):
    integration = models.ForeignKey(Integration, on_delete=models.CASCADE)
    nordigen_id = models.UUIDField(unique=True)
    reference_id = models.UUIDField()
    completed = models.BooleanField(default=False)
    api_data = models.JSONField(null=True, blank=True)
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE)
    max_historical_days = models.PositiveSmallIntegerField()

    def __str__(self):
        return str(self.nordigen_id)


class Account(BaseModel):
    integration = models.ForeignKey(Integration, on_delete=models.CASCADE)
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE)
    nordigen_id = models.UUIDField(unique=True)
    api_data = models.JSONField()
    api_details = models.JSONField()
    requisitions = models.ManyToManyField(Requisition, blank=True)
    synced_at = models.DateTimeField(null=True)
    alias = models.CharField(max_length=1000, blank=True)

    class Meta:
        ordering = ['-synced_at']

    @property
    def currency(self):
        return self.api_details['account']['currency']

    @property
    def iban(self):
        return self.api_details['account'].get('iban')

    def __str__(self):
        return self.alias or self.iban or str(self.nordigen_id)


class Balance(BaseModel):
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    type = models.CharField(max_length=100)
    api_data = models.JSONField()
    synced_at = models.DateTimeField(null=True)

    def __str__(self):
        return f'{self.amount} {self.currency}'

    @property
    def amount(self):
        return self.api_data['balanceAmount']['amount']

    @property
    def currency(self):
        return self.api_data['balanceAmount']['currency']


class Transaction(BaseModel):
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    nordigen_id = models.CharField(max_length=32)
    api_data = models.JSONField()
    booking_date = models.DateField(null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['account', 'nordigen_id'],
                name='nordigen_unique_account_internal_id',
            ),
        ]
        ordering = ['-booking_date', '-pk']

    def __str__(self):
        return f'{self.amount} {self.currency}'

    @property
    def amount(self):
        return self.api_data['transactionAmount']['amount']

    @property
    def currency(self):
        return self.api_data['transactionAmount']['currency']
