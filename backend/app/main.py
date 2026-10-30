import os
import json
import numpy as np
import pandas as pd
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

import app.state as state
import app.config as config
from app.agent import run_agent_loop

app = FastAPI(title="Automated Data Analysis Agent API")

# Configure CORS for React frontend (development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure static folder and charts directory exists
static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "static"))
os.makedirs(static_dir, exist_ok=True)
state.init_charts_dir()

# Mount static folder to serve generated charts
app.mount("/static", StaticFiles(directory=static_dir), name="static")

MAX_UPLOAD_BYTES = 50 * 1024 * 1024

class QueryRequest(BaseModel):
    query: str

@app.post("/api/upload")
async def upload_csv(file: UploadFile = File(...)):
    """Uploads a CSV file, stores it in Pandas memory, and returns schema metadata."""
    # Strip any directory components to prevent path traversal
    filename = os.path.basename(file.filename or "")
    if not filename.lower().endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are supported.")

    contents = await file.read()
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 50MB.")

    try:
        # Create temp folder inside workspace for uploads if needed
        upload_dir = os.path.join(os.path.dirname(__file__), "..", "uploads")
        os.makedirs(upload_dir, exist_ok=True)

        file_path = os.path.join(upload_dir, filename)
        with open(file_path, "wb") as f:
            f.write(contents)

        # Load into state DataFrame
        # Low_memory=False to prevent warning for mixed type inference
        state.df = pd.read_csv(file_path, low_memory=False)
        state.file_path = file_path

        # Clean old charts
        if os.path.exists(state.CHARTS_DIR):
            for f in os.listdir(state.CHARTS_DIR):
                if f.endswith(".png"):
                    try:
                        os.remove(os.path.join(state.CHARTS_DIR, f))
                    except OSError:
                        pass

        return {
            "message": "File uploaded successfully.",
            "filename": filename,
            "shape": {"rows": state.df.shape[0], "columns": state.df.shape[1]},
            "columns": list(state.df.columns)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process CSV file: {str(e)}")

@app.post("/api/query")
def query_agent(request: QueryRequest):
    """
    Query endpoint streaming agent execution trace in real-time
    using Server-Sent Events (SSE).
    """
    if state.df is None:
        raise HTTPException(status_code=400, detail="No dataset uploaded yet. Please upload a CSV first.")
        
    def event_stream():
        try:
            for step in run_agent_loop(request.query):
                yield f"data: {json.dumps(step, default=str)}\n\n"
        except Exception as e:
            err = {"type": "error", "content": f"Streaming Error: {str(e)}"}
            yield f"data: {json.dumps(err)}\n\n"
            
    return StreamingResponse(event_stream(), media_type="text/event-stream")

@app.get("/api/dataset")
def get_dataset_preview():
    """Returns shape, columns, and top 100 rows of the dataset as a preview."""
    if state.df is None:
        return {"loaded": False}
        
    try:
        # Load first 100 rows
        head_df = state.df.head(100).copy()

        # Standardize NaN/inf to None for JSON serialization
        head_df = head_df.replace([np.inf, -np.inf], np.nan)
        head_df = head_df.astype(object).where(head_df.notna(), None)

        return {
            "loaded": True,
            "filename": os.path.basename(state.file_path) if state.file_path else "dataset.csv",
            "shape": {"rows": state.df.shape[0], "columns": state.df.shape[1]},
            "columns": list(state.df.columns),
            "dtypes": {str(c): str(t) for c, t in state.df.dtypes.items()},
            "data": head_df.to_dict(orient="records")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve preview: {str(e)}")

@app.delete("/api/dataset")
def clear_dataset():
    """Unloads the current dataset and removes any generated charts."""
    state.df = None
    state.file_path = None
    if os.path.exists(state.CHARTS_DIR):
        for f in os.listdir(state.CHARTS_DIR):
            if f.endswith(".png"):
                try:
                    os.remove(os.path.join(state.CHARTS_DIR, f))
                except OSError:
                    pass
    return {"message": "Dataset cleared."}

@app.get("/api/config")
def get_config_status():
    """Returns status of Groq configuration."""
    return {
        "llm_provider": "groq",
        "model": config.GROQ_MODEL,
        "api_key_configured": bool(config.GROQ_API_KEY)
    }
