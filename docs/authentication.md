# Authentication, Roles, and Public Routes — Plain-English Guide

This explains how login, permissions, and public access work in this
backend, without assuming you already know Django or DRF. It matches the
code exactly as it exists today — file paths are given so you can open
the real thing alongside this.

---

## 1. How JWT login works here

### The problem it solves

An API has no memory between requests. Every single request — "get me
the seller list", "update this admin's status" — arrives on its own,
with no idea who's asking. JWT (JSON Web Token) is how the client proves
"it's still me" on every request, without sending a password every time.

### Step by step

**Step 1 — Login.** The client sends an email and password to one of
three endpoints:

- `POST /api/v1/auth/admin/login/`
- `POST /api/v1/auth/seller/login/`
- `POST /api/v1/auth/buyer/login/`

(code: [`apps/authentication/views.py`](../apps/authentication/views.py))

The server checks the email/password against the right table (`Admin`,
`Seller`, or `User` — buyers are stored in a table called `User`, see
[`apps/accounts/models.py`](../apps/accounts/models.py)). If it matches,
the server hands back two tokens:

```json
{
  "access": "eyJhbGciOi...",
  "refresh": "eyJhbGciOi...",
  "actor_type": "admin",
  "id": 10,
  "name": "Test Admin",
  "email": "test.admin@egoola.com"
}
```

**Step 2 — The client stores the `access` token** and sends it on every
later request, in a header:

```
Authorization: Bearer eyJhbGciOi...
```

**Step 3 — What's actually inside a token.** A JWT looks like gibberish
but it's really just three parts glued with dots:
`header.payload.signature`. The middle part (payload) is plain,
readable data — you can decode it yourself, it's not a secret. For our
tokens it looks like:

```json
{
  "actor_type": "admin",
  "actor_id": 10,
  "email": "test.admin@egoola.com",
  "name": "Test Admin",
  "exp": 1790339352
}
```

Since anyone can read this, the security doesn't come from hiding it —
it comes from the third part, the **signature**. The signature is a
scramble of the payload plus a secret key that only the server knows
(`SIMPLE_JWT["SIGNING_KEY"]` in
[`config/settings.py`](../config/settings.py)). If a client edited
`"actor_type": "seller"` to `"actor_type": "admin"` by hand, the
signature would no longer match, and the server throws the token out
immediately.

**Step 4 — Every request re-checks the token, and re-checks the
database.** This is the part that's easy to miss: the server doesn't
just trust the payload. On every request, it:

1. Checks the signature is genuine and the token hasn't expired.
2. Reads `actor_id` and `actor_type` from the payload.
3. Actually looks that row up in the database — `Admin.objects.get(id=10)`,
   for example.

That third step matters. Say an Admin gets suspended right now, mid-day
— their token is still validly signed and not expired, but the very
next request they make fails, because the lookup in step 3 no longer
finds an active account. The token is a claim ("I was Admin #10 at
login time"); the database lookup is what keeps that claim honest a
minute, an hour, or a day later.

This whole lookup lives in one file:
[`apps/authentication/backends.py`](../apps/authentication/backends.py),
in a class called `ActorJWTAuthentication`.

**Step 5 — Refreshing.** Access tokens expire after 1 hour
(`ACCESS_TOKEN_LIFETIME`). Instead of logging in again, the client
sends its `refresh` token (valid 14 days) to
`POST /api/v1/auth/token/refresh/` and gets a new access token back —
with the same `actor_type`/`actor_id` carried over automatically.

### Why not just use Django's built-in login?

Django ships with its own `auth_user` table and login system. This
project deliberately doesn't use it for the API — Admins, Sellers, and
Buyers are three separate tables with their own rules (only Admin/Seller
track a "last logged in" time, only Seller has a verification status,
etc.). `ActorJWTAuthentication` is what makes a normal JWT library work
against three different tables instead of Django's one.

---

## 2. How role-based access works here

### The idea in one sentence

Knowing *who* someone is (authentication) and deciding *what they're
allowed to do* (permission) are two separate checks, done one after the
other, every request.

### The two checks

1. **Authentication** — "who is this?" `ActorJWTAuthentication` answers
   this. It sets `request.user` to the actual `Admin`/`Seller`/`User`
   row that matches the token. If there's no token, or it's invalid,
   `request.user` becomes an anonymous placeholder instead — nobody.

2. **Permission** — "is *this* person allowed *here*?" This runs next,
   using whatever role the person turned out to have.

### Where the role check lives

[`apps/authentication/permissions.py`](../apps/authentication/permissions.py)
has three small classes:

```python
class IsAdminActor(_IsActor):
    actor_type = ActorType.ADMIN

class IsSellerActor(_IsActor):
    actor_type = ActorType.SELLER

class IsBuyerActor(_IsActor):
    actor_type = ActorType.USER
```

Each one just asks: "does this request's role match the one I care
about?" A view (an endpoint, roughly) picks which one applies to it:

```python
class AdminViewSet(ModelViewSet):
    permission_classes = [IsAdminActor]
```

This line is the entire rule for "only an Admin can manage
Admins/Sellers/Buyers." If a Seller's or Buyer's token hits this
endpoint, the role check fails and they get rejected — same code path,
just a different answer.

### The two failure codes, and why they're different

- **No token at all → `401 Unauthorized`.** "I don't know who you are."
- **Valid token, wrong role → `403 Forbidden`.** "I know exactly who you
  are, and the answer is no."

This distinction is standard across almost every web API, not something
specific to this project — a `401` means "log in first," a `403` means
"logging in won't help, you're just not allowed."

### What's actually protected today

Only Admin/Seller/Buyer *management* (an Admin creating, editing, or
listing Seller and Buyer records —
[`apps/accounts/views.py`](../apps/accounts/views.py)) uses
`IsAdminActor` right now. `IsSellerActor` and `IsBuyerActor` already
exist and work exactly the same way, but nothing uses them yet, because
Sellers and Buyers don't have any of their own routes yet (their own
product listings, their own orders, etc. — those apps haven't been
built). The moment one of those routes is built, locking it to "only
that Seller" is the same one-line pattern:
`permission_classes = [IsSellerActor]`.

