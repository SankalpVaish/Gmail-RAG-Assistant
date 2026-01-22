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

# TEST CASE: PROVING ISOLATION
user_a = target_user
user_b = "XYZ@example.com"

print("--- Security Test: XYZ searching for my's data ---")
malicious_query = "What is Sankalp's Indusind Bank account transaction history?" 

results = collection.query(
    query_embeddings=embedding_model.encode([malicious_query]).tolist(),
    n_results=5,
    where={"user_id": user_b} # Even though my account has the data, XYZ's ID is used
)

if not results["documents"][0]:
    print("Success: XYZ retrieved 0 results from my data.")
else:
    print("Failure: Security leak detected!")