import random

from django.utils.text import slugify
from rest_framework import serializers

from .models import City, Country, State, Thana


def _generate_numeric_code():
    """Random 3-digit code used for every geography level's `*_code` field
    (country_code, state_code, city_code, thana_code) — not checked for
    uniqueness, matching the spec these were defined against."""
    return f"{random.randint(0, 999):03d}"


# Every geography model is an AuditedModel — these six columns say who
# created/last-updated the row (apps.core.mixins.AuditedViewSetMixin is what
# actually populates them). Always read-only: the client reports itself via
# its token, never by putting these fields in the request body.
AUDIT_FIELDS = [
    "created_by",
    "creator_type",
    "creator_name",
    "updated_by",
    "updater_type",
    "updater_name",
]


class CountrySerializer(serializers.ModelSerializer):
    """Client only ever sends `name` — slug and country_code are always
    server-generated (see create()/validate_name()). flag_path/flag_url
    aren't accepted from the client yet (no upload step defined for them
    so far), so they're read-only here too."""

    class Meta:
        model = Country
        fields = ["id", "name", "slug", "country_code", "flag_path", "flag_url"] + AUDIT_FIELDS
        read_only_fields = ["slug", "country_code", "flag_path", "flag_url"] + AUDIT_FIELDS

    def validate_name(self, value):
        slug = slugify(value)
        clash = Country.objects.filter(slug=slug)
        if self.instance is not None:
            clash = clash.exclude(pk=self.instance.pk)
        if clash.exists():
            raise serializers.ValidationError("A country with this name already exists.")
        return value

    def create(self, validated_data):
        validated_data["slug"] = slugify(validated_data["name"])
        validated_data["country_code"] = _generate_numeric_code()
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if "name" in validated_data:
            validated_data["slug"] = slugify(validated_data["name"])
        return super().update(instance, validated_data)


class CountryNestedSerializer(serializers.ModelSerializer):
    """Trimmed shape for a parent Country embedded in another resource's
    list rows — just enough to display a name without a separate lookup,
    not the full audit trail."""

    class Meta:
        model = Country
        fields = ["id", "name", "slug", "country_code"]


class StateNestedSerializer(serializers.ModelSerializer):
    class Meta:
        model = State
        fields = ["id", "name", "slug", "state_code"]


class CityNestedSerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = ["id", "name", "slug", "city_code"]


class StateSerializer(serializers.ModelSerializer):
    """Client sends `name` and `country` — slug and state_code are always
    server-generated. A state's name only has to be unique within its own
    country (see validate()), since the same name can legitimately show up
    under two different countries."""

    class Meta:
        model = State
        fields = [
            "id",
            "country",
            "name",
            "slug",
            "state_code",
            "flag_path",
            "flag_url",
        ] + AUDIT_FIELDS
        read_only_fields = ["slug", "state_code", "flag_path", "flag_url"] + AUDIT_FIELDS

    def validate(self, attrs):
        name = attrs.get("name", getattr(self.instance, "name", None))
        country = attrs.get("country", getattr(self.instance, "country", None))
        slug = slugify(name)
        clash = State.objects.filter(country=country, slug=slug)
        if self.instance is not None:
            clash = clash.exclude(pk=self.instance.pk)
        if clash.exists():
            raise serializers.ValidationError(
                {"name": "A state with this name already exists in this country."}
            )
        return attrs

    def create(self, validated_data):
        validated_data["slug"] = slugify(validated_data["name"])
        validated_data["state_code"] = _generate_numeric_code()
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if "name" in validated_data:
            validated_data["slug"] = slugify(validated_data["name"])
        return super().update(instance, validated_data)


class StateListSerializer(StateSerializer):
    """Read-only shape for List — embeds the parent Country instead of just
    its id, so a table/dropdown doesn't need a separate lookup per row."""

    country = CountryNestedSerializer(read_only=True)


