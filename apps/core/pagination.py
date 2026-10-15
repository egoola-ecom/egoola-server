from rest_framework.response import Response
from rest_framework.pagination import CursorPagination, LimitOffsetPagination, PageNumberPagination


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


class BuyerPagePagination(PageNumberPagination):
    """Page-based pagination for every Buyer Panel list: `?page=1&page_size=20`.

    `page` starts at 1; `page_size` defaults to 20 and is capped at 100. The
    response is `{count, page, page_size, total_pages, results}`: the client
    loads more while `page < total_pages` (no `next` / `previous` links). No
    matches is `count: 0`, `total_pages: 0`, `results: []`. A page past the last
    one is `404` (`{"detail": "Invalid page."}`)."""

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response(
            {
                "count": self.page.paginator.count,
                "page": self.page.number,
                "page_size": self.get_page_size(self.request),
                "total_pages": self.page.paginator.num_pages if self.page.paginator.count else 0,
                "results": data,
            }
        )

    def get_paginated_response_schema(self, schema):
        return {
            "type": "object",
            "required": ["count", "page", "page_size", "total_pages", "results"],
            "properties": {
                "count": {"type": "integer", "example": 11},
                "page": {"type": "integer", "example": 2},
                "page_size": {"type": "integer", "example": 2},
                "total_pages": {"type": "integer", "example": 6},
                "results": schema,
            },
        }
