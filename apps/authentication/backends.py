"""
Resolves a JWT to an Admin/Seller/Buyer row instead of Django's own
auth_user. Every access token this project issues (see tokens.py) carries
an `actor_type` claim ("admin"/"seller"/"user") alongside the usual
`actor_id` — this looks the id up in the matching table.
"""

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken

from apps.accounts.models import Admin, Seller, User
from apps.core.models import ActorType

ACTOR_MODELS = {
    ActorType.ADMIN: Admin,
    ActorType.SELLER: Seller,
    ActorType.USER: User,
}


class ActorJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        actor_type = validated_token.get("actor_type")
        actor_id = validated_token.get("actor_id")
        model = ACTOR_MODELS.get(actor_type)
        if model is None or actor_id is None:
            raise InvalidToken("Token does not carry a valid actor_type/actor_id.")

        try:
            actor = model.objects.get(id=actor_id)
        except model.DoesNotExist:
            raise InvalidToken("No such actor for this token.")

        # DRF's IsAuthenticated (and everything downstream) only ever checks
        # `request.user.is_authenticated` — Admin/Seller/User aren't Django
        # auth users and don't have that attribute, so it's set here rather
        # than adding a real model field for something that's only ever
        # True. `actor_type` is set the same way, for IsAdminActor etc.
        actor.is_authenticated = True
        actor.actor_type = actor_type
        return actor
