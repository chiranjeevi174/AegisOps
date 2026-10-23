import os
from collections.abc import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from aegisops.core.config import get_settings

# Configure test environment tokens for automated testing without committing secrets
os.environ.setdefault(
    "HUMAN_AUTH_TOKENS",
    "aegisops-dev-operator-token:sre-operator-dan:operator+executor+verifier,"
    "aegisops-dev-approver-token:sre-lead-charlie:approver,"
    "aegisops-dev-requester-token:sre-engineer-alice:requester,"
    "aegisops-dev-admin-token:sre-admin-bob:approver+requester+operator+executor+verifier+admin,"
    "aegisops-dev-viewer-token:sre-viewer-dave:viewer",
)
get_settings.cache_clear()
from aegisops.db.base import Base
from aegisops.db.session import get_db
from aegisops.domain.approval import RemediationApproval  # noqa: F401
from aegisops.domain.approval_event import ApprovalEvent  # noqa: F401
from aegisops.domain.execution import RemediationExecution  # noqa: F401
from aegisops.domain.execution_event import ExecutionEvent  # noqa: F401
from aegisops.domain.incident import Incident  # noqa: F401
from aegisops.domain.rollback import RollbackAssessment  # noqa: F401
from aegisops.domain.rollback_event import RollbackEvent  # noqa: F401
from aegisops.domain.verification import ExecutionVerification  # noqa: F401
from aegisops.domain.verification_event import VerificationEvent  # noqa: F401
from aegisops.main import app

TEST_DATABASE_URL = (
    "postgresql+asyncpg://aegisops:aegisops_local@localhost:5433/aegisops_test"
)


@pytest_asyncio.fixture
async def test_context() -> AsyncGenerator:
    engine = create_async_engine(TEST_DATABASE_URL)

    if engine.url.database != "aegisops_test":
        raise RuntimeError("Refusing to modify a non-test database")

    session_factory = async_sessionmaker(
        engine,
        expire_on_commit=False,
    )

    async def override_get_db():
        async with session_factory() as session:
            yield session

    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
            await connection.run_sync(Base.metadata.create_all)

        app.dependency_overrides[get_db] = override_get_db

        transport = ASGITransport(app=app)

        async with AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            yield client, session_factory

    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


@pytest_asyncio.fixture
async def webhook_client(test_context):
    client, session_factory = test_context

    token = get_settings().alertmanager_webhook_token.get_secret_value()

    if not token:
        raise RuntimeError("Configure ALERTMANAGER_WEBHOOK_TOKEN in .env")

    client.headers["Authorization"] = f"Bearer {token}"

    return client, session_factory
