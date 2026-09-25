from rest_framework.permissions import BasePermission

from apps.core.models import ActorType


class _IsActor(BasePermission):
    """Shared shape for the three actor-only permissions below — each one
    only differs in which `actor_type` it requires, so that's the only
    thing a subclass sets."""

    actor_type = None

    def has_permission(self, request, view):
        return getattr(request.user, "actor_type", None) == self.actor_type


class IsAdminActor(_IsActor):
    """Passes only for a request authenticated as an Admin (see
    backends.ActorJWTAuthentication) — a Seller/Buyer actor, and an
    anonymous request, are both rejected.

    Currently applied to Admin/Seller/Buyer Management (apps.accounts) —
    that's Admin-only management of every actor's record, not a Seller's
    or Buyer's own self-service routes (see IsSellerActor/IsBuyerActor).
    """

    actor_type = ActorType.ADMIN
    message = "Only an authenticated Admin can access this endpoint."


class IsSellerActor(_IsActor):
    """Passes only for a request authenticated as a Seller — not yet
    attached to any endpoint (no Seller-facing views exist yet), but ready
    for when catalog/bidding/orders add a Seller's own self-service
    routes."""

    actor_type = ActorType.SELLER
    message = "Only an authenticated Seller can access this endpoint."


class IsBuyerActor(_IsActor):
    """Passes only for a request authenticated as a Buyer — not yet
    attached to any endpoint, for the same reason as IsSellerActor."""

    actor_type = ActorType.USER
    message = "Only an authenticated Buyer can access this endpoint."
