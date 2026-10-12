"""
The seller's own endpoints (`/api/v1/seller/...`). Open to any logged-in seller
(not suspended) — a seller who cannot operate yet (still pending or rejected, or
approved but inactive) can log in but may only use these: edit their profile,
change password, resubmit a rejected application.
Every other seller feature must use IsActiveVerifiedSellerActor.
"""

from django.contrib.auth.hashers import make_password
from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.authentication.permissions import IsSellerActor
from apps.core.models import ActorType

from .models import Seller, SellerVerificationLog
from .profile_log import record_profile_changes, snapshot
from .serializers import SellerChangePasswordSerializer, SellerResubmitSerializer, SellerSelfSerializer


def _own_profile(seller_id):
    return Seller.objects.select_related("country", "state", "city", "thana", "info").get(pk=seller_id)


def _actor_stamp(seller, prefix):
    """The audit columns for a row the seller changes themselves."""
    return {f"{prefix}_by": seller.pk, f"{prefix}er_type": ActorType.SELLER, f"{prefix}er_name": seller.name}


class SellerMeView(APIView):
    """`GET` the seller's own profile; `PATCH` to edit it (multipart/form-data when
    a file is sent). Phone and email cannot be changed."""

    permission_classes = [IsSellerActor]

    def get(self, request):
        return Response(SellerSelfSerializer(_own_profile(request.user.pk)).data)

    def patch(self, request):
        seller = _own_profile(request.user.pk)
        serializer = SellerSelfSerializer(seller, data=request.data, partial=True, context={"request": request})
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            serializer.save(updated_by=seller.pk, updater_type=ActorType.SELLER, updater_name=seller.name)
        return Response(SellerSelfSerializer(_own_profile(seller.pk)).data)


class SellerResubmitView(APIView):
    """A rejected seller, after fixing their profile and documents, sends the
    application back for review: status becomes `pending`, the seller joins the
    admin's Seller Request queue again, and the history gets an entry."""

    permission_classes = [IsSellerActor]

    def post(self, request):
        seller = _own_profile(request.user.pk)
        if seller.verification_status != Seller.VerificationStatus.REJECTED:
            return Response(
                {"detail": "Only a rejected application can be resubmitted."}, status=status.HTTP_400_BAD_REQUEST
            )
        body = SellerResubmitSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        note = body.validated_data.get("note") or None
        with transaction.atomic():
            seller.verification_status = Seller.VerificationStatus.PENDING
            # The note on the row is for the current status: here, the seller's
            # message to the reviewer (the rejection reason stays in the history).
            seller.verification_note = note
            seller.is_seller_request = True
            seller.requested_at = timezone.now()
            seller.updated_by, seller.updater_type, seller.updater_name = seller.pk, ActorType.SELLER, seller.name
            seller.save()
            SellerVerificationLog.objects.create(
                seller=seller,
                verification_status=seller.verification_status,
                verification_note=note,
                created_by=seller.pk,
                creator_type=ActorType.SELLER,
                creator_name=seller.name,
            )
        return Response(SellerSelfSerializer(_own_profile(seller.pk)).data)


class SellerChangePasswordView(APIView):
    """The seller changes their own password; the current one is required."""

    permission_classes = [IsSellerActor]

    def post(self, request):
        seller = _own_profile(request.user.pk)
        serializer = SellerChangePasswordSerializer(data=request.data, context={"seller": seller})
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            before = snapshot(seller)
            seller.password = make_password(serializer.validated_data["new_password"])
            seller.updated_by, seller.updater_type, seller.updater_name = seller.pk, ActorType.SELLER, seller.name
            seller.save()
            record_profile_changes(seller, before, seller.pk, ActorType.SELLER, seller.name)
        return Response({"detail": "Password changed."})
