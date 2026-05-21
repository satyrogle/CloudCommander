from __future__ import annotations
from typing import List, Literal
from uuid import UUID
class UnauthorizedStateTransitionError(Exception):
    pass

def verify_permission(actor_claims:List[str],required_action:Literal['allocate','freeze','resolve'],target_node_id:UUID)->None:
    if 'admin' in actor_claims:
        return
    required=f"{required_action}:node:{str(target_node_id)}"
    wildcard=f"{required_action}:node:*"
    if required not in actor_claims and wildcard not in actor_claims:
        raise UnauthorizedStateTransitionError(f"Actor lacks '{required_action}' claim for node {target_node_id}")
