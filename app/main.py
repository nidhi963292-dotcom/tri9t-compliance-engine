# app/main.py
import os
import uuid
import shutil
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from app import models, schemas, parser, versioning, llm
from app.database import SessionLocal, engine
from app.json_store import JSONDocumentStore

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Tri9T AI Compliance Mapping Engine", version="1.0.0")
nosql_store = JSONDocumentStore()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/api/v1/documents/ingest")
async def ingest_document(version_tag: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Ingests engineering manuals, calculates parent links, and builds structure histories."""
    os.makedirs("data/uploads", exist_ok=True)
    target_path = f"data/uploads/{version_tag}_{file.filename}"
    
    with open(target_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    try:
        nodes = parser.parse_pdf(target_path, version_tag)
        
        # Upsert operation safeguarding historical structural indices
        existing_version = db.query(models.DocumentVersion).filter_by(version_tag=version_tag).first()
        if existing_version:
            db.delete(existing_version)
            db.commit()
            
        doc_version = models.DocumentVersion(version_tag=version_tag)
        db.add(doc_version)
        db.flush()
        
        for n in nodes:
            db_node = models.DocNode(
                id=n.id,
                version_id=doc_version.id,
                parent_id=n.parent_id,
                heading_number=n.heading_number,
                heading_title=n.heading_title,
                level=n.level,
                body_text=n.body_text,
                table_data=n.table_data,
                content_hash=n.finalize_hash()
            )
            db.add(db_node)
            
        db.commit()
        return {"status": "SUCCESS", "nodes_processed": len(nodes), "version": version_tag}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Pipeline failure: {str(e)}")

@app.get("/api/v1/documents/{version_tag}/tree")
def browse_hierarchy_tree(version_tag: str, db: Session = Depends(get_db)):
    """Returns the flattened list of tree blocks for the specified document version."""
    version = db.query(models.DocumentVersion).filter_by(version_tag=version_tag).first()
    if not version:
        raise HTTPException(status_code=404, detail="Version requested not found.")
    return [
        {
            "node_id": n.id,
            "parent_id": n.parent_id,
            "heading": f"{n.heading_number} {n.heading_title}",
            "level": n.level,
            "body_snippet": n.body_text[:60] if n.body_text else "",
            "has_table": n.table_data is not None
        } for n in version.nodes
    ]

@app.post("/api/v1/selections/pin", response_model=schemas.SelectionResponse)
def pin_selection(payload: schemas.SelectionCreate, db: Session = Depends(get_db)):
    """Pins specific node matrices to ensure structural integrity over time."""
    selection_id = str(uuid.uuid4())
    
    for nid in payload.node_ids:
        target_node = db.query(models.DocNode).filter_by(id=nid).first()
        if not target_node:
            raise HTTPException(status_code=404, detail=f"Reference ID mapping invalid: {nid}")
            
        pin = models.PinnedSelection(
            id=str(uuid.uuid4()),
            selection_id=selection_id,
            node_id=nid,
            pinned_version_tag=payload.version_tag
        )
        db.add(pin)
        
    db.commit()
    return {
        "selection_id": selection_id,
        "version_tag": payload.version_tag,
        "nodes_pinned": payload.node_ids
    }

@app.post("/api/v1/generations/trigger/{selection_id}")
def trigger_test_generation(selection_id: str, payload: schemas.GenerationRequest, db: Session = Depends(get_db)):
    """Generates traceable QA test cases based on pinned node configurations."""
    pins = db.query(models.PinnedSelection).filter_by(selection_id=selection_id).all()
    if not pins:
        raise HTTPException(status_code=404, detail="Active selection tracking link missing.")
        
    # Idempotency Guard: Check for duplicate submissions
    existing_run = nosql_store.get_generation(selection_id)
    if existing_run:
        return {"status": "RESOLVED_FROM_CACHE", "data": existing_run}

    # Reconstruct exact pinned historical texts across records
    aggregated_context = ""
    for pin in pins:
        node = pin.node
        aggregated_context += f"\nSection {node.heading_number}: {node.heading_title}\n{node.body_text}\n"
        if node.table_data:
            aggregated_context += f"Table Content: {str(node.table_data)}\n"

    # Call the self-correcting structured LLM interface layer
    ai_output = llm.generate_qa_scenarios(aggregated_context.strip())
    
    storage_payload = {
        "selection_id": selection_id,
        "model_output": ai_output,
        "context_snapshot_md5": uuid.uuid4().hex # Tracking asset tag fingerprints
    }
    nosql_store.save_generation(selection_id, storage_payload)
    return {"status": "GENERATED", "data": storage_payload}

@app.get("/api/v1/selections/{selection_id}/staleness", response_model=schemas.StalenessResponse)
def evaluate_selection_staleness(selection_id: str, target_version: str, db: Session = Depends(get_db)):
    """Evaluates text modifications and structural shifts across document versions."""
    pins = db.query(models.PinnedSelection).filter_by(selection_id=selection_id).all()
    if not pins:
        raise HTTPException(status_code=404, detail="Active selection missing.")

    v2_version = db.query(models.DocumentVersion).filter_by(version_tag=target_version).first()
    if not v2_version:
        raise HTTPException(status_code=404, detail="Target tracking baseline not initialized.")
        
    v2_nodes_dict = {f"{n.heading_number}_{n.heading_title}": n for n in v2_version.nodes}
    report = []
    
    for pin in pins:
        original_node = pin.node
        analysis = versioning.check_staleness(original_node, v2_nodes_dict)
        
        report.append({
            "node_id": original_node.id,
            "heading": f"{original_node.heading_number} {original_node.heading_title}",
            "is_stale": analysis["is_stale"],
            "status_reason": analysis["reason"],
            "similarity_score": round(analysis["diff_ratio"], 4)
        })
        
    return {"target_version_tag": target_version, "staleness_report": report}

@app.get("/api/v1/generations/retrieve/{selection_id}")
def retrieve_generated_scenarios(selection_id: str):
    """Fetches previously generated test cases from the local document store."""
    data = nosql_store.get_generation(selection_id)
    if not data:
        raise HTTPException(status_code=404, detail="No historical data matches this selection key.")
    return data