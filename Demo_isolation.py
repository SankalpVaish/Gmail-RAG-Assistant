import chromadb
from sentence_transformers import SentenceTransformer
import requests
import time

# 1. Load ChromaDB
client = chromadb.PersistentClient(path="chroma_db")
target_user = "sankalp.vaish14@gmail.com"
collection = client.get_collection("gmail_emails")

# 2. Load embedding model 
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

# TEST CASE: PROVING ISOLATION
user_a = target_user
user_b = "XYZ@example.com"

print("--- Security Test: XYZ searching for my's data ---")
malicious_query = "What is Sankalp's secret order number?" 

results = collection.query(
    query_embeddings=embedding_model.encode([malicious_query]).tolist(),
    n_results=5,
    where={"user_id": user_b} # Even though my account has the data, XYZ's ID is used
)

if not results["documents"][0]:
    print("Success: XYZ retrieved 0 results from my data.")
else:
    print("Failure: Security leak detected!")