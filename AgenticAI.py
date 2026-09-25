import chromadb
from sentence_transformers import SentenceTransformer
import requests
import time
from Extract_emails import get_gmail_service, get_user_email

# 1. Load ChromaDB
client = chromadb.PersistentClient(path="chroma_db")
service = get_gmail_service()
target_user = get_user_email(service) 
collection = client.get_collection("gmail_emails")

# 2. Load embedding model 
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

query = "What is my Bank account transaction history?" 

query_embedding = embedding_model.encode(query).tolist()

start_time = time.time()
results = collection.query(
    query_embeddings=[query_embedding],
    n_results=5,
    where={"user_id": target_user} # Enforce user isolation
)
end_time = time.time()
print(f"Query and retrieval time: {end_time - start_time:.2f} seconds")
context = "\n\n---\n\n".join(results["documents"][0])

# 5. Prompt
prompt = f"""
You are an assistant.
Answer the user's question using ONLY the following email context.
If the answer is not present, say "I don't know".

Email context:
{context}

User question:
{query}
"""

# 6. Ollama call

start_time = time.time()

ollama_response = requests.post(
    "http://localhost:11434/api/generate",
    json={
        "model": "llama3",
        "prompt": prompt,
        "stream": False 
    }
)

generation_time = time.time() - start_time
output_text = ollama_response.json().get("response", "")

print(f"Generation time: {generation_time:.2f} seconds") 
print("LLM output:", output_text)
print("\nSources used:")
for meta in results["metadatas"][0]:
    # Used emails as sources
    print(f"- Subject: {meta['subject']} | Date: {meta['date']}")