from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import (
    get_actor_id,
    get_current_user_claims,
    get_db_pool,
    get_subject_context,
    get_tenant_id,
)
from app.domain.schemas import QuarantineResolveRequest
from app.security.abac import SubjectContext, SubjectRole

router = APIRouter(prefix="/api/v1/control", tags=["Control"])


def _is_quarantine_admin(subject: SubjectContext, claims: list[str]) -> bool:
    if subject.role == SubjectRole.SYSTEM:
        return True
    normalized = {claim.strip().lower() for claim in claims}
    return "tenant_admin" in normalized


@router.post("/quarantine/{quarantine_id}/resolve")
async def resolve_quarantine_event(
    quarantine_id: int,
    request: QuarantineResolveRequest,
    tenant_id=Depends(get_tenant_id),
    subject: SubjectContext = Depends(get_subject_context),
    actor_id: str = Depends(get_actor_id),
    actor_claims: list[str] = Depends(get_current_user_claims),
    pool: Any = Depends(get_db_pool),
):
    if not _is_quarantine_admin(subject, actor_claims):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant admin claim required for quarantine resolution.",
        )

    async with pool.acquire() as conn:
        async with conn.transaction():
            row = await conn.fetchrow(
                """
                SELECT quarantine_id, event_id, aggregate_id
                FROM read_model_causality_quarantine
                WHERE quarantine_id = $1 AND tenant_id = $2
                FOR UPDATE
                """,
                quarantine_id,
                tenant_id,
            )
            if row is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Quarantine event not found for tenant.",
                )

            requeued = False
            if request.action == "RETRY_FORCE":
                result = await conn.execute(
                    """
                    UPDATE outbox
                    SET status = 'pending',
                        attempts = 0,
                        last_attempt_at = NULL,
                        processed_at = NULL,
                        error_payload = NULL,
                        payload = COALESCE(payload, '{}'::jsonb)
                                  || jsonb_build_object(
                                      'force_causal_apply', true,
                                      'forced_by', $3::text
                                  ),
                        updated_at = NOW()
                    WHERE event_id = $1 AND tenant_id = $2
                    """,
                    row["event_id"],
                    tenant_id,
                    actor_id,
                )
                requeued = result.endswith(" 1")

            await conn.execute(
                """
                DELETE FROM read_model_causality_quarantine
                WHERE quarantine_id = $1 AND tenant_id = $2
                """,
                quarantine_id,
                tenant_id,
            )

    return {
        "status": "resolved",
        "action": request.action,
        "quarantine_id": quarantine_id,
        "event_id": str(row["event_id"]),
        "aggregate_id": str(row["aggregate_id"]),
        "requeued": requeued,
    }
