"""
Login — one endpoint per actor table (Admin/Seller/Buyer). All three share
the same flow (BaseActorLoginView below); a subclass only says which model
to check the email/password against and which `actor_type` claim to stamp
on the token it issues.
"""

from django.contrib.auth.hashers import check_password
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import Admin, Seller, User
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
            raise AuthenticationFailed("This account is not active.")

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
            }
        )


class AdminLoginView(BaseActorLoginView):
    actor_model = Admin
    actor_type = ActorType.ADMIN


class SellerLoginView(BaseActorLoginView):
    actor_model = Seller
    actor_type = ActorType.SELLER


class BuyerLoginView(BaseActorLoginView):
    actor_model = User
    actor_type = ActorType.USER
