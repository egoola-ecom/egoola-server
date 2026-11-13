from rest_framework import serializers

from ..models import Banner


class PublicBannerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Banner
        fields = ["id", "placement", "heading", "small_heading", "link_url", "image_url", "category", "sort_order"]
