"""
CMS & Site Settings (DB Redesign doc, Section 3.12).

`Banner` merges the legacy `banners` and `sidebar_banners` (same concept,
two placements) into one table with a `placement` column. `EmailTemplate`
replaces `email_contents`, adding an explicit `is_active` flag. `Setting`
replaces `others`' three fixed value1/value2/value3 columns with a proper
key -> JSON value store.
"""

from django.db import models

from apps.core.models import AuditedModel


class Banner(AuditedModel):
    class Placement(models.TextChoices):
        HERO = "hero", "Hero"
        SIDEBAR = "sidebar", "Sidebar"
        CATEGORY = "category", "Category"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"

    placement = models.CharField(max_length=10, choices=Placement.choices)
    heading = models.CharField(max_length=255, null=True, blank=True)
    small_heading = models.CharField(db_column="smallHeading", max_length=255, null=True, blank=True)
    link_url = models.CharField(db_column="linkUrl", max_length=500, null=True, blank=True)
    image_path = models.CharField(db_column="imagePath", max_length=255, null=True, blank=True)
    image_url = models.URLField(db_column="imageUrl", max_length=500, null=True, blank=True)
    # Sidebar placement only.
    category = models.ForeignKey(
        "catalog.Category", on_delete=models.SET_NULL, null=True, blank=True, related_name="banners",
        db_column="categoryId",
    )
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    sort_order = models.IntegerField(db_column="sortOrder", default=0)
    starts_at = models.DateTimeField(db_column="startsAt", null=True, blank=True)
    ends_at = models.DateTimeField(db_column="endsAt", null=True, blank=True)

    class Meta:
        db_table = "banners"
        ordering = ["placement", "sort_order"]

    def __str__(self):
        return self.heading or f"Banner #{self.pk}"


class EmailTemplate(AuditedModel):
    key = models.CharField(max_length=100, unique=True)
    subject = models.CharField(max_length=255)
    content = models.TextField()
    is_active = models.BooleanField(db_column="isActive", default=True)

    class Meta:
        db_table = "emailTemplates"
        ordering = ["key"]

    def __str__(self):
        return self.key


class Setting(AuditedModel):
    """Keyed by a stable string, not an auto-incrementing id — see DB
    Redesign doc Section 3.12."""

    key = models.CharField(max_length=100, primary_key=True)
    value = models.JSONField()

    class Meta:
        db_table = "settings"
        ordering = ["key"]

    def __str__(self):
        return self.key
