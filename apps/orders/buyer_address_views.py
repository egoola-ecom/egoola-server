"""
The buyer's own saved delivery addresses (`/api/v1/buyer/addresses/...`).
Checkout snapshots one of these onto the order it creates — editing or
deleting a saved address here never changes a past order.
"""

from rest_framework import viewsets

from apps.authentication.permissions import IsBuyerActor

from .buyer_address_serializers import BuyerAddressSerializer
from .models import Address


class BuyerAddressViewSet(viewsets.ModelViewSet):
    permission_classes = [IsBuyerActor]
    serializer_class = BuyerAddressSerializer
    pagination_class = None  # a buyer never has enough saved addresses to paginate

    def get_queryset(self):
        return Address.objects.filter(
            addressable_type=Address.AddressableType.USER, addressable_id=self.request.user.id,
        ).select_related("country", "state", "city", "thana").order_by("-created_at")

    def perform_create(self, serializer):
        actor = self.request.user
        serializer.save(
            addressable_type=Address.AddressableType.USER, addressable_id=actor.id,
            created_by=actor.id, creator_type=actor.actor_type, creator_name=actor.name,
        )

    def perform_update(self, serializer):
        actor = self.request.user
        serializer.save(updated_by=actor.id, updater_type=actor.actor_type, updater_name=actor.name)
