from rest_framework.pagination import LimitOffsetPagination


class DefaultPagination(LimitOffsetPagination):
    """Project-wide limit/offset pagination (?limit=&offset=).

    `max_limit` caps what a client can ask for in one request — DRF's own
    default leaves this unset, which would let `?limit=1000000` return an
    entire table in one response and defeat the point of paginating at all.
    """

    max_limit = 100
