from django.db import models


class ActorType(models.TextChoices):
    ADMIN = "admin", "Admin"
    SELLER = "seller", "Seller"
    USER = "user", "User"
    SYSTEM = "system", "System"


class AuditedModel(models.Model):
    """
    Shared created-by/updated-by audit trail used by every table in the
    Database Redesign document (Section 3). `created_by`/`updated_by` are
    plain ids (not FKs) because they can point into admins, sellers, or
    users depending on the paired *_type column.
    """

    created_by = models.BigIntegerField(db_column="createdBy", null=True, blank=True)
    creator_type = models.CharField(
        db_column="creatorType", max_length=10, choices=ActorType.choices, default=ActorType.SYSTEM
    )
    creator_name = models.CharField(db_column="creatorName", max_length=255, null=True, blank=True)

    updated_by = models.BigIntegerField(db_column="updatedBy", null=True, blank=True)
    updater_type = models.CharField(
        db_column="updaterType", max_length=10, choices=ActorType.choices, null=True, blank=True
    )
    updater_name = models.CharField(db_column="updaterName", max_length=255, null=True, blank=True)

    created_at = models.DateTimeField(db_column="createdAt", auto_now_add=True)
    updated_at = models.DateTimeField(db_column="updatedAt", auto_now=True)

    class Meta:
        abstract = True
