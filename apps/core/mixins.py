from apps.core.models import ActorType


class AuditedViewSetMixin:
    """Stamps the shared creator_*/updater_* columns every AuditedModel
    subclass has (apps.core.models.AuditedModel) from the actor making the
    request. Nothing populates these automatically — request.user is the
    Admin/Seller/User row itself (see ActorJWTAuthentication), so `.id` and
    `.name` are read straight off it."""

    def perform_create(self, serializer):
        actor = self.request.user
        serializer.save(
            created_by=getattr(actor, "id", None),
            creator_type=getattr(actor, "actor_type", ActorType.SYSTEM),
            creator_name=getattr(actor, "name", None),
        )

    def perform_update(self, serializer):
        actor = self.request.user
        serializer.save(
            updated_by=getattr(actor, "id", None),
            updater_type=getattr(actor, "actor_type", ActorType.SYSTEM),
            updater_name=getattr(actor, "name", None),
        )
