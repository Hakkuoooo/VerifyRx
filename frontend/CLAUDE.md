@AGENTS.md

## How to Work

- Read existing code before changing anything
- Explain your approach in 1–2 sentences before implementing
- Make small, focused changes — not big rewrites
- Run tests/typecheck after changes before saying "done"
- If something seems wrong with my request, ask before proceeding
- Don't add dependencies without asking first

## Don't Do This

- Don't add dependencies without asking
- Don't over-engineer when simple works
- Don't change code style without a reason
- Don't give long explanations when short ones work
- Don't generate flashy demos that break in production
- Don't assume I need hand-holding — but do explain what's happening

### Code Safety

- NEVER hardcode database connection strings, webhook URLs, or third-party service endpoints in source files — use env vars
- NEVER log sensitive data (tokens, passwords, user PII) to the console, even in development
- NEVER disable authentication or security middleware "temporarily" — if it needs to be off, flag it and explain why
- ALWAYS validate and sanitize user input before using it in queries, APIs, or rendered output
- ALWAYS use parameterized queries — never concatenate user input into SQL strings

All code must follow these security practices:

**Input & Validation**
- Validate all user input at API edge with Zod schemas (`server/src/middleware/schemas.js`)
- Use `validateBody()` middleware on every route that accepts input
- Use `.strict()` on Zod schemas to reject unexpected fields
- Sanitize free-text fields with the `xss` library before storage
- Never trust client-supplied IDs — always verify ownership via `req.user.id`

**Authentication & Authorization**
- Every non-public route must use `authenticateToken` middleware
- Always verify resource ownership (e.g., `where: { id, userId }`) — never fetch by ID alone
- Use constant-time comparison for secrets (bcrypt handles this for passwords)
- Never log tokens, passwords, or secrets — Winston logger masks sensitive fields

**Database**
- Use Prisma's parameterized queries exclusively — never use `$queryRawUnsafe`
- Always scope queries to the authenticated user (include `userId` in where clauses)
- Use `select`/`include` to return only needed fields — never return password hashes

**URLs & External Requests**
- Validate URLs against an allowlist of known domains before server-side fetching
- Reject private/reserved IPs (127.0.0.0/8, 10.0.0.0/8, 172.16.0.0/12, 169.254.0.0/16) to prevent SSRF
- Use `server/src/utils/urlValidator.js` for URL validation
- Set timeouts and response size limits on all outbound HTTP requests

**Frontend**
- Never use `dangerouslySetInnerHTML` with dynamic content
- Never store sensitive data beyond auth tokens in localStorage/sessionStorage
- Sanitize any data rendered from external sources

**API Responses**
- Never expose stack traces in production (the global error handler already masks these)
- Never return sensitive fields (passwordHash, tokens) in API responses
- Use appropriate HTTP status codes (401 vs 403 vs 404)

**Rate Limiting**
- All new routes under `/api/*` inherit the global rate limiter
- AI/expensive operations must use `aiOperationLimiter`
- Auth endpoints (login, signup, OAuth) must use their specific limiters
