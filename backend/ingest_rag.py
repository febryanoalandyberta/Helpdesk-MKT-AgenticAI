import os
import chromadb
import re

def main():
    host = os.getenv("CHROMA_HOST", "chromadb")
    client = chromadb.HttpClient(host=host, port=8000)
    collection = client.get_or_create_collection("knowledge_base")
    
    # hapus data lama
    try:
        docs = collection.get()
        if docs and "ids" in docs and docs["ids"]:
            collection.delete(ids=docs["ids"])
    except:
        pass
        
    with open("/app/../IT_Helpdesk_Knowledge_Base.md", "r", encoding="utf-8") as f:
        content = f.read()
        
    # Split by "**Case"
    cases = content.split("**Case ")
    
    documents = []
    metadatas = []
    ids = []
    
    for i, case_text in enumerate(cases[1:]): # skip the intro
        case_id = f"KB_{i+1}"
        full_text = "**Case " + case_text
        
        # Extract title
        lines = case_text.split("\n")
        title = lines[0].strip().replace("**", "")
        
        documents.append(full_text.strip())
        metadatas.append({"title": title, "category": "general", "sop_id": case_id})
        ids.append(case_id)
        
    if documents:
        collection.upsert(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        print(f"Successfully ingested {len(documents)} cases into knowledge_base collection!")

if __name__ == "__main__":
    main()
