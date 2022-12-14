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
    nordigen_id = models.UUIDField()

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
