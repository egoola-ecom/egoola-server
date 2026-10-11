"""
Login — one endpoint per actor table (Admin/Seller/Buyer). All three share
the same flow (BaseActorLoginView below); a subclass only says which model
to check the email/password against and which `actor_type` claim to stamp
on the token it issues.
"""

from django.contrib.auth.hashers import check_password
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import Admin, Seller, User
from apps.accounts.serializers import SellerRegistrationSerializer
from apps.core.models import ActorType

from .tokens import tokens_for_actor


class LoginInputSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, style={"input_type": "password"})


class BaseActorLoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []  # logging in is how you get a token, so it never requires one
    actor_model = None
    actor_type = None

    def post(self, request):
        serializer = LoginInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        password = serializer.validated_data["password"]

        actor = self.actor_model.objects.filter(email__iexact=email).first()
        if actor is None or not check_password(password, actor.password):
            # Same error either way — confirming "no such email" to a
            # client would let anyone probe which emails are registered.
            raise AuthenticationFailed("Invalid email or password.")

        if actor.status != actor.Status.ACTIVE:
            raise AuthenticationFailed(self.inactive_message(actor), code="user_inactive")

        # Admin and Seller track last_logged_at; Buyer (`User`) doesn't
        # have that column at all — this stays generic across all three
        # rather than every subclass repeating the same save() call.
        if hasattr(actor, "last_logged_at"):
            actor.last_logged_at = timezone.now()
            actor.save(update_fields=["last_logged_at"])

        refresh = tokens_for_actor(actor, self.actor_type)
        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "actor_type": self.actor_type,
                "id": actor.id,
                "name": actor.name,
                "email": actor.email,
                **self.extra_login_fields(actor),
            }
        )

    def get_authenticate_header(self, request):
        # Login has no authenticator, and DRF turns a 401 into a 403 when
        # there is no authenticator to name in the WWW-Authenticate header.
        # A wrong password or an inactive account is a 401, so say "Bearer".
        return 'Bearer realm="api"'

    def extra_login_fields(self, actor):
        """Extra keys for the login response of one kind of actor."""
        return {}

    def inactive_message(self, actor):
        """The error shown when the password is right but the account is not active."""
        return "This account is not active."


class AdminLoginView(BaseActorLoginView):
    actor_model = Admin
    actor_type = ActorType.ADMIN

    def extra_login_fields(self, actor):
        # Lets the admin panel show or hide the super-admin-only Admin
        # Management section. (The server still enforces it on every request.)
        return {"admin_type": actor.type}


class SellerLoginView(BaseActorLoginView):
    actor_model = Seller
    actor_type = ActorType.SELLER

    def inactive_message(self, actor):
        # A self-registered seller still waiting for an admin sees why they
        # cannot get in, instead of a generic "not active".
        if actor.is_seller_request:
            return "Your registration is under review. You can log in once an admin approves it."
        return super().inactive_message(actor)


class SellerRegisterView(APIView):
    """A seller signs up by themselves. Public — no token needed.

    Send multipart/form-data (the NID files make JSON impossible). The account
    is created unverified and inactive and joins the admin's Seller Request
    queue; there is no login token in the response because the seller cannot
    log in until an admin activates the account."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = SellerRegistrationSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            serializer.save()
        return Response(
            {
                **serializer.data,
                "message": "Registration received. An admin will review your documents; "
                "you can log in once your account is approved.",
            },
            status=status.HTTP_201_CREATED,
        )


class BuyerLoginView(BaseActorLoginView):
    actor_model = User
    actor_type = ActorType.USER
