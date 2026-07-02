"""
Knowledge Base Tools — Vector search + incident memory search
Uses ChromaDB for semantic similarity search
"""
import chromadb
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import os
from loguru import logger


def get_chroma_client():
    host = os.getenv("CHROMA_HOST", "chromadb")
    port = int(os.getenv("CHROMA_PORT", "8000"))
    return chromadb.HttpClient(host=host, port=port)


# ─────────────────────────────────────────────
# Knowledge Base Search (SOP, FAQ, Docs)
# ─────────────────────────────────────────────
class KnowledgeSearchInput(BaseModel):
    query: str = Field(..., description="Search query — describe the issue or keywords to find relevant SOPs")
    n_results: int = Field(2, description="Number of results to return")
    category: Optional[str] = Field(None, description="Filter by category: hardware, software, network, printing, payment")


class KnowledgeSearch(BaseTool):
    name: str = "knowledge_search"
    description: str = (
        "Search the knowledge base for relevant SOPs, technical documentation, and FAQs. "
        "Use this to find solutions to known issues before escalating."
    )
    args_schema: type = KnowledgeSearchInput

    def _run(self, query: str, n_results: int = 2, category: Optional[str] = None) -> Dict[str, Any]:
        try:
            client = get_chroma_client()
            collection = client.get_or_create_collection("knowledge_base")

            where_filter = None
            if category:
                where_filter = {"category": category.lower()}

            results = collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where_filter,
            )

            documents = results.get("documents", [[]])[0]
            metadatas = results.get("metadatas", [[]])[0]
            distances = results.get("distances", [[]])[0]

            formatted = []
            for i, (doc, meta, dist) in enumerate(zip(documents, metadatas, distances)):
                formatted.append({
                    "rank": i + 1,
                    "content": doc[:400] + ("..." if len(doc) > 400 else ""),
                    "title": meta.get("title", "Unknown"),
                    "category": meta.get("category", "general"),
                    "sop_id": meta.get("sop_id", ""),
                    "similarity": round(1 - dist, 3),
                })

            logger.info(f"[KnowledgeTool] Found {len(formatted)} results for: '{query}'")
            return {"success": True, "results": formatted, "total": len(formatted)}

        except Exception as e:
            logger.error(f"[KnowledgeTool] Search error: {e}")
            return {"success": False, "results": [], "error": str(e)}


# ─────────────────────────────────────────────
# Incident Memory Search
# ─────────────────────────────────────────────
class IncidentMemorySearchInput(BaseModel):
    query: str = Field(..., description="Describe the current issue to find similar past incidents")
    n_results: int = Field(5, description="Number of past incidents to retrieve")
    site_name: Optional[str] = Field(None, description="Filter by specific site name")


class IncidentMemorySearch(BaseTool):
    name: str = "incident_memory_search"
    description: str = (
        "Search incident memory for similar past incidents and their resolutions. "
        "Use this to find proven solutions from historical data."
    )
    args_schema: type = IncidentMemorySearchInput

    def _run(self, query: str, n_results: int = 5, site_name: Optional[str] = None) -> Dict[str, Any]:
        try:
            client = get_chroma_client()
            collection = client.get_or_create_collection("incident_memories")

            where_filter = None
            if site_name:
                where_filter = {"site_name": site_name}

            results = collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where_filter,
            )

            documents = results.get("documents", [[]])[0]
            metadatas = results.get("metadatas", [[]])[0]
            distances = results.get("distances", [[]])[0]

            formatted = []
            for i, (doc, meta, dist) in enumerate(zip(documents, metadatas, distances)):
                formatted.append({
                    "rank": i + 1,
                    "summary": doc,
                    "root_cause": meta.get("root_cause", ""),
                    "resolution": meta.get("resolution", ""),
                    "site_name": meta.get("site_name", ""),
                    "device_type": meta.get("device_type", ""),
                    "category": meta.get("category", ""),
                    "similarity": round(1 - dist, 3),
                    "occurred_at": meta.get("occurred_at", ""),
                })

            logger.info(f"[IncidentMemory] Found {len(formatted)} similar incidents for: '{query}'")
            return {"success": True, "incidents": formatted, "total": len(formatted)}

        except Exception as e:
            logger.error(f"[IncidentMemory] Search error: {e}")
            return {"success": False, "incidents": [], "error": str(e)}


# ─────────────────────────────────────────────
# Write Incident Memory
# ─────────────────────────────────────────────
class IncidentMemoryWriteInput(BaseModel):
    incident_id: str = Field(..., description="Unique incident ID")
    summary: str = Field(..., description="Summary of the incident")
    root_cause: str = Field(..., description="Identified root cause")
    resolution: str = Field(..., description="Resolution applied")
    category: str = Field(..., description="Incident category")
    site_name: str = Field(..., description="Site where incident occurred")
    device_type: str = Field(..., description="Device type affected")
    tags: Optional[List[str]] = Field(None, description="Tags for categorization")


class IncidentMemoryWrite(BaseTool):
    name: str = "incident_memory_write"
    description: str = (
        "Save a resolved incident to the incident memory for future reference. "
        "This helps the AI learn from past incidents and improve future recommendations."
    )
    args_schema: type = IncidentMemoryWriteInput

    def _run(self, incident_id: str, summary: str, root_cause: str, resolution: str,
             category: str, site_name: str, device_type: str,
             tags: Optional[List[str]] = None) -> Dict[str, Any]:
        try:
            client = get_chroma_client()
            collection = client.get_or_create_collection("incident_memories")

            collection.add(
                ids=[incident_id],
                documents=[summary],
                metadatas=[{
                    "root_cause": root_cause,
                    "resolution": resolution,
                    "category": category,
                    "site_name": site_name,
                    "device_type": device_type,
                    "tags": ",".join(tags) if tags else "",
                }]
            )
            logger.info(f"[IncidentMemory] Saved incident {incident_id}")
            return {"success": True, "incident_id": incident_id}
        except Exception as e:
            logger.error(f"[IncidentMemory] Write error: {e}")
            return {"success": False, "error": str(e)}


class KnowledgeTools:
    @staticmethod
    def get_all() -> list:
        return [KnowledgeSearch(), IncidentMemorySearch(), IncidentMemoryWrite()]
