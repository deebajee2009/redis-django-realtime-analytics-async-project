"""
Polls app db models.
"""
from django.utils import timezone

from django.db import models


class Poll(models.Model):
    """
    Poll db model
    """
    question = models.CharField(max_length=255)
    text = models.JSONField()
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    def is_expired(self):
        return self.expires_at and timezone.now() > self.expires_at
    def __str__(self):
        return self.question
