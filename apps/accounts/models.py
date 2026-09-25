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

from apps.core.models import AuditedModel


class MediaType(models.TextChoices):
    IMAGE = "image", "Image"
    VIDEO = "video", "Video"
    DOCUMENT = "document", "Document"


class Admin(AuditedModel):
    class AdminType(models.TextChoices):
        SUPER_ADMIN = "super_admin", "Super Admin"
        ADMIN = "admin", "Admin"
        MODERATOR = "moderator", "Moderator"
        SUPPORT = "support", "Support"

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

    class Meta:
        db_table = "sellers"
        ordering = ["name"]

    def __str__(self):
        return self.name


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
    email = models.EmailField(unique=True)
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
