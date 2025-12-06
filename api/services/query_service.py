import os
from typing import Dict, Any
from orchestrator_new import answer_user_query
print("query_service.py loaded")
def query_answer_sevice(query_payload: Dict[str, Any]) -> Dict[str, Any]:
    if "query" not in query_payload:
        raise ValueError("query_payload must include 'query'")
    
    query = query_payload["query"]
    user_id= query_payload["user_id"]
    
    response = answer_user_query(query,user_id)
    
    return response