---

## 3. How public routes work here

### The default is "locked," not "open"

Project-wide, every endpoint requires a valid, real token unless it says
otherwise (`DEFAULT_PERMISSION_CLASSES` in
[`config/settings.py`](../config/settings.py)). A "public" route is one
that explicitly opts back out of that default — it's an exception you
have to ask for, not something that happens by accident.

### How a route opts out

The three login views are the working example of this today
([`apps/authentication/views.py`](../apps/authentication/views.py)):

```python
class BaseActorLoginView(APIView):
    permission_classes = [AllowAny]     # anyone can call this, logged in or not
    authentication_classes = []         # don't even try to read a token
```

This makes sense for login specifically — you obviously can't require
someone to already have a token in order to get one.

### A second kind of "public": open, but aware of who's logged in

Sometimes a route should be open to everyone, but behave a little
differently if the caller happens to be logged in — e.g., a product
page anyone can view, but with a filled-in "wishlisted" heart icon only
if you're a logged-in Buyer who saved it. For this, keep the normal
authentication turned on, and only change the permission:

```python
permission_classes = [AllowAny]
# authentication_classes left as the project default
```

Here's the detail that makes this safe: when no token is sent,
`request.user` doesn't become `None` — Django gives it a stand-in
"anonymous" object instead. That stand-in doesn't have an `actor_type`,
but the permission classes never assume it does — they ask for it
carefully (`getattr(request.user, "actor_type", None)`), so a missing
role just quietly becomes "no role," instead of crashing the request.
The same trick lets ordinary view code check "is anyone logged in, and
if so, who" with one line, without a separate branch for the anonymous
case.

### A third kind: public to read, protected to change

A common shape for something like a product catalog: anyone can browse
(`GET`), but only the Seller who owns a listing can edit it
(`PATCH`/`DELETE`). This is a permission class that treats read requests
differently from write requests:

```python
from rest_framework.permissions import SAFE_METHODS

class IsSellerOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:   # GET/HEAD/OPTIONS
            return True
        return getattr(request.user, "actor_type", None) == ActorType.SELLER
```

`SAFE_METHODS` just means "methods that only read, never change
anything." Nothing in the project uses this pattern yet — it's here as
the template for whenever a catalog-style public-read endpoint gets
built.

---

## Quick reference

| Question | Answered by |
|---|---|
| How is a token created at login? | [`apps/authentication/tokens.py`](../apps/authentication/tokens.py) |
| How is a token turned back into "who is this"? | [`apps/authentication/backends.py`](../apps/authentication/backends.py) |
| How is "what role is allowed here" decided? | [`apps/authentication/permissions.py`](../apps/authentication/permissions.py) |
| Where do the login endpoints live? | [`apps/authentication/views.py`](../apps/authentication/views.py) + [`apps/authentication/urls.py`](../apps/authentication/urls.py) |
| Where is the project-wide "locked by default" rule set? | `REST_FRAMEWORK` in [`config/settings.py`](../config/settings.py) |
