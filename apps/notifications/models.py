"""
Notifications (DB Redesign doc, Section 3.11).

Laravel's standard polymorphic notifications table, kept exactly as-is —
including its snake_case column names — since this table is framework-owned
and written exclusively by the framework itself. It deliberately does NOT
carry the createdBy/creatorType audit block used everywhere else: the doc
notes there is no ambiguity to resolve, since the actor is always "system".
"""

import uuid

from django.db import models


class Notification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    notifiable_type = models.CharField(max_length=255)
    notifiable_id = models.BigIntegerField()
    type = models.CharField(max_length=255)
    data = models.TextField()
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "notifications"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["notifiable_type", "notifiable_id"], name="notif_notifiable_idx"),
        ]

    def __str__(self):
        return f"{self.type} -> {self.notifiable_type}#{self.notifiable_id}"
