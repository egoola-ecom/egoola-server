from rest_framework import serializers

LOCATION_FIELDS = ("country", "state", "city", "thana")


class LocationNamesMixin(serializers.ModelSerializer):
    """Adds `country_name`/`state_name`/`city_name`/`thana_name`, read-only,
    alongside whichever id fields a serializer already lists. A page
    showing an address only has ids to work with otherwise — it has no way
    to turn `{"country": 126, "state": 13}` into "Feni, Chittagong" without
    a second round trip to the geography endpoints.

    List the ones you want in `Meta.fields` (e.g. add `"country_name"` next
    to `"country"`) — only a level the model actually has should be listed."""

    country_name = serializers.CharField(source="country.name", read_only=True, default=None)
    state_name = serializers.CharField(source="state.name", read_only=True, default=None)
    city_name = serializers.CharField(source="city.name", read_only=True, default=None)
    thana_name = serializers.CharField(source="thana.name", read_only=True, default=None)


class LocationConsistencyMixin:
    """Keeps a record's country / state / city / thana on one branch of the
    geography tree: the state must belong to the country, the city to the
    state, the thana to the city (and each to the higher levels too).

    Only the levels that are actually filled in are compared, so a record
    may name just a country, or a country and a state, and so on. The check
    runs only when a request touches one of the four fields — merged with
    the values already stored on the record — so an unrelated edit is never
    blocked by older data. Serializers that define their own validate()
    without calling super() call `_check_location(attrs)` themselves."""

    def _check_location(self, attrs):
        if not any(field in attrs for field in LOCATION_FIELDS):
            return
        instance = self.instance
        level = {
            field: attrs[field] if field in attrs else getattr(instance, field, None)
            for field in LOCATION_FIELDS
        }
        errors = {}
        for child, parents in (
            ("state", ("country",)),
            ("city", ("state", "country")),
            ("thana", ("city", "state", "country")),
        ):
            child_obj = level[child]
            if child_obj is None:
                continue
            for parent in parents:
                parent_obj = level[parent]
                if parent_obj is not None and getattr(child_obj, f"{parent}_id") != parent_obj.pk:
                    errors[child] = f"This {child} does not belong to the selected {parent}."
                    break
        if errors:
            raise serializers.ValidationError(errors)

    def validate(self, attrs):
        self._check_location(attrs)
        return super().validate(attrs)
