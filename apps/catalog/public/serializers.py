from rest_framework import serializers

from apps.core.pagination import BuyerPagePagination

from ..models import Category


class PublicCategorySerializer(serializers.ModelSerializer):
    """One category for browsing. `has_children` says whether there is anything
    to drill into (an active sub-category), so the app can show an arrow."""

    has_children = serializers.BooleanField(read_only=True)

    class Meta:
        model = Category
        fields = ["id", "parent", "type", "name", "name_bn", "slug", "image_url", "sort_order", "has_children"]


class CategoryListQuerySerializer(serializers.Serializer):
    """The query string of the category list: validated, with its defaults."""

    parent_id = serializers.IntegerField(required=False, min_value=1)
    search = serializers.CharField(required=False, allow_blank=True, max_length=100, trim_whitespace=True)
    type = serializers.ChoiceField(required=False, choices=Category.CatalogType.choices)
    page = serializers.IntegerField(required=False, min_value=1)
    page_size = serializers.IntegerField(required=False, min_value=1, max_value=BuyerPagePagination.max_page_size)
