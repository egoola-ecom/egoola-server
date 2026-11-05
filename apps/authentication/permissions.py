from rest_framework.permissions import BasePermission

from apps.accounts.models import Admin
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


class IsSuperAdminActor(_IsActor):
    """Passes only for an Admin whose own `type` is super_admin — a plain
    `admin`, a Seller, a Buyer and an anonymous request are all rejected.
    Used by Admin Management, the one area only super-admins may touch. The
    actor row is loaded fresh on every request (see ActorJWTAuthentication),
    so demoting a super-admin takes effect immediately, not at token expiry."""

    actor_type = ActorType.ADMIN
    message = "Only a super-admin can access Admin Management."

    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.type == Admin.AdminType.SUPER_ADMIN


class IsSellerActor(_IsActor):
    """Passes for any logged-in Seller — every status, even a locked one, can
    log in and reach a GET of their own profile. Writing to it, or anything
    further, needs IsProfileEditableSellerActor or IsActiveVerifiedSellerActor
    instead (see both, and Seller.can_edit_profile/can_operate)."""

    actor_type = ActorType.SELLER
    message = "Only an authenticated Seller can access this endpoint."


class IsProfileEditableSellerActor(IsSellerActor):
    """A Seller allowed to edit their own profile/documents, change password,
    or (if rejected) resubmit — `SellerMeView.patch`, `SellerResubmitView`,
    `SellerChangePasswordView`. Broader than IsActiveVerifiedSellerActor (full
    operate), narrower than IsSellerActor (any logged-in seller — used only
    for the read-only GET of this same profile). A "locked" seller fails
    this: see Seller.can_edit_profile for exactly which combinations do."""

    message = "Your seller account is locked. Contact support."

    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.can_edit_profile


class IsActiveVerifiedSellerActor(IsSellerActor):
    """A Seller who is verified (approved) AND active. Every seller feature
    except editing one's own profile (listings, orders, wallet, withdrawals ...)
    must use this, not IsSellerActor. The row is loaded fresh on every request,
    so an approval, a pause (inactive) or a suspension takes effect at once."""

    message = "Your seller account cannot do this yet."

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        seller = request.user
        if seller.can_operate:
            return True
        # Only two ways to fail can_operate while still reaching here: locked
        # (can_edit_profile is False — this covers verified+inactive too,
        # since can_edit_profile already excludes that combination, so there
        # is no third "verified but not active" branch left to report) or
        # simply not verified yet.
        if not seller.can_edit_profile:
            self.message = "Your seller account is locked. Contact support."
        else:
            self.message = "Your seller application is not approved yet. You can only edit your profile until an admin approves it."
        return False


class IsBuyerActor(_IsActor):
    """Passes only for a request authenticated as a Buyer — not yet
    attached to any endpoint, for the same reason as IsSellerActor."""

    actor_type = ActorType.USER
    message = "Only an authenticated Buyer can access this endpoint."
