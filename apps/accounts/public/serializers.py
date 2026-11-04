"""
Public, no-auth serializers: the seller profile a buyer sees, and the
self-registration serializers for a seller or buyer signing up. See
public/views.py and docs/public-api-guide.md.
"""

import re

from django.utils import timezone
from rest_framework import serializers

from apps.core.location import LocationConsistencyMixin
from apps.core.models import ActorType

from ..common_serializers import (
    KYC_MEDIA_FOR, MediaSyncMixin, OptionalBuyerEmailMixin, PasswordWriteMixin, ProfilePicUploadMixin,
    SellerInfoSerializer, validate_kyc_files,
)
from ..models import Seller, SellerInfo, SellerMedia, SellerVerificationLog, User


class PublicSellerBriefSerializer(serializers.ModelSerializer):
    """The seller block on a listing: enough to show the name and link to the profile."""

    class Meta:
        model = Seller
        fields = ["id", "name", "profile_pic_url"]


class PublicSellerSerializer(serializers.ModelSerializer):
    """The seller's public page."""

    member_since = serializers.DateTimeField(source="created_at", read_only=True)
    location = serializers.SerializerMethodField()
    business = serializers.SerializerMethodField()
    contact = serializers.SerializerMethodField()
    product_count = serializers.IntegerField(read_only=True)
    gig_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Seller
        fields = [
            "id", "name", "profile_pic_url", "member_since", "location", "business", "contact",
            "skills", "education", "experience", "product_count", "gig_count",
        ]

    def get_location(self, obj):
        info = getattr(obj, "info", None)
        place = info if info is not None and (info.country_id or info.city_id) else obj
        return {
            "country": place.country.name if place.country_id else None,
            "state": place.state.name if place.state_id else None,
            "city": place.city.name if place.city_id else None,
            "thana": place.thana.name if place.thana_id else None,
        }

    def get_business(self, obj):
        info = getattr(obj, "info", None)
        if info is None:
            return None
        return {
            "business_type": info.business_type,
            "main_product": info.main_product,
            "description": info.description,
            "established_year": info.established_year,
            "employees_range": info.employees_range,
        }

    def get_contact(self, obj):
        info = getattr(obj, "info", None)
        if info is None:
            return None
        return {
            "public_email": info.public_email, "whatsapp": info.whatsapp, "facebook": info.facebook,
            "wechat": info.wechat, "skype": info.skype,
        }


