"""
Identity & Authentication (DB Redesign doc, Section 3.2) plus Seller
Business Profile (Section 3.3).

Three independent registration roots — Admin, Seller, User (buyer) — each
with its own dedicated media table, replacing the legacy schema's single
`users` table with a `role` column plus a dozen bolt-on tables (user_infos,
verifies, verify_phone, otps, otp_logs, forget_otps, password_resets,
contacts, skills, interests, edcations, experiences).
"""

from django.db import models

from apps.core.models import ActorType, AuditedModel


class MediaType(models.TextChoices):
    IMAGE = "image", "Image"
    VIDEO = "video", "Video"
    DOCUMENT = "document", "Document"


class Admin(AuditedModel):
    class AdminType(models.TextChoices):
        SUPER_ADMIN = "super_admin", "Super Admin"
        ADMIN = "admin", "Admin"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"

    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    mobile = models.CharField(max_length=32, unique=True)
    password = models.CharField(max_length=255)
    profile_pic_path = models.CharField(db_column="profilePicPath", max_length=255, null=True, blank=True)
    profile_pic_url = models.URLField(db_column="profilePicUrl", max_length=500, null=True, blank=True)
    type = models.CharField(max_length=20, choices=AdminType.choices)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)

    skills = models.JSONField(null=True, blank=True)
    experiences = models.JSONField(null=True, blank=True)
    interests = models.JSONField(null=True, blank=True)
    educations = models.JSONField(null=True, blank=True)

    present_address = models.TextField(db_column="presentAddress", null=True, blank=True)
    permanent_address = models.TextField(db_column="permanentAddress", null=True, blank=True)
    country = models.ForeignKey(
        "geography.Country", on_delete=models.SET_NULL, null=True, blank=True, db_column="countryId"
    )
    state = models.ForeignKey(
        "geography.State", on_delete=models.SET_NULL, null=True, blank=True, db_column="stateId"
    )
    city = models.ForeignKey(
        "geography.City", on_delete=models.SET_NULL, null=True, blank=True, db_column="cityId"
    )
    thana = models.ForeignKey(
        "geography.Thana", on_delete=models.SET_NULL, null=True, blank=True, db_column="thanaId"
    )

    last_logged_at = models.DateTimeField(db_column="lastLoggedAt", null=True, blank=True)

    # Statuses that may log in (checked at login and on every request).
    LOGIN_STATUSES = (Status.ACTIVE,)

    class Meta:
        db_table = "admins"
        ordering = ["name"]

    def __str__(self):
        return self.name


class AdminMedia(AuditedModel):
    class MediaFor(models.TextChoices):
        NID = "nid", "NID"
        BIRTH_CERTIFICATE = "birth_certificate", "Birth Certificate"
        PROFILE_DOCUMENT = "profile_document", "Profile Document"
        OTHER = "other", "Other"

    admin = models.ForeignKey(Admin, on_delete=models.CASCADE, related_name="media", db_column="adminId")
    media_type = models.CharField(db_column="mediaType", max_length=10, choices=MediaType.choices)
    media_for = models.CharField(db_column="mediaFor", max_length=20, choices=MediaFor.choices)
    media_path = models.CharField(db_column="mediaPath", max_length=255)
    media_url = models.URLField(db_column="mediaUrl", max_length=500)

    class Meta:
        db_table = "adminMedia"
        verbose_name_plural = "admin media"


