# Complete Setup Guide

This guide shows you how to connect the Gmail RAG Assistant to your **real Gmail account**.

> **Note:** The demo mode works without this! Only follow these steps if you want to search your actual emails.

---

## Prerequisites

Before starting:
- ✅ Python 3.10+ installed
- ✅ Ollama installed and running (`ollama serve`)
- ✅ Model downloaded (`ollama pull llama3`)
- ✅ App dependencies installed (`pip install -r requirements.txt`)

---

## Gmail API Setup

### Step 1: Create a Google Cloud Project

1. Go to [console.cloud.google.com](https://console.cloud.google.com/)
2. Click **"Create Project"**
3. Name it something like "Gmail RAG Assistant"
4. Click **"Create"**

### Step 2: Enable Gmail API

1. In your project, go to **APIs & Services** → **Library**
2. Search for **"Gmail API"**
3. Click on it, then click **"Enable"**

### Step 3: Configure OAuth Consent Screen

1. Go to **APIs & Services** → **OAuth consent screen**
2. Choose **"External"** user type
3. Click **"Create"**
4. Fill in the required fields:
   - **App name:** Gmail RAG Assistant
   - **User support email:** Your email
   - **Developer contact:** Your email
5. Click **"Save and Continue"**
6. On the **Scopes** page, click **"Save and Continue"** (don't add scopes here)
7. On the **Test users** page, click **"Add Users"**
8. Enter **your Gmail address** (the one you want to search)
9. Click **"Save and Continue"**

> **Important:** Keep the app in "Testing" mode. It only needs to work for you.

### Step 4: Create OAuth Credentials

1. Go to **APIs & Services** → **Credentials**
2. Click **"Create Credentials"** → **"OAuth client ID"**
3. Choose **"Desktop app"** as the application type
4. Name it "Gmail RAG Desktop"
5. Click **"Create"**
6. Click **"Download JSON"** (or the download icon)
7. Rename the downloaded file to `credentials.json`
8. **Move it to your project folder:**
   ```bash
   # It should be in the same folder as app.py
   gmail-rag-assistant/
   ├── app.py
   ├── credentials.json  ← Here!
   ├── rag_core.py
   └── ...
   ```

---

## Running with Real Gmail

### Start the Server

```bash
python app.py
```

Open **http://127.0.0.1:8100**

### Ingest Your Gmail

1. In the sidebar, enter how many emails to fetch (default: 50)
2. Click **"Ingest my Gmail"**
3. **A browser window will open** asking you to:
   - Sign in to Google
   - Grant read-only access to Gmail
4. Click **"Allow"**
5. The window closes automatically
6. Watch the progress in the sidebar

**First-time only:** The auth flow saves a `token.pickle` file so you don't need to authorize again.

### Ask Questions

Once ingestion completes:
1. Select your email address from the **"Active user"** dropdown
2. Type a question in the chat
3. Press Enter or click **"Ask"**

The AI will:
- Search your indexed emails
- Find relevant messages
- Generate an answer with source citations

---

## Understanding the Files

After setup, you'll see:

```
gmail-rag-assistant/
├── credentials.json     ← Google OAuth client (yours, secret)
├── token.pickle         ← Refresh token (auto-generated, secret)
├── chroma_db/          ← Vector database with your emails (private)
├── app.py              ← The web server
├── rag_core.py         ← Search & AI logic
└── static/             ← Web interface
```

### ⚠️ Keep These Secret

**Never commit to GitHub:**
- `credentials.json` - Contains your OAuth client secret
- `token.pickle` - Access token for your Gmail
- `chroma_db/` folder - Contains your email data

They're already in `.gitignore`, but double-check before pushing!

---

## Advanced Options

### Fetch More Emails

By default, 50 emails are fetched. To get more:

1. Web UI: Change the number in **"Emails to fetch"**
2. CLI: Edit `Extract_emails.py` line 46:
   ```python
   messages = list_messages(service, max_results=200)  # Change 50 to 200
   ```

### Use a Different AI Model

```bash
# Pull a different model
ollama pull mistral

# Set environment variable
export OLLAMA_MODEL=mistral  # Mac/Linux
set OLLAMA_MODEL=mistral     # Windows

# Restart the app
python app.py
```

### Force CPU Mode (No GPU)

If you get CUDA errors:

```bash
export OLLAMA_NUM_GPU=0  # Mac/Linux
set OLLAMA_NUM_GPU=0     # Windows

python app.py
```

The app will automatically fall back to CPU if GPU fails.

---

## Troubleshooting

### "Backend unreachable" in browser

**Cause:** FastAPI server isn't running  
**Fix:**
```bash
python app.py
```

### "Ollama offline" warning

**Cause:** Ollama isn't running  
**Fix:**
```bash
# In a separate terminal:
ollama serve

# Then pull the model if needed:
ollama pull llama3
```

### OAuth browser doesn't open

**Cause:** Running on a server without a desktop  
**Solution:**
1. Run ingestion on your local machine first
2. Copy `token.pickle` to the server
3. Or use a service account (advanced)

### "Invalid grant" or "Token expired"

**Cause:** OAuth token expired (happens after 7 days in Testing mode)  
**Fix:**
```bash
# Delete the old token
rm token.pickle

# Restart the app - it will ask you to authorize again
python app.py
```

### Slow responses (20+ seconds)

**Cause:** Model is too large for your GPU  
**Fix:**
```bash
# Use a smaller model
ollama pull llama3.2:3b

# Set it as default
export OLLAMA_MODEL=llama3.2:3b

python app.py
```

---

## CLI Scripts (Alternative to Web UI)

If you prefer command-line:

### Ingest Gmail
```bash
python Extract_emails.py
```

### Query
```bash
# Edit the query in Query_Ollama.py first, then:
python Query_Ollama.py
```

### Test with Fake Data
```bash
python FakeDemo.py
```

These use the same `rag_core.py` logic as the web UI.

---

## Security Notes

### What Access Does the App Have?

- **Read-only Gmail access** (`gmail.readonly` scope)
- Cannot send, delete, or modify emails
- Cannot access other Google services

### Where Is Data Stored?

- **`chroma_db/`** - Encrypted chunks of your email text
- **Local machine only** - Never sent to any server
- **Isolated by user** - If multiple accounts, data never mixes

### Can I Delete My Data?

Yes! Just delete the folders:
```bash
rm -rf chroma_db/
rm token.pickle
```

Your Gmail remains untouched.

---

## Performance Tips

### Indexing Speed

- **50 emails:** ~2 minutes
- **200 emails:** ~8 minutes
- **500 emails:** ~20 minutes

Limited by embedding model speed (~2s per email).

### Query Speed

- **Retrieval:** 0.1-0.5 seconds
- **Generation:** 5-20 seconds (depends on CPU/GPU)
- **Total:** Usually 10-25 seconds per question

### Improving Speed

1. **Use a smaller model:**
   ```bash
   ollama pull llama3.2:3b  # Faster, slightly less accurate
   ```

2. **Keep Ollama warm:**
   - The first query loads the model (slow)
   - Subsequent queries reuse it (fast)
   - Model stays loaded for 10 minutes by default

3. **Use GPU if available:**
   - Automatic if you have NVIDIA GPU
   - 3-5x faster than CPU

---

## Multi-User Setup

If multiple people use the same installation:

1. Each person runs **"Ingest my Gmail"** with their own credentials
2. Each gets their own entry in the **"Active user"** dropdown
3. ChromaDB uses `user_id` metadata to keep data separate
4. **Isolation test** button verifies no data leakage

---

## Updating the App

```bash
git pull origin main
pip install -r requirements.txt --upgrade
python app.py
```

Your `chroma_db/` and `token.pickle` are preserved.

---

## Next Steps

- **Try different questions** - see what it can find
- **Adjust retrieval count** - more chunks = more context (slower)
- **Experiment with models** - mistral, phi, codellama
- **Run the isolation test** - verify security

---

**Questions?** Open an issue on GitHub!