class SellerRegistrationSerializer(
    LocationConsistencyMixin, MediaSyncMixin, ProfilePicUploadMixin, PasswordWriteMixin, serializers.ModelSerializer
):
    """A seller signing up by themselves (public endpoint, no login).

    Deliberately a separate serializer from SellerSerializer: that one lets an
    admin set verification_status, status, wallet and so on. Here none of those
    can be sent — the account is always created unverified and inactive, flagged
    as a seller request, and attributed to the seller themselves.

    Required: name, email, phone, password, both addresses, country/state/city
    and at least one NID file. Optional: thana, profile_pic, other documents,
    and the business profile (`info`)."""

    password = serializers.CharField(write_only=True, required=True, style={"input_type": "password"})
    profile_pic = serializers.ImageField(write_only=True, required=False)
    media_for = serializers.ListField(
        child=serializers.ChoiceField(choices=[(item.value, item.label) for item in KYC_MEDIA_FOR]),
        write_only=True, required=True,
    )
    media_file = serializers.ListField(child=serializers.FileField(), write_only=True, required=True)
    info = serializers.JSONField(write_only=True, required=False)

    media_model = SellerMedia
    media_fk_name = "seller"

    class Meta:
        model = Seller
        fields = [
            "id", "name", "email", "phone", "password", "profile_pic",
            "present_address", "permanent_address", "country", "state", "city", "thana",
            "media_for", "media_file", "info",
            "verification_status", "status", "is_seller_request",
        ]
        read_only_fields = ["verification_status", "status", "is_seller_request"]
        extra_kwargs = {
            "present_address": {"required": True, "allow_null": False, "allow_blank": False},
            "permanent_address": {"required": True, "allow_null": False, "allow_blank": False},
            "country": {"required": True, "allow_null": False},
            "state": {"required": True, "allow_null": False},
            "city": {"required": True, "allow_null": False},
        }

    def validate_email(self, value):
        # The model's own unique check is case-sensitive, but login matches
        # emails case-insensitively — so two spellings must not both register.
        if Seller.objects.filter(email__iexact=value).exists():
            # Same wording as the model's own unique check, so the form shows one message.
            raise serializers.ValidationError("seller with this email already exists.")
        return value

    def validate_media_file(self, files):
        return validate_kyc_files(files)

    def validate_info(self, value):
        # Optional business profile: when sent it must be complete. Validated
        # here, before anything is saved, so a bad profile never leaves a
        # half-registered seller (or uploaded files) behind.
        info_serializer = SellerInfoSerializer(data=value)
        info_serializer.is_valid(raise_exception=True)
        return info_serializer.validated_data

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if SellerMedia.MediaFor.NID not in attrs["media_for"]:
            raise serializers.ValidationError(
                {"media_for": "At least one NID document is required (media_for = nid)."}
            )
        return attrs

    def create(self, validated_data):
        info_data = validated_data.pop("info", None)
        validated_data.update(
            verification_status=Seller.VerificationStatus.UNVERIFIED,
            status=Seller.Status.INACTIVE,
            is_seller_request=True,
            requested_at=timezone.now(),
            creator_type=ActorType.SELLER,
            creator_name=validated_data["name"],
        )
        seller = super().create(validated_data)
        # The seller is their own creator — their id only exists after the save.
        seller.created_by = seller.pk
        seller.save(update_fields=["created_by"])
        if info_data:
            SellerInfo.objects.update_or_create(seller=seller, defaults=info_data)
        SellerVerificationLog.objects.create(
            seller=seller,
            verification_status=seller.verification_status,
            created_by=seller.pk,
            creator_type=ActorType.SELLER,
            creator_name=seller.name,
        )
        return seller


MOBILE_PATTERN = re.compile(r"^\+?[0-9]{6,15}$")


class BuyerRegistrationSerializer(
    OptionalBuyerEmailMixin, LocationConsistencyMixin, ProfilePicUploadMixin, PasswordWriteMixin,
    serializers.ModelSerializer,
):
    """A buyer signing up by themselves (public endpoint, no login).

    Required: `name`, `phone` (the mobile number, also the login) and `password`.
    Everything else is optional: `email`, `profile_pic`, `description`, `address_line`,
    `country` / `state` / `city` / `thana` (one branch of the geography tree) and the
    free-form `skills`, `experiences`, `interests`, `educations`. The account is active
    at once and is attributed to the buyer themselves. Status and wallet cannot be sent."""

    password = serializers.CharField(write_only=True, required=True, style={"input_type": "password"})
    profile_pic = serializers.ImageField(write_only=True, required=False)

    class Meta:
        model = User
        fields = [
            "id", "name", "phone", "password", "email", "profile_pic", "profile_pic_url", "description",
            "address_line", "country", "state", "city", "thana",
            "skills", "experiences", "interests", "educations", "status",
        ]
        read_only_fields = ["profile_pic_url", "status"]
        extra_kwargs = {
            "name": {"required": True, "allow_blank": False},
            "phone": {"required": True, "validators": []},  # uniqueness is checked in validate_phone
            "description": {"allow_blank": True},
            "address_line": {"allow_blank": True},
        }

    def validate_phone(self, value):
        phone = re.sub(r"[\s-]", "", value)
        if not MOBILE_PATTERN.match(phone):
            raise serializers.ValidationError("Enter a valid mobile number (digits only, may start with +).")
        if User.objects.filter(phone=phone).exists():
            raise serializers.ValidationError("buyer with this phone already exists.")
        return phone

    def create(self, validated_data):
        validated_data.update(creator_type=ActorType.USER, creator_name=validated_data["name"])
        buyer = super().create(validated_data)
        # The buyer is their own creator: their id only exists after the save.
        buyer.created_by = buyer.pk
        buyer.save(update_fields=["created_by"])
        return buyer
