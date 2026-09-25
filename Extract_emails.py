import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
from googleapiclient.discovery import build
import base64
from bs4 import BeautifulSoup
from sentence_transformers import SentenceTransformer
import chromadb
import time

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def gmail_authenticate():
    creds = None

    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        refreshed = False

        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                refreshed = True
            except RefreshError:
                # The saved refresh token is dead — typically because the OAuth
                # consent screen is still in "Testing" mode, where Google expires
                # test-user refresh tokens after 7 days. Discard it and log in again.
                print("Saved credentials expired or were revoked. Re-authenticating...")
                creds = None
                if os.path.exists('token.pickle'):
                    os.remove('token.pickle')

        if not refreshed:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES
            )
            creds = flow.run_local_server(port=0)

        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    return creds



def get_gmail_service():
    creds = gmail_authenticate()
    return build('gmail', 'v1', credentials=creds)

def get_user_email(service):
    profile = service.users().getProfile(userId='me').execute()
    return profile.get('emailAddress') # This is the user_id


def list_messages(service, max_results=50):
    results = service.users().messages().list(
        userId='me', maxResults=max_results
    ).execute()
    return results.get('messages', [])



def get_message_content(service, msg_id):
    msg = service.users().messages().get(
        userId='me', id=msg_id, format='full'
    ).execute()

    headers = msg['payload']['headers']
    metadata = {h['name']: h['value'] for h in headers}

    body = ""
    parts = msg['payload'].get('parts', [])
    for part in parts:
        if part['mimeType'] == 'text/html':
            data = part['body'].get('data')
            if data:
                html = base64.urlsafe_b64decode(data).decode('utf-8')
                body = BeautifulSoup(html, 'html.parser').get_text()

    return {
        "from": metadata.get("From"),
        "subject": metadata.get("Subject"),
        "date": metadata.get("Date"),
        "body": body
    }

def get_drive_service():
    creds = gmail_authenticate() 
    return build('drive', 'v3', credentials=creds)

# Bonus: Download and parse Google Drive documents
def download_and_parse_drive_docs(service, user_id):
    # List files
    results = service.files().list(pageSize=5, fields="files(id, name, mimeType)").execute()
    items = results.get('files', [])

    for item in items:
        file_id = item['id']
        mime_type = item['mimeType']
        
        if mime_type == 'application/vnd.google-apps.document':
            # Convert Google Doc to text (Requirement: Demonstrate usable format conversion)
            request = service.files().export_media(fileId=file_id, mimeType='text/plain')
            content = request.execute().decode('utf-8')
            
            # Use your existing chunking and storage logic
            chunks = chunk_text(content)
            store_chunks(chunks, {
                "subject": item['name'],
                "source": "google_drive",
                "file_id": file_id
            }, user_id)



def chunk_text(text, chunk_size=500):
    return [
        text[i:i+chunk_size]
        for i in range(0, len(text), chunk_size)
    ]

if __name__ == "__main__":
    embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

    chroma_client = chromadb.PersistentClient(
        path="chroma_db"
    )
    collection = chroma_client.get_or_create_collection("gmail_emails")

    def store_chunks(chunks, metadata, user_id):
        embeddings = embedding_model.encode(chunks).tolist()
        
        for i, chunk in enumerate(chunks):
            # Add user_id to the metadata dictionary for filtering
            meta = metadata.copy()
            meta["user_id"] = user_id 
            
            collection.add(
                documents=[chunk],
                embeddings=[embeddings[i]],
                metadatas=[meta],
                ids=[f"{user_id}_{metadata['subject']}_{i}"]
            )

    service = get_gmail_service()
    current_user_email = get_user_email(service) 
    print(f"Logged in as: {current_user_email}")

    messages = list_messages(service)
    start_time = time.time()
    print(f"Fetched {len(messages)} messages. Processing...")
    for msg in messages:
        email = get_message_content(service, msg['id'])
        chunks = chunk_text(email['body'])

        store_chunks(
            chunks,
            {
                "from": email["from"],
                "subject": email["subject"],
                "date": email["date"]
            },
            current_user_email
        )
    end_time = time.time()
    print(f"Processed and stored emails in {end_time - start_time:.2f} seconds.")
    print("Gmail extraction complete")




