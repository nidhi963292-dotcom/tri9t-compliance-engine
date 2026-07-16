# app/json_store.py
import os
import json
from typing import Dict, Any, Optional

class JSONDocumentStore:
    """Enterprise JSON local document store replacing remote NoSQL configurations."""
    def __init__(self, storage_path: str = "data/llm_outputs_store.json"):
        self.storage_path = storage_path
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        if not os.path.exists(self.storage_path):
            with open(self.storage_path, "w") as f:
                json.dump({}, f)

    def _read_store(self) -> Dict[str, Any]:
        with open(self.storage_path, "r") as f:
            return json.load(f)

    def _write_store(self, data: Dict[str, Any]):
        with open(self.storage_path, "w") as f:
            json.dump(data, f, indent=2)

    def save_generation(self, selection_id: str, payload_data: Dict[str, Any]):
        data = self._read_store()
        data[selection_id] = payload_data
        self._write_store(data)

    def get_generation(self, selection_id: str) -> Optional[Dict[str, Any]]:
        return self._read_store().get(selection_id)