class CitySerializer(serializers.ModelSerializer):
    """Client sends `name`, `country` and `state` — slug and city_code are
    always server-generated. A city's name only has to be unique within its
    own state (see validate()); `country` is denormalized alongside `state`
    (DB Redesign 3.1) so it's cross-checked against `state.country` rather
    than trusted on its own."""

    class Meta:
        model = City
        fields = [
            "id",
            "country",
            "state",
            "name",
            "slug",
            "city_code",
            "flag_path",
            "flag_url",
        ] + AUDIT_FIELDS
        read_only_fields = ["slug", "city_code", "flag_path", "flag_url"] + AUDIT_FIELDS

    def validate(self, attrs):
        name = attrs.get("name", getattr(self.instance, "name", None))
        country = attrs.get("country", getattr(self.instance, "country", None))
        state = attrs.get("state", getattr(self.instance, "state", None))

        if state.country_id != country.id:
            raise serializers.ValidationError(
                {"state": "This state does not belong to the selected country."}
            )

        slug = slugify(name)
        clash = City.objects.filter(state=state, slug=slug)
        if self.instance is not None:
            clash = clash.exclude(pk=self.instance.pk)
        if clash.exists():
            raise serializers.ValidationError(
                {"name": "A city with this name already exists in this state."}
            )
        return attrs

    def create(self, validated_data):
        validated_data["slug"] = slugify(validated_data["name"])
        validated_data["city_code"] = _generate_numeric_code()
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if "name" in validated_data:
            validated_data["slug"] = slugify(validated_data["name"])
        return super().update(instance, validated_data)


class CityListSerializer(CitySerializer):
    """Read-only shape for List — embeds the parent Country and State
    instead of just their ids."""

    country = CountryNestedSerializer(read_only=True)
    state = StateNestedSerializer(read_only=True)


class ThanaSerializer(serializers.ModelSerializer):
    """Client sends `name`, `country`, `state` and `city` — slug and
    thana_code are always server-generated. A thana's name only has to be
    unique within its own city (see validate()); `country`/`state` are
    denormalized alongside `city` (DB Redesign 3.1) so they're cross-checked
    against `city.state`/`city.state.country` rather than trusted on their
    own."""

    class Meta:
        model = Thana
        fields = [
            "id",
            "country",
            "state",
            "city",
            "name",
            "slug",
            "thana_code",
            "flag_path",
            "flag_url",
        ] + AUDIT_FIELDS
        read_only_fields = ["slug", "thana_code", "flag_path", "flag_url"] + AUDIT_FIELDS

    def validate(self, attrs):
        name = attrs.get("name", getattr(self.instance, "name", None))
        country = attrs.get("country", getattr(self.instance, "country", None))
        state = attrs.get("state", getattr(self.instance, "state", None))
        city = attrs.get("city", getattr(self.instance, "city", None))

        if city.state_id != state.id:
            raise serializers.ValidationError(
                {"city": "This city does not belong to the selected state."}
            )
        if state.country_id != country.id:
            raise serializers.ValidationError(
                {"state": "This state does not belong to the selected country."}
            )

        slug = slugify(name)
        clash = Thana.objects.filter(city=city, slug=slug)
        if self.instance is not None:
            clash = clash.exclude(pk=self.instance.pk)
        if clash.exists():
            raise serializers.ValidationError(
                {"name": "A thana with this name already exists in this city."}
            )
        return attrs

    def create(self, validated_data):
        validated_data["slug"] = slugify(validated_data["name"])
        validated_data["thana_code"] = _generate_numeric_code()
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if "name" in validated_data:
            validated_data["slug"] = slugify(validated_data["name"])
        return super().update(instance, validated_data)


class ThanaListSerializer(ThanaSerializer):
    """Read-only shape for List — embeds the parent Country, State and City
    instead of just their ids."""

    country = CountryNestedSerializer(read_only=True)
    state = StateNestedSerializer(read_only=True)
    city = CityNestedSerializer(read_only=True)
