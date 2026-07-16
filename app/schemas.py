# app/schemas.py
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class SelectionCreate(BaseModel):
    node_ids: List[str] = Field(..., description="Target node identities to combine into a pinned selection context")
    version_tag: str = Field(..., description="Document version identifier tag (e.g. v1, v2)")

class SelectionResponse(BaseModel):
    selection_id: str
    version_tag: str
    nodes_pinned: List[str]

class GenerationRequest(BaseModel):
    system_prompt: Optional[str] = Field(None, description="Custom prompt adjustments for validation checks")

class TestCaseItem(BaseModel):
    id: str = Field(..., description="Unique deterministic test index mapping tag")
    scenario: str = Field(..., description="Concrete verification condition sequence description")
    expected_result: str = Field(..., description="System response requirement condition status")

class StructuredTestCases(BaseModel):
    test_cases: List[TestCaseItem] = Field(..., description="List of generated QA validation test cases")

class StalenessCheckItem(BaseModel):
    node_id: str
    heading: str
    is_stale: bool
    status_reason: str # UNCHANGED, MODIFIED, DELETED
    similarity_score: float

class StalenessResponse(BaseModel):
    target_version_tag: str
    staleness_report: List[StalenessCheckItem]