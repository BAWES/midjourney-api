# Coding Conventions: midjourney-api

> AI Agents will reference this document to maintain consistency.

## Naming Conventions

- **Files**: snake_case for Python modules (e.g., `task_service.py`, `correlation.py`)
- **Variables**: snake_case (e.g., `api_key_id`, `dispatch_queue`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `MJ_APP_ID`, `COMMAND_CACHE_TTL`, `VALID_TRANSITIONS`)
- **Classes**: PascalCase (e.g., `TaskService`, `ConcurrencyLimiter`)
- **Enums**: PascalCase class, UPPER_SNAKE_CASE members (e.g., `TaskStatus.QUEUED`)
- **DB Tables**: snake_case plural (e.g., `api_keys`, `quota_usages`)
- **Indexes**: `ix_{table}_{columns}` (e.g., `ix_tasks_api_key_created`)
- **Unique constraints**: `uq_{description}` (e.g., `uq_api_key_date`)

## Code Patterns (Follow)

- Use `async/await` for all database and I/O operations
- Use `Mapped[]` type annotations for all SQLAlchemy columns (2.x style)
- Use `from_attributes=True` in Pydantic models that serialize ORM objects
- Use FastAPI `Depends()` for dependency injection in endpoints
- Use `uuid.UUID` for all primary keys and foreign keys
- Use `secrets.token_hex()` for cryptographic randomness (not `uuid4().hex`)
- Use `datetime.now(timezone.utc)` instead of `datetime.utcnow()`
- Use `hmac.new()` with configurable secret for API key hashing
- Use Protocol for duck-typing across provider implementations
- Use composition over inheritance for complex classes
- Commit then refresh after all DB mutations
- Place input validation at service boundary (not in ORM models)

## Code Patterns (Avoid)

- Avoid `datetime.utcnow()` — deprecated, use `datetime.now(timezone.utc)`
- Avoid raw `hashlib.sha256` for secrets — use `hmac` with a secret key
- Avoid `uuid.uuid4().hex[:N]` for security tokens — use `secrets.token_hex()`
- Avoid catching exceptions silently — always log or re-raise
- Avoid releasing semaphore in multiple places — single ownership pattern
- Avoid `--param` flags in user prompts — strip via regex
- Avoid circular imports — use module-level DI (`set_dependencies()` pattern)

## Error Handling

- Custom exceptions in `src/app/exceptions.py`: `TaskNotFoundError`, `QuotaExceededError`, `InvalidStateTransitionError`
- Exception handlers in `main.py` map to HTTP status: 404, 429, 409
- Services raise domain exceptions; API layer translates to HTTP
- `dispatch_one` re-raises after transitioning task to FAILED; wrapper handles semaphore release

## Testing Conventions

- Framework: pytest + pytest-asyncio
- Unit tests: `tests/unit/` — services, concurrency, discord parsing, auth
- Integration tests: `tests/integration/` — full API endpoint tests via httpx AsyncClient
- Fixtures: `tests/conftest.py` — shared DB session, API keys, test client
- Use `hash_api_key()` from `deps.py` for consistent test key hashing
- SQLite in-memory for tests; wrap PostgreSQL-specific features in try/except

## Git Conventions

- Conventional commits: `feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`
- English commit messages
- Feature branches for non-trivial changes
