import json
import chromadb
from sentence_transformers import SentenceTransformer
import requests

# 1. Initialization
client = chromadb.PersistentClient(path="chroma_db")

# Ensure we start fresh for the demo
try:
    client.delete_collection("gmail_emails")
except:
    pass

collection = client.create_collection("gmail_emails")
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

def load_and_ingest(file_path):
    with open(file_path, 'r') as f:
        emails = json.load(f)
    
    for email in emails:
        # Create a unique ID and store with user_id metadata
        chunks = [email['body']] # Simple 1-chunk demo
        embeddings = embedding_model.encode(chunks).tolist()
        
        collection.add(
            documents=chunks,
            embeddings=embeddings,
            metadatas=[{
                "user_id": email['user_id'],
                "subject": email['subject'],
                "sender": email['sender']
            }],
            ids=[f"{email['user_id']}_{email['subject']}"]
        )
    print(f"Ingested {len(emails)} emails into the local Vector DB.")

# 2. Security Test Function
def run_security_test(query_text, acting_user_id):
    print(f"\n--- Querying as: {acting_user_id} ---")
    print(f"Question: {query_text}")
    
    query_vec = embedding_model.encode([query_text]).tolist()
    
    # The 'where' clause provides the mandatory user isolation
    results = collection.query(
        query_embeddings=query_vec,
        n_results=1,
        where={"user_id": acting_user_id}
    )
    
    print("Retrieved Documents:", results['documents'][0])
    if not results['documents'][0]:
        return "Empty Results (Access Denied/No Data)"
    
    # Prepare LLM Prompt
    context = results['documents'][0][0]
    prompt = f"Use this context to answer: {context}\n\nQuestion: {query_text}"
    
    # Call Local Ollama
    resp = requests.post("http://localhost:11434/api/generate", 
                         json={"model": "llama3", "prompt": prompt, "stream": False})
    return resp.json().get("response")

# --- EXECUTION ---
load_and_ingest('fake_emails.json')

# Test 1: Authorized Access
# Sankalp asks about her own budget (Should work)
print("Result:", run_security_test("How much is the API budget?", "Sankalp@example.com"))

# Test 2: Unauthorized Access (Multi-User Isolation Check)
# Bob asks about Sankalp's budget (Should FAIL/Return Empty)
print("Result:", run_security_test("How much is the API budget?", "bob@example.com"))