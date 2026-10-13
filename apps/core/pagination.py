from rest_framework.pagination import CursorPagination, LimitOffsetPagination


class DefaultPagination(LimitOffsetPagination):
    """Project-wide limit/offset pagination (?limit=&offset=).

    `max_limit` caps what a client can ask for in one request — DRF's own
    default leaves this unset, which would let `?limit=1000000` return an
    entire table in one response and defeat the point of paginating at all.
    """

    max_limit = 100


class LargeListPagination(LimitOffsetPagination):
    """For dropdown lookups that need the whole list: default 500, max 1000."""

    default_limit = 500
    max_limit = 1000


class DefaultCursorPagination(CursorPagination):
    """Cursor pagination for queue-style lists that grow while an admin is
    working through them (e.g. the Seller Request queue). The response has
    `next` and `previous` links (each carries an opaque `cursor`) and no
    `count`: a row added or removed between two requests never causes a skipped
    or repeated row, which offset paging cannot promise.

    `?limit=` sets the page size (default 20, max 100). The sort comes from the
    view's OrderingFilter (`?ordering=`), falling back to `ordering` below."""

    page_size = 20
    page_size_query_param = "limit"
    max_page_size = 100
    ordering = "-created_at"
