import pytest

from app.infrastructure.adapters.mock_aws import MockAWSAdapter


@pytest.mark.asyncio
async def test_mock_adapter_explicit_reason_code_overrides_chaos():
    adapter = MockAWSAdapter(
        chaos_enabled=True,
        chaos_r=3.95,
        chaos_x=0.91,
        chaos_min_delay_sec=0.0,
        chaos_max_delay_sec=0.0,
    )

    result = await adapter.apply_allocation("agg-1", {"reason_code": "trigger-timeout"})

    assert result["status"] == "timeout"
    assert "Connection timed out" in result["provider_message"]


@pytest.mark.asyncio
async def test_mock_adapter_chaos_mode_emits_transient_failures():
    adapter = MockAWSAdapter(
        chaos_enabled=True,
        chaos_r=3.95,
        chaos_x=0.91,
        chaos_min_delay_sec=0.0,
        chaos_max_delay_sec=0.0,
    )

    statuses = []
    for _ in range(6):
        result = await adapter.apply_allocation("agg-1", {"reason_code": "standard-scale"})
        statuses.append(result["status"])

    assert any(status in {"partial_failure", "throttled", "timeout"} for status in statuses)
