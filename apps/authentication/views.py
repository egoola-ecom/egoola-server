"""
Login — one endpoint per actor table (Admin/Seller/Buyer). All three share
the same flow (BaseActorLoginView below); a subclass only says which model
to check the credentials against, which field identifies the person (Admin and
Buyer log in with email + password, a Seller with phone + password) and which
`actor_type` claim to stamp on the token it issues.
"""

import re

from django.contrib.auth.hashers import check_password
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import Admin, Seller, User
from apps.accounts.serializers import BuyerRegistrationSerializer, SellerRegistrationSerializer
from apps.core.models import ActorType

from .tokens import tokens_for_actor


class LoginInputSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, style={"input_type": "password"})


class SellerLoginInputSerializer(serializers.Serializer):
    phone = serializers.CharField()
    password = serializers.CharField(write_only=True, style={"input_type": "password"})


class BuyerLoginInputSerializer(serializers.Serializer):
    """A buyer logs in with the mobile number they signed up with, or with their
    email when they gave one: send exactly one of `phone` or `email`."""

    phone = serializers.CharField(required=False)
    email = serializers.EmailField(required=False)
    password = serializers.CharField(write_only=True, style={"input_type": "password"})

    def validate(self, attrs):
        if ("phone" in attrs) == ("email" in attrs):
            raise serializers.ValidationError({"phone": "Send either phone or email (one of them)."})
        return attrs


class BaseActorLoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []  # logging in is how you get a token, so it never requires one
    actor_model = None
    actor_type = None
    login_field = "email"  # which column identifies the person: "email", or "phone" for a Seller
    input_serializer = LoginInputSerializer

    def post(self, request):
        serializer = self.input_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        login_field = self.get_login_field(serializer.validated_data)
        identifier = serializer.validated_data[login_field]
        password = serializer.validated_data["password"]
        identifier = self.normalize_identifier(login_field, identifier)

        actor = self.actor_model.objects.filter(**{f"{login_field}__iexact": identifier}).first()
        if actor is None or not check_password(password, actor.password):
            # Same error either way — confirming "no such email/phone" to a
            # client would let anyone probe which accounts are registered.
            raise AuthenticationFailed(self.invalid_message)

        if actor.status not in actor.LOGIN_STATUSES:
            raise AuthenticationFailed("This account is not active.", code="user_inactive")

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

    invalid_message = "Invalid email or password."

    def get_login_field(self, validated_data):
        return self.login_field

    def normalize_identifier(self, login_field, identifier):
        return identifier.strip() if login_field == "phone" else identifier

    def get_authenticate_header(self, request):
        # Login has no authenticator, and DRF turns a 401 into a 403 when
        # there is no authenticator to name in the WWW-Authenticate header.
        # A wrong password or an inactive account is a 401, so say "Bearer".
        return 'Bearer realm="api"'

    def extra_login_fields(self, actor):
        """Extra keys for the login response of one kind of actor."""
        return {}


class AdminLoginView(BaseActorLoginView):
    actor_model = Admin
    actor_type = ActorType.ADMIN

    def extra_login_fields(self, actor):
        # Lets the admin panel show or hide the super-admin-only Admin
        # Management section. (The server still enforces it on every request.)
        return {"admin_type": actor.type}


class SellerLoginView(BaseActorLoginView):
    """A seller logs in with phone number + password (not email)."""

    actor_model = Seller
    actor_type = ActorType.SELLER
    login_field = "phone"
    input_serializer = SellerLoginInputSerializer
    invalid_message = "Invalid phone number or password."

    def extra_login_fields(self, actor):
        # A seller who cannot operate yet (pending, rejected, or approved but
        # paused) can log in but only edit their profile; these tell the app
        # which screens to show.
        return {
            "phone": actor.phone,
            "verification_status": actor.verification_status,
            "status": actor.status,
            "can_operate": actor.can_operate,
        }


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
                "message": "Registration received. An admin will review your documents. "
                "You can log in now to complete your profile; you can start selling once your account is approved and active.",
            },
            status=status.HTTP_201_CREATED,
        )


class BuyerLoginView(BaseActorLoginView):
    """A buyer logs in with phone + password, or with email + password."""

    actor_model = User
    actor_type = ActorType.USER
    input_serializer = BuyerLoginInputSerializer
    invalid_message = "Invalid phone number, email or password."

    def get_login_field(self, validated_data):
        return "phone" if "phone" in validated_data else "email"

    def normalize_identifier(self, login_field, identifier):
        # Registration stores the mobile number without spaces or hyphens.
        return re.sub(r"[\s-]", "", identifier) if login_field == "phone" else identifier

    def extra_login_fields(self, actor):
        return {"phone": actor.phone}


class BuyerRegisterView(APIView):
    """A buyer signs up by themselves. Public — no token needed.

    Required: `name`, `phone`, `password`; everything else is optional (see
    BuyerRegistrationSerializer). JSON, or multipart/form-data when a `profile_pic`
    file is sent. The account is active at once, so the response carries the tokens
    (the buyer is logged in) and the profile."""

    permission_classes = [AllowAny]
    authentication_classes = []
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def post(self, request):
        serializer = BuyerRegistrationSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            buyer = serializer.save()
        refresh = tokens_for_actor(buyer, ActorType.USER)
        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "actor_type": ActorType.USER,
                **{key: value for key, value in serializer.data.items() if key != "password"},
                "message": "Welcome to Egoola. Your account is ready.",
            },
            status=status.HTTP_201_CREATED,
        )
