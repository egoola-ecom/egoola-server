"""
Geography reference data — DB Redesign document, Section 3.1.

Four-level location hierarchy (country -> state -> city -> thana), seeded
once at install time. Every address field elsewhere in the system (on
admins, sellers, users, listings, orders...) points into this chain.

This redesign replaces the legacy `unions` / `upazilas` pair with a single
`Thana` table: `unions` (~5,246 rows) was the table every real `thana_id`
column actually pointed to, and `upazilas` (~560 rows) was a dormant,
never-written duplicate — see egoola_db_structure.md Section 4 for the
original evidence. Every `thana_id` column going forward is a real,
enforced foreign key into this table.
"""

from django.db import models

from apps.core.models import AuditedModel


class Country(AuditedModel):
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    country_code = models.CharField(db_column="countryCode", max_length=10)
    flag_path = models.CharField(db_column="flagPath", max_length=255, null=True, blank=True)
    flag_url = models.URLField(db_column="flagUrl", max_length=500, null=True, blank=True)

    class Meta:
        db_table = "countries"
        ordering = ["name"]
        verbose_name_plural = "countries"

    def __str__(self):
        return self.name


class State(AuditedModel):
    country = models.ForeignKey(
        Country, on_delete=models.CASCADE, related_name="states", db_column="countryId"
    )
    name = models.CharField(max_length=255)
    # Not globally unique — the same state name legitimately recurs under
    # different countries, so redundancy is only checked within one country
    # (see StateSerializer.validate()); this constraint backs that up at
    # the DB level.
    slug = models.SlugField(max_length=255)
    state_code = models.CharField(db_column="stateCode", max_length=20)
    flag_path = models.CharField(db_column="flagPath", max_length=255, null=True, blank=True)
    flag_url = models.URLField(db_column="flagUrl", max_length=500, null=True, blank=True)

    class Meta:
        db_table = "states"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["country", "slug"], name="unique_state_slug_per_country")
        ]

    def __str__(self):
        return self.name


class City(AuditedModel):
    # country is denormalized alongside state so a city can be filtered by
    # country directly, without joining through State (DB Redesign 3.1).
    country = models.ForeignKey(
        Country, on_delete=models.CASCADE, related_name="cities", db_column="countryId"
    )
    state = models.ForeignKey(
        State, on_delete=models.CASCADE, related_name="cities", db_column="stateId"
    )
    name = models.CharField(max_length=255)
    # Not globally unique — the same city name legitimately recurs under
    # different states, so redundancy is only checked within one state
    # (see CitySerializer.validate()).
    slug = models.SlugField(max_length=255)
    city_code = models.CharField(db_column="cityCode", max_length=20)
    flag_path = models.CharField(db_column="flagPath", max_length=255, null=True, blank=True)
    flag_url = models.URLField(db_column="flagUrl", max_length=500, null=True, blank=True)

    class Meta:
        db_table = "cities"
        ordering = ["name"]
        verbose_name_plural = "cities"
        constraints = [
            models.UniqueConstraint(fields=["state", "slug"], name="unique_city_slug_per_state")
        ]

    def __str__(self):
        return self.name


class Thana(AuditedModel):
    # country/state are denormalized alongside city for direct filtering at
    # any level without joining all the way down (DB Redesign 3.1).
    country = models.ForeignKey(
        Country, on_delete=models.CASCADE, related_name="thanas", db_column="countryId"
    )
    state = models.ForeignKey(
        State, on_delete=models.CASCADE, related_name="thanas", db_column="stateId"
    )
    city = models.ForeignKey(
        City, on_delete=models.CASCADE, related_name="thanas", db_column="cityId"
    )
    name = models.CharField(max_length=255)
    # Not globally unique — the same thana name legitimately recurs under
    # different cities, so redundancy is only checked within one city
    # (see ThanaSerializer.validate()).
    slug = models.SlugField(max_length=255)
    thana_code = models.CharField(db_column="thanaCode", max_length=20)
    flag_path = models.CharField(db_column="flagPath", max_length=255, null=True, blank=True)
    flag_url = models.URLField(db_column="flagUrl", max_length=500, null=True, blank=True)

    class Meta:
        db_table = "thanas"
        ordering = ["name"]
        verbose_name_plural = "thanas"
        constraints = [
            models.UniqueConstraint(fields=["city", "slug"], name="unique_thana_slug_per_city")
        ]

    def __str__(self):
        return self.name
