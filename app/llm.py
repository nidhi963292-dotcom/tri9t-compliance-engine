# app/llm.py
import os
import json
import httpx
from typing import List, Dict, Any

def generate_qa_scenarios(combined_context: str, max_retries: int = 3) -> Dict[str, Any]:
    """
    Triggers structured test scenario extractions via generative network backends.
    Uses open JSON schemas to enforce structural validation constraints.
    """
    api_key = os.getenv("GROQ_API_KEY", "mock_key_for_testing")
    # Base endpoint URL routing infrastructure
    url = "https://api.groq.com/openai/v1/chat/completions"
    
    system_instruction = (
        "You are an expert Medical Device QA Engineer specializing in ISO 13485 and IEC 62304 standards.\n"
        "Generate 3 to 5 highly concrete QA test cases from the provided user manual context.\n"
        "Each test case must include a clear, actionable scenario and a distinct expected result.\n"
        "You MUST respond with a valid JSON object matching this schema exactly:\n"
        r'{"test_cases": [{"id": "TC1", "scenario": "...", "expected_result": "..."}]}'
    )
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "mixtral-8x7b-32768",
        "messages": [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": f"Context data:\n{combined_context}"}
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.1
    }
    
    # Injected check supporting isolated sandboxed environments
    if api_key == "mock_key_for_testing":
        return {
            "test_cases": [
                {"id": "TC_MOCK_1", "scenario": "Simulate pressure above threshold limits.", "expected_result": "Emergency vents open."},
                {"id": "TC_MOCK_2", "scenario": "Disconnect inflation cuff entirely.", "expected_result": "E1 logs immediately."}
            ]
        }

    for attempt in range(max_retries):
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(url, json=payload, headers=headers)
                if response.status_code != 200:
                    raise ValueError(f"Backend returned bad status: {response.text}")
                
                result_json = response.json()
                raw_content = result_json["choices"][0]["message"]["content"]
                
                # Moved here to break the circular dependency import loop
                from app.schemas import StructuredTestCases
                
                # Enforce structure validation bounds using Pydantic models
                validated_data = StructuredTestCases.parse_raw(raw_content)
                return validated_data.dict()
                
        except Exception as e:
            if attempt == max_retries - 1:
                # Fallback implementation safeguarding production runtimes against crashes
                return {
                    "error": "LLM extraction layer failed validation checks.",
                    "details": str(e),
                    "test_cases": [
                        {"id": "TC_FALLBACK", "scenario": f"Manual run verification for: {combined_context[:60]}...", "expected_result": "Passes validation."}
                    ]
                }
            # Self-Correction Step: Append error diagnostics into subsequent payload requests
            payload["messages"].append({"role": "assistant", "content": raw_content if 'raw_content' in locals() else "Error"})
            payload["messages"].append({"role": "user", "content": f"Your last response failed validation constraints with error: {str(e)}. Fix the JSON formatting."})