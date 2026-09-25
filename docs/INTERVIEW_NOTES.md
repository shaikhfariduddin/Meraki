# Engineering decisions — interview notes

Answers here are grounded in what's actually implemented, not textbook
definitions. Grown incrementally as each stage is built.

## Why FastAPI?

Async-capable, Pydantic-based request/response validation out of the
box, and auto-generated OpenAPI docs — which matters for a project that
needs to be usable by someone who didn't write it (see the API
Documentation requirement).

## Why SQLAlchemy 2.x?

The 2.0-style `Mapped[]` / `mapped_column()` API gives full type hints
on ORM models, and the ORM cleanly separates the data-access layer
(repositories) from business logic (services) — no raw SQL scattered
through route handlers.

## Why JWT for authentication?

Stateless — the API server doesn't need a session store to verify a
request, which matters since the backend (Render) and frontend
(Vercel) are deployed and scaled independently. Trade-off: a token
can't be revoked before it expires, which is why
`ACCESS_TOKEN_EXPIRE_MINUTES` is kept short (60 min) rather than
issuing long-lived tokens.

## How does RBAC actually work here?

The JWT's `role` claim is set once at login time from `users.role`,
but it is **not** what authorization decisions are based on.
`get_current_user` re-reads the user row from the database on every
request, and `require_role(*roles)` checks `current_user.role` — the
live DB value — against the allowed roles for that endpoint. This
means: (a) the frontend can never smuggle in a role, since the only
role that matters comes from a server-side DB lookup, and (b) an
admin deactivating or demoting a user takes effect on their very next
request, not after their token expires. The cost is one extra DB
query per authenticated request — acceptable at this scale, and
exactly the kind of thing to point at if asked "what would you change
at 10x traffic" (e.g. cache the user row keyed by id with a short TTL,
invalidated on role change).

## What happens if a request has no token, or an invalid/expired one?

`get_current_user` raises `401 Unauthorized` before any route logic
runs (FastAPI resolves dependencies before the endpoint body). A
valid token for the wrong role gets `403 Forbidden` from
`require_role`, not 401 — the request *is* authenticated, it's just
not permitted.

## Why is Inventory a separate table from Product?

Stock changes far more often than name/price/description do, and once
checkout exists, stock updates need row-level locking (`SELECT ...
FOR UPDATE`) without locking the whole product row. Keeping it
separate also means `Product.available_stock` can be a plain Python
property (`self.inventory.available_stock`) rather than a denormalized
column that could drift out of sync.

## Why does approving a seller change their role, but suspending doesn't revert it?

A suspended seller is still fundamentally a seller — just currently
blocked. Reverting their role to CUSTOMER on suspension would be
losing information (were they ever approved?) for no benefit, since
every product-management endpoint checks live SellerProfile.status
(via `get_current_approved_seller`) anyway, not just role. Role
answers "what kind of account is this", status answers "can they act
right now" — conflating them would mean re-deriving one from the
other later.
