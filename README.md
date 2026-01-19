#Gmail RAG Assistant (ReadMe)

Overview

Gmail RAG Assistant is a local system that allows users to:

•	Fetch emails from Gmail

•	Split and store emails in a local vector database (ChromaDB)

•	Search emails semantically using embeddings

•	Generate answers via a local LLM (Ollama)

•	Support multiple users securely using metadata filtering

All data remains local and offline after ingestion.
________________________________________

Features

•	Gmail API integration with OAuth2

•	Email parsing and chunking

•	Local vector storage with ChromaDB

•	Semantic search using SentenceTransformers embeddings

•	Grounded responses from Ollama LLM

•	Multi-user isolation using user_id metadata

•	Unicode-safe (supports ₹, emojis, etc.)

•	The system handles both Gmail and Google Drive files, converting non-text formats into indexable strings.
________________________________________

Setup Instructions

1.	Ollama must be installed.

2.	Install Python 3.10+

3.	Install dependencies:

4.	pip install google-auth google-auth-oauthlib google-api-python-client chromadb sentence-transformers beautifulsoup4

5.	Setup Google Cloud project

o	Enable Gmail API

o	Configure OAuth consent screen (External, add yourself as test user)

o	Create OAuth Desktop credentials

o	Download credentials.json to project folder
________________________________________

Usage

Extraction
•	Fetch Gmail emails

•	Split into chunks

•	Store in ChromaDB with user_id metadata

Query

•	Embed user question

•	Retrieve top-k chunks filtered by user_id

•	Generate answer via Ollama LLM

•	Returns grounded responses or “I don’t know” if no context
________________________________________
Multi-User Support

•	All email chunks tagged with user_id

•	Queries filtered with where={"user_id": user_id}

•	Prevents cross-user data leakage
________________________________________
Project Files
File	Description
credentials.json	Google OAuth2 credentials for Gmail API access.

Architecture.txt	Architecture used for the project.

Extract_emails.py	Script to fetch Gmail emails, clean, chunk, and store them in ChromaDB with user_id metadata.

Query_Ollama.py	Script to query the local vector database and generate answers using Ollama LLM.

requirements.txt	Lists all Python dependencies for the project.

chroma_db/	Folder  that will be present after execution of Extract_enail.py where ChromaDB stores the persistent vector database (auto-created after first ingestion).

Demo_isolation.py	A script that demonstrates the Multi-User Support bonus by attempting to query one user's real data while authenticated as another, proving that cross-user queries return empty results.

Evaluation Report.docx	Evaluation Report summarizing the project's performance, the technical difficulties, and the limitations of the current design. 

fake_emails.json	This file contains a curated set of synthetic emails designed to test both retrieval accuracy and security boundaries.

FakeDemo.py	A script that demonstrates the Multi-User Support bonus by attempting to query one user's fake data while authenticated as another.

README.md	This file- overview, setup instructions, and file descriptions.
________________________________________
Run FakeDemo.py file to see a small demo of how the system works on fake dataset.
References
•	Gmail API: https://developers.google.com/gmail/api
•	ChromaDB: https://www.trychroma.com/
•	Ollama: https://ollama.com/
•	SentenceTransformers: https://www.sbert.net/
