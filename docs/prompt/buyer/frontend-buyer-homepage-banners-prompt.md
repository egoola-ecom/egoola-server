# Brief for the Egoola Web session — wire the homepage hero banner to the real API

Backend done and tested in `egoola-server`: a public, no-login endpoint that returns the admin's active
homepage banners. `HomeScreen` (`src/components/shop/home-screen.tsx`) already has a working hero carousel —
it's just pointed at a hardcoded `BANNERS` array of two static image paths (line 24). This brief is a
**wire-up, not a new build**: replace that hardcoded array with a real API call, and make each slide a link
using the banner's `link_url`. Do not push; commit locally only if asked.

Read first: `egoola-server/docs/admin/cms-api-guide.md` section 5 (the technical contract below is a copy of
it). No Postman collection for this one yet — it's a single `GET`, test it with `curl` or the browser. Run the
backend with `uv run manage.py runserver 8000`. No login needed.

---

## 1. What this is

```
GET /api/v1/public/cms/banners/
GET /api/v1/public/cms/banners/?placement=hero
```
No auth header needed; a stale/expired token sent by mistake is ignored, never `401`. `200`, a **plain list**
(no `count`/`results` wrapper, no pagination):
```json
[
  { "id": 105, "placement": "hero", "heading": "Big Autumn Sale", "small_heading": "Up to 50% off",
    "link_url": "http://localhost:3000/products", "image_url": "/media/banners/580ebafe….png",
    "category": null, "sort_order": 1 }
]
```
Already ordered by `placement`, then `sort_order` — render in the order the array comes back, no client-side
sort needed. Only banners that are **live right now** (admin status `active`, and inside its scheduling window
if one is set) come back at all — nothing to filter again on this side.

`placement` is one of `hero` | `sidebar` | `category`. The home page's carousel is `hero` — filter the call to
`?placement=hero` so a sidebar/category banner (added later, no UI slot for it yet) never shows up here by
accident.

`link_url` is whatever the admin typed: sometimes a path on this site (`/categories/electronics`), sometimes a
full URL (`http://localhost:3000/products`, or someday an external one). It can also be empty/`null` — a purely
decorative banner with nothing to click through to.

`image_url` is server-relative (e.g. `/media/banners/….png`) — resolve it the same way every other listing
image on this site already does (`resolveMediaUrl`, used elsewhere in `home-screen.tsx` and the gig/listing
cards), don't build a second resolver.

## 2. Task

1. **API client**: add `listBanners(params?: { placement?: "hero" | "sidebar" | "category" })` next to the
   other public buyer API functions (see `src/lib/buyer/public-categories-api.ts` for the shape of a simple
   public GET — no auth, no paging).
2. **Replace the hardcoded array**: in `HomeScreen`, drop the `BANNERS` constant and load hero banners via
   `useEffect` the same way `listCategories`/`listGigs` already load there — "each block loads on its own, one
   failing call must not blank the page" (see the comment right above the existing `useEffect` block).
3. **Make each slide a link**: wrap each `<img>` in the carousel with a link to that banner's `link_url`.
   - Empty/`null` `link_url` → no wrapping link, just the image (don't render a dead/empty `<a>`).
   - A same-site path (starts with `/`) → use Next's `Link`, like every other internal link on this page.
   - A full URL to another host → plain `<a href=...>`, `target="_blank" rel="noopener noreferrer"` (don't
     navigate the buyer away from the SPA into a different origin in the same tab).
   - A full URL on **this same site's own origin** (like the test data above,
     `http://localhost:3000/products`) → still works fine as a plain `<a>`; don't overbuild a same-origin
     detector just to swap it to `Link` — only the empty vs. non-empty and relative vs. absolute checks matter.
4. **Empty state**: if the list comes back empty (no active hero banners), hide the whole `banner-area` block
   rather than rendering an empty carousel — `OwlCarousel` with zero children is likely to render oddly.
5. **Alt text**: use the banner's `heading` for the image's `alt`, falling back to `"Banner"` (the current
   hardcoded value) when it's empty — better for accessibility than a static string on every slide.

Out of scope for this brief: there's no sidebar or category-placement banner slot in the UI yet — don't invent
one. If/when that's wanted, it's the same endpoint with `?placement=sidebar`, a separate brief.

## 3. Verify (browser; record results)

| # | Case | Expected |
|---|---|---|
| 1 | Home page loads with at least one active hero banner in the dev DB | carousel shows it, same visual style as before |
| 2 | Click a slide whose `link_url` is a same-site path | navigates there, no full page reload |
| 3 | Click a slide whose `link_url` is an external URL | opens in a new tab |
| 4 | A banner with `link_url` empty/null | renders, not clickable, no console error |
| 5 | No active hero banners at all (deactivate them via the admin panel to test) | banner area doesn't render; rest of the home page is unaffected |
| 6 | One backend call fails (e.g. stop the server briefly) | the rest of the home page (categories, gigs) still renders — this block fails on its own |

Report which cases pass, what you changed, and anything in the backend docs that looked wrong or unclear once
you tried it against the real API.
