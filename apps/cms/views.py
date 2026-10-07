from rest_framework import status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.authentication.permissions import IsAdminActor
from apps.core.mixins import AuditedViewSetMixin
from apps.core.models import ActorType
from config.storage import delete_upload, save_upload

from .filters import BannerFilter
from .models import Banner, EmailTemplate, Setting
from .serializers import (
    LOGO_PATH_KEY,
    LOGO_URL_KEY,
    RESERVED_SETTING_KEYS,
    BannerSerializer,
    EmailTemplateSerializer,
    SettingSerializer,
    SiteLogoUploadSerializer,
)


class BannerViewSet(AuditedViewSetMixin, viewsets.ModelViewSet):
    """Banner Management — Create / Retrieve / Update / List / Delete.
    Create and update take multipart form data because of the image file.
    Replacing or deleting a banner also removes its old image file."""

    permission_classes = [IsAdminActor]
    queryset = Banner.objects.select_related("category")
    serializer_class = BannerSerializer
    filterset_class = BannerFilter
    search_fields = ["heading", "small_heading"]

    def perform_destroy(self, instance):
        path = instance.image_path
        instance.delete()
        delete_upload(path)


class EmailTemplateViewSet(AuditedViewSetMixin, viewsets.ModelViewSet):
    """Email Templates — full CRUD. `is_active` controls whether the
    application actually sends a template."""

    permission_classes = [IsAdminActor]
    queryset = EmailTemplate.objects.all()
    serializer_class = EmailTemplateSerializer
    filterset_fields = ["is_active"]
    search_fields = ["key", "subject"]


class SettingViewSet(AuditedViewSetMixin, viewsets.ModelViewSet):
    """Site Settings — generic key -> JSON value CRUD, addressed by key
    (`/settings/{key}/`). The site-logo keys can be read here but only
    changed through /site-logo/."""

    permission_classes = [IsAdminActor]
    queryset = Setting.objects.all()
    serializer_class = SettingSerializer
    lookup_field = "key"
    lookup_value_regex = "[a-z][a-z0-9_]*"
    search_fields = ["key"]

    def perform_destroy(self, instance):
        if instance.key in RESERVED_SETTING_KEYS:
            raise ValidationError({"key": "This setting is managed by the site-logo endpoint."})
        instance.delete()


class SiteLogoView(APIView):
    """GET    /site-logo/  -> {"path": ..., "url": ...} (both null when unset)
    POST   /site-logo/  -> multipart `image`; stores a new logo, replacing and
                           deleting the old file (PUT does the same)
    DELETE /site-logo/  -> removes the logo and its file

    The logo lives in two settings rows, `site_logo_path` and `site_logo_url`."""

    permission_classes = [IsAdminActor]

    @staticmethod
    def _current():
        values = dict(Setting.objects.filter(key__in=RESERVED_SETTING_KEYS).values_list("key", "value"))
        return {"path": values.get(LOGO_PATH_KEY), "url": values.get(LOGO_URL_KEY)}

    def get(self, request):
        return Response(self._current())

    def post(self, request):
        serializer = SiteLogoUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        old_path = self._current()["path"]
        path, url = save_upload(serializer.validated_data["image"], "site")

        actor = request.user
        actor_id = getattr(actor, "id", None)
        actor_type = getattr(actor, "actor_type", ActorType.SYSTEM)
        actor_name = getattr(actor, "name", None)
        for key, value in ((LOGO_PATH_KEY, path), (LOGO_URL_KEY, url)):
            setting = Setting.objects.filter(key=key).first()
            if setting is None:
                setting = Setting(key=key, created_by=actor_id, creator_type=actor_type, creator_name=actor_name)
            setting.value = value
            setting.updated_by = actor_id
            setting.updater_type = actor_type
            setting.updater_name = actor_name
            setting.save()

        if old_path and old_path != path:
            delete_upload(old_path)
        return Response(self._current())

    put = post

    def delete(self, request):
        old_path = self._current()["path"]
        Setting.objects.filter(key__in=RESERVED_SETTING_KEYS).delete()
        delete_upload(old_path)
        return Response(status=status.HTTP_204_NO_CONTENT)
