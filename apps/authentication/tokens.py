"""
Builds JWT pairs for our own three actor tables (accounts.Admin/Seller/
User) instead of Django's auth_user — see apps.accounts.models' `User`
docstring for why this project doesn't use `django.contrib.auth` for API
login at all.
"""

from rest_framework_simplejwt.tokens import RefreshToken


def tokens_for_actor(actor, actor_type):
    """Mints a refresh+access token pair for an Admin/Seller/Buyer row.

    Not `RefreshToken.for_user(actor)` — that helper assumes `actor` is
    Django's own AUTH_USER_MODEL and reads settings tied to it. Building a
    blank token and setting claims by hand works the same way for any of
    our three actor tables. `actor_type` (and `actor_id`) is what
    ActorJWTAuthentication reads back on every later request to know which
    table to look the actor up in and, together with `IsAdminActor`, what
    kind of actor is making the request.
    """
    refresh = RefreshToken()
    refresh["actor_type"] = actor_type
    refresh["actor_id"] = actor.id
    refresh["email"] = actor.email
    refresh["name"] = actor.name
    return refresh
