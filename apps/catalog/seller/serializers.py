"""
Every serializer for the seller's own products (`/seller/listings/`), gigs
(`/seller/gigs/`), job board (`/seller/jobs/`), and the read-only lookups
the listing form needs (`/seller/lookups/...`). See seller/views.py.
"""

from rest_framework import serializers

from .. import kinds
from ..admin_api.serializers import GigSerializer, ListingSerializer
from ..common_serializers import ListingFromPriceMixin
from ..models import (
    Attribute, AttributeValue, Brand, Category, Listing, ListingStatusChangeLog, Measurement,
)

# --- Lookups for the listing/gig form ---------------------------------------

class SellerCategoryLookupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "type", "parent", "name", "name_bn", "slug", "sort_order"]


class SellerBrandLookupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ["id", "name", "slug"]


class SellerMeasurementLookupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Measurement
        fields = ["id", "name", "slug", "symbol"]


class SellerAttributeValueLookupSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttributeValue
        fields = ["id", "name", "name_bn"]


class SellerAttributeLookupSerializer(serializers.ModelSerializer):
    values = serializers.SerializerMethodField()

    class Meta:
        model = Attribute
        fields = ["id", "name", "name_bn", "values"]

    def get_values(self, attribute):
        active = [value for value in attribute.values.all() if value.is_active]
        return SellerAttributeValueLookupSerializer(active, many=True).data


# --- Products and gigs -------------------------------------------------------

class SellerListingListSerializer(ListingFromPriceMixin, serializers.ModelSerializer):
    """A seller's own product list: what they need to see at a glance."""

    price = serializers.SerializerMethodField()
    discounted_price = serializers.SerializerMethodField()

    class Meta:
        model = Listing
        fields = [
            "id", "title", "title_bn", "slug", "catalog_type", "listing_type",
            "category", "brand", "price", "discounted_price", "image_url",
            "status", "note", "requested_at", "created_at", "updated_at",
        ]


class SellerGigListSerializer(ListingFromPriceMixin, serializers.ModelSerializer):
    """A seller's own gig list (see GigListSerializer for the price fields)."""

    price = serializers.SerializerMethodField()
    discounted_price = serializers.SerializerMethodField()
    price_type = serializers.SerializerMethodField()

    class Meta:
        model = Listing
        fields = [
            "id", "title", "title_bn", "slug", "category", "price", "discounted_price", "price_type",
            "image_url", "status", "note", "requested_at", "created_at", "updated_at",
        ]


class SellerStatusLogSerializer(serializers.ModelSerializer):
    """The status history as a seller sees it: what happened, why and when, and
    whether the seller or an admin did it, but not which admin."""

    class Meta:
        model = ListingStatusChangeLog
        fields = ["id", "status", "note", "creator_type", "created_at"]


class SellerListingMixin:
    """What makes a listing serializer a seller's own (`/seller/listings/`,
    `/seller/gigs/`): the moderation parts are taken away from the seller.

    - The owner is always the logged-in seller and the listing is always a
      `seller_offer`: `seller`, `buyer` and `posted_by_role` are not accepted.
    - `status` is read-only. A new listing is always `pending`. Saving a
      `rejected` or `changes_requested` listing sends it back to `pending`
      (and to the admin's pending list as the newest request). Saving an
      `approved` or `pending` listing leaves its status alone.
    - `note` is the admin's reason when the listing was rejected. A note sent
      while saving a rejected / changes-requested listing becomes the seller's
      message to the reviewer; in any other state a note is ignored.
    - The seller sees the status history but not the info change log."""

    duplicate_title_message = "You already have a listing with this title. Update the existing listing instead."

    def validate(self, attrs):
        if self.instance is None:
            attrs["seller"] = self.context["request"].user
            attrs["posted_by_role"] = Listing.PostedByRole.SELLER_OFFER
            attrs.pop("note", None)  # a new listing has no reason to explain yet
        return super().validate(attrs)

    def update(self, instance, validated_data):
        # A listing an admin left as a draft is submitted the same way.
        if instance.status in Listing.RESUBMIT_STATUSES:
            validated_data["status"] = Listing.Status.PENDING
            validated_data["note"] = validated_data.get("note") or None
        else:
            validated_data.pop("note", None)
        return super().update(instance, validated_data)


_SELLER_HIDDEN_FIELDS = ("seller", "buyer", "posted_by_role", "info_change_logs")


class SellerListingSerializer(SellerListingMixin, ListingSerializer):
    """A seller's own product (`/seller/listings/`). Service fields are not
    part of a product; a seller's service offer is a gig (SellerGigSerializer)."""

    scope = kinds.PRODUCT
    foreign_fields = kinds.SERVICE_ONLY_FIELDS
    status_change_logs = SellerStatusLogSerializer(many=True, read_only=True)

    class Meta(ListingSerializer.Meta):
        fields = [
            name for name in ListingSerializer.Meta.fields
            if name not in _SELLER_HIDDEN_FIELDS and name not in kinds.SERVICE_ONLY_FIELDS
        ]
        read_only_fields = ListingSerializer.Meta.read_only_fields + ["status"]
        extra_kwargs = {**ListingSerializer.Meta.extra_kwargs, "catalog_type": {"required": False}}


class SellerGigSerializer(SellerListingMixin, GigSerializer):
    """A seller's own gig (`/seller/gigs/`)."""

    status_change_logs = SellerStatusLogSerializer(many=True, read_only=True)

    class Meta(GigSerializer.Meta):
        fields = [name for name in GigSerializer.Meta.fields if name not in _SELLER_HIDDEN_FIELDS]
        read_only_fields = GigSerializer.Meta.read_only_fields + ["status"]


# --- Job board ----------------------------------------------------------------

class _JobCategoryBrief(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "name_bn", "slug"]


class SellerJobListSerializer(serializers.ModelSerializer):
    category = _JobCategoryBrief(read_only=True)
    budget = serializers.SerializerMethodField()
    bid_count = serializers.IntegerField(read_only=True)
    my_bid_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Listing
        fields = [
            "id", "title", "title_bn", "slug", "category", "status", "budget",
            "delivery_days", "urgent", "bid_count", "my_bid_count", "created_at",
        ]

    def get_budget(self, obj):
        skus = [s for s in obj.skus.all() if s.is_active]
        if not skus:
            return None
        cheapest = min(skus, key=lambda s: s.effective_price())
        return {"price": str(cheapest.effective_price()), "price_type": cheapest.price_type}


class SellerJobDetailSerializer(SellerJobListSerializer):
    my_bids = serializers.SerializerMethodField()
    location = serializers.SerializerMethodField()

    class Meta(SellerJobListSerializer.Meta):
        fields = SellerJobListSerializer.Meta.fields + [
            "description", "description_bn", "package_includes", "package_includes_bn",
            "available_from", "available_to", "location", "my_bids",
        ]

    def get_location(self, obj):
        return {
            level: ({"id": getattr(obj, f"{level}_id"), "name": getattr(obj, level).name} if getattr(obj, f"{level}_id") else None)
            for level in ("country", "state", "city", "thana")
        }

    def get_my_bids(self, obj):
        # Imported here to avoid a hard import cycle between catalog and bidding.
        from apps.bidding.seller.serializers import SellerBidListSerializer

        seller = self.context["request"].user
        mine = [b for b in obj.bids.all() if b.bidder_id == seller.id]
        return SellerBidListSerializer(mine, many=True).data
