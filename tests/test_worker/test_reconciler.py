import pytest

from app.infrastructure.adapters.mock_aws import MockAWSAdapter
from app.worker.reconciler import ReconcilerLoop


@pytest.fixture
def reconciler():
    adapter = MockAWSAdapter()
    return ReconcilerLoop(adapter)


@pytest.mark.asyncio
async def test_reconciler_happy_path(reconciler):
    payload = {"reason_code": "standard-scale", "target_cpu_cores": 4}
    result = await reconciler.execute_intent("evt-1", "agg-1", payload)
    assert result == "completed"


@pytest.mark.asyncio
async def test_reconciler_throttled_raises_exception_for_retry(reconciler):
    payload = {"reason_code": "trigger-throttle"}
    with pytest.raises(Exception, match="Transient adapter failure: throttled"):
        await reconciler.execute_intent("evt-2", "agg-2", payload)


@pytest.mark.asyncio
async def test_reconciler_partial_failure_triggers_maut_selection(reconciler):
    payload = {"reason_code": "trigger-partial"}
    result = await reconciler.execute_intent("evt-3", "agg-3", payload)
    assert result == "compensating_via_full_revert"


@pytest.mark.asyncio
async def test_reconciler_executes_rollback(reconciler):
    payload = {"reason_code": "auto-compensation:full_revert"}
    result = await reconciler.execute_rollback("evt-4", "agg-4", payload)
    assert result == "rollback_completed"