class Seller(AuditedModel):
    class VerificationStatus(models.TextChoices):
        UNVERIFIED = "unverified", "Unverified"
        PENDING = "pending", "Pending"
        VERIFIED = "verified", "Verified"
        REJECTED = "rejected", "Rejected"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        # A seller who registered by themselves starts here and cannot log
        # in until an admin activates the account.
        INACTIVE = "inactive", "Inactive"
        SUSPENDED = "suspended", "Suspended"

    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=32, unique=True)
    password = models.CharField(max_length=255)
    profile_pic_path = models.CharField(db_column="profilePicPath", max_length=255, null=True, blank=True)
    profile_pic_url = models.URLField(db_column="profilePicUrl", max_length=500, null=True, blank=True)

    email_verified_at = models.DateTimeField(db_column="emailVerifiedAt", null=True, blank=True)
    phone_verified_at = models.DateTimeField(db_column="phoneVerifiedAt", null=True, blank=True)
    email_otp_code = models.CharField(db_column="emailOtpCode", max_length=20, null=True, blank=True)
    email_otp_expires_at = models.DateTimeField(db_column="emailOtpExpiresAt", null=True, blank=True)
    phone_otp_code = models.CharField(db_column="phoneOtpCode", max_length=20, null=True, blank=True)
    phone_otp_expires_at = models.DateTimeField(db_column="phoneOtpExpiresAt", null=True, blank=True)
    phone_otp_attempts = models.IntegerField(db_column="phoneOtpAttempts", default=0)
    password_reset_token = models.CharField(db_column="passwordResetToken", max_length=255, null=True, blank=True)
    password_reset_expires_at = models.DateTimeField(db_column="passwordResetExpiresAt", null=True, blank=True)
    remember_token = models.CharField(db_column="rememberToken", max_length=255, null=True, blank=True)

    verification_status = models.CharField(
        db_column="verificationStatus", max_length=12, choices=VerificationStatus.choices,
        default=VerificationStatus.UNVERIFIED,
    )
    verification_note = models.TextField(db_column="verificationNote", null=True, blank=True)
    # True while a self-registered seller is waiting in the admin's "Seller
    # Request" queue. Set by the registration endpoint; cleared by the first
    # admin action on the seller's verification_status or status. Never
    # writable by a client.
    is_seller_request = models.BooleanField(db_column="isSellerRequest", default=False)
    # When the seller joined the request queue: set at sign-up and again each
    # time a rejected seller resubmits. The queue sorts on this, so a
    # resubmission shows up as new instead of sitting at its old sign-up date.
    requested_at = models.DateTimeField(db_column="requestedAt", null=True, blank=True)

    skills = models.JSONField(null=True, blank=True)
    education = models.JSONField(null=True, blank=True)
    experience = models.JSONField(null=True, blank=True)
    interest = models.JSONField(null=True, blank=True)

    present_address = models.TextField(db_column="presentAddress", null=True, blank=True)
    permanent_address = models.TextField(db_column="permanentAddress", null=True, blank=True)
    country = models.ForeignKey(
        "geography.Country", on_delete=models.SET_NULL, null=True, blank=True, db_column="countryId"
    )
    state = models.ForeignKey(
        "geography.State", on_delete=models.SET_NULL, null=True, blank=True, db_column="stateId"
    )
    city = models.ForeignKey(
        "geography.City", on_delete=models.SET_NULL, null=True, blank=True, db_column="cityId"
    )
    thana = models.ForeignKey(
        "geography.Thana", on_delete=models.SET_NULL, null=True, blank=True, db_column="thanaId"
    )

    wallet_balance = models.DecimalField(db_column="walletBalance", max_digits=12, decimal_places=2, default=0)
    bonus_balance = models.DecimalField(db_column="bonusBalance", max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    last_logged_at = models.DateTimeField(db_column="lastLoggedAt", null=True, blank=True)

    # Two separate switches. `verification_status` is the KYC decision ("approved"
    # = verified). `status` is the account switch: an inactive seller (a new
    # sign-up, or an approved seller an admin paused) may log in but only manage
    # their own profile until an admin makes them active. A suspended seller may
    # not log in at all.
    LOGIN_STATUSES = (Status.ACTIVE, Status.INACTIVE)

    class Meta:
        db_table = "sellers"
        ordering = ["name"]
        indexes = [
            # The Seller Request queue: filter on the flag, page by newest request.
            models.Index(fields=["is_seller_request", "-requested_at"], name="sellers_request_queue_idx"),
        ]

    def __str__(self):
        return self.name

    @property
    def can_operate(self):
        """Allowed to use the full seller features (listings, orders, wallet):
        verified (approved) AND active. Every other seller — still pending or
        rejected, or approved but inactive — may only edit their own profile."""
        return (
            self.verification_status == self.VerificationStatus.VERIFIED
            and self.status == self.Status.ACTIVE
        )


class SellerMedia(AuditedModel):
    class MediaFor(models.TextChoices):
        NID = "nid", "NID"
        BIRTH_CERTIFICATE = "birth_certificate", "Birth Certificate"
        CERTIFICATE = "certificate", "Certificate"
        GALLERY_IMAGE = "gallery_image", "Gallery Image"
        GALLERY_VIDEO = "gallery_video", "Gallery Video"
        OTHER = "other", "Other"

    seller = models.ForeignKey(Seller, on_delete=models.CASCADE, related_name="media", db_column="sellerId")
    media_type = models.CharField(db_column="mediaType", max_length=10, choices=MediaType.choices)
    media_for = models.CharField(db_column="mediaFor", max_length=20, choices=MediaFor.choices)
    media_path = models.CharField(db_column="mediaPath", max_length=255)
    media_url = models.URLField(db_column="mediaUrl", max_length=500)

    class Meta:
        db_table = "sellerMedia"
        verbose_name_plural = "seller media"


class SellerVerificationLog(models.Model):
    """Append-only history of every verification_status change on a Seller
    — who changed it, to what, and (for a rejection) why. Written once on
    Seller creation and again on every update that changes
    verification_status; never updated or deleted afterwards, so this
    isn't an AuditedModel — there's no updated_by/updated_at to track on a
    row that never changes after it's written."""

    seller = models.ForeignKey(
        Seller, on_delete=models.CASCADE, related_name="verification_logs", db_column="sellerId"
    )
    verification_status = models.CharField(
        db_column="verificationStatus", max_length=12, choices=Seller.VerificationStatus.choices
    )
    verification_note = models.TextField(db_column="verificationNote", null=True, blank=True)

    created_by = models.BigIntegerField(db_column="createdBy", null=True, blank=True)
    creator_type = models.CharField(
        db_column="creatorType", max_length=10, choices=ActorType.choices, default=ActorType.SYSTEM
    )
    creator_name = models.CharField(db_column="creatorName", max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(db_column="createdAt", auto_now_add=True)

    class Meta:
        db_table = "sellerVerificationLogs"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Seller #{self.seller_id} -> {self.verification_status}"


class SellerProfileChangeLog(models.Model):
    """One row for every save that actually changed a seller's profile — by the
    seller themselves or by an admin. `previous_data` and `new_data` hold the
    same keys: only the fields that changed, as they were before and as they
    are now. Never updated or deleted afterwards (so not an AuditedModel).
    Status and verification changes are not here — see SellerVerificationLog."""

    seller = models.ForeignKey(
        Seller, on_delete=models.CASCADE, related_name="profile_change_logs", db_column="sellerId"
    )
    changed_fields = models.JSONField(db_column="changedFields")
    previous_data = models.JSONField(db_column="previousData")
    new_data = models.JSONField(db_column="newData")

    created_by = models.BigIntegerField(db_column="createdBy", null=True, blank=True)
    creator_type = models.CharField(
        db_column="creatorType", max_length=10, choices=ActorType.choices, default=ActorType.SYSTEM
    )
    creator_name = models.CharField(db_column="creatorName", max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(db_column="createdAt", auto_now_add=True)

    class Meta:
        db_table = "sellerProfileChangeLogs"
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["seller", "-created_at"], name="seller_change_log_idx")]

    def __str__(self):
        return f"Seller #{self.seller_id}: {', '.join(self.changed_fields)}"


class SellerInfo(AuditedModel):
    """The seller's public business profile — a 1:1 extension of Seller. Replaces
    the legacy `companies` table and folds in `contacts` (whatsapp/facebook/
    wechat/skype/public email)."""

    seller = models.OneToOneField(Seller, on_delete=models.CASCADE, related_name="info", db_column="sellerId")
    business_type = models.CharField(db_column="businessType", max_length=255)
    main_product = models.CharField(db_column="mainProduct", max_length=255)
    owner_name = models.CharField(db_column="ownerName", max_length=255)
    employees_range = models.CharField(db_column="employeesRange", max_length=50)
    annual_revenue = models.CharField(db_column="annualRevenue", max_length=100)
    established_year = models.CharField(db_column="establishedYear", max_length=10)
    description = models.TextField(null=True, blank=True)

    public_email = models.EmailField(db_column="publicEmail", null=True, blank=True)
    whatsapp = models.CharField(max_length=32, null=True, blank=True)
    facebook = models.URLField(max_length=500, null=True, blank=True)
    wechat = models.CharField(max_length=100, null=True, blank=True)
    skype = models.CharField(max_length=100, null=True, blank=True)

    country = models.ForeignKey(
        "geography.Country", on_delete=models.SET_NULL, null=True, blank=True, db_column="countryId"
    )
    state = models.ForeignKey(
        "geography.State", on_delete=models.SET_NULL, null=True, blank=True, db_column="stateId"
    )
    city = models.ForeignKey(
        "geography.City", on_delete=models.SET_NULL, null=True, blank=True, db_column="cityId"
    )
    thana = models.ForeignKey(
        "geography.Thana", on_delete=models.SET_NULL, null=True, blank=True, db_column="thanaId"
    )

    class Meta:
        db_table = "sellerInfos"

    def __str__(self):
        return f"{self.seller.name} profile"


class User(AuditedModel):
    """An ordinary buyer's login and account row. Named `User` to match the
    Planning document's app/model table (Section 4.1) — this is the buyer,
    not Django's own auth user (see `core`/settings: this app does not use
    `django.contrib.auth`'s User for application login at all, per the
    Planning document Section 4.2)."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        SUSPENDED = "suspended", "Suspended"

    name = models.CharField(max_length=255)
    # Optional: a buyer signs up with a name, a mobile number and a password.
    # Several buyers may have no email (NULLs do not collide in the unique index).
    email = models.EmailField(unique=True, null=True, blank=True)
    phone = models.CharField(max_length=32, unique=True)
    password = models.CharField(max_length=255)
    profile_pic_path = models.CharField(db_column="profilePicPath", max_length=255, null=True, blank=True)
    profile_pic_url = models.URLField(db_column="profilePicUrl", max_length=500, null=True, blank=True)
    description = models.TextField(null=True, blank=True)

    skills = models.JSONField(null=True, blank=True)
    experiences = models.JSONField(null=True, blank=True)
    interests = models.JSONField(null=True, blank=True)
    educations = models.JSONField(null=True, blank=True)

    email_verified_at = models.DateTimeField(db_column="emailVerifiedAt", null=True, blank=True)
    phone_verified_at = models.DateTimeField(db_column="phoneVerifiedAt", null=True, blank=True)
    email_otp_code = models.CharField(db_column="emailOtpCode", max_length=20, null=True, blank=True)
    email_otp_expires_at = models.DateTimeField(db_column="emailOtpExpiresAt", null=True, blank=True)
    phone_otp_code = models.CharField(db_column="phoneOtpCode", max_length=20, null=True, blank=True)
    phone_otp_expires_at = models.DateTimeField(db_column="phoneOtpExpiresAt", null=True, blank=True)
    phone_otp_attempts = models.IntegerField(db_column="phoneOtpAttempts", default=0)
    password_reset_token = models.CharField(db_column="passwordResetToken", max_length=255, null=True, blank=True)
    password_reset_expires_at = models.DateTimeField(db_column="passwordResetExpiresAt", null=True, blank=True)
    remember_token = models.CharField(db_column="rememberToken", max_length=255, null=True, blank=True)

    address_line = models.CharField(db_column="addressLine", max_length=255, null=True, blank=True)
    country = models.ForeignKey(
        "geography.Country", on_delete=models.SET_NULL, null=True, blank=True, db_column="countryId"
    )
    state = models.ForeignKey(
        "geography.State", on_delete=models.SET_NULL, null=True, blank=True, db_column="stateId"
    )
    city = models.ForeignKey(
        "geography.City", on_delete=models.SET_NULL, null=True, blank=True, db_column="cityId"
    )
    thana = models.ForeignKey(
        "geography.Thana", on_delete=models.SET_NULL, null=True, blank=True, db_column="thanaId"
    )

    wallet_balance = models.DecimalField(db_column="walletBalance", max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)

    LOGIN_STATUSES = (Status.ACTIVE,)

    class Meta:
        db_table = "users"
        ordering = ["name"]

    def __str__(self):
        return self.name


class BuyerMedia(AuditedModel):
    class MediaFor(models.TextChoices):
        NID = "nid", "NID"
        BIRTH_CERTIFICATE = "birth_certificate", "Birth Certificate"
        PROFILE_DOCUMENT = "profile_document", "Profile Document"
        OTHER = "other", "Other"

    buyer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="media", db_column="buyerId")
    media_type = models.CharField(db_column="mediaType", max_length=10, choices=MediaType.choices)
    media_for = models.CharField(db_column="mediaFor", max_length=20, choices=MediaFor.choices)
    media_path = models.CharField(db_column="mediaPath", max_length=255)
    media_url = models.URLField(db_column="mediaUrl", max_length=500)

    class Meta:
        db_table = "buyerMedia"
        verbose_name_plural = "buyer media"
