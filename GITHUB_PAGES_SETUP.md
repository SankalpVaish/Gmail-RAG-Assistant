# GitHub Pages Deployment Guide

This guide shows you how to deploy the **static demo version** of the Gmail RAG Assistant to GitHub Pages.

## What Gets Deployed

The static demo:
- ✅ **Works without a backend** - all processing happens in the browser
- ✅ **Loads the 16 demo emails** from `fake_emails.json`
- ✅ **Simulates streaming** with mock LLM responses
- ✅ **Shows the full UI** - chat interface, demo viewer, isolation test
- ✅ **Automatically detects** when the backend is unavailable and switches to demo mode

**Note:** The static demo uses hardcoded answers for common questions. It's a **showcase/portfolio version**, not the full RAG system.

## Setup Steps

### 1. Push to GitHub

```bash
git add .
git commit -m "Add web interface with automatic static fallback

- FastAPI backend with streaming SSE
- Professional UI (Inter font, dark/light themes)
- Automatic backend detection: falls back to client-side demo
- 16 synthetic emails for demo
- Multi-user isolation testing

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
git push origin main
```

### 2. Enable GitHub Pages

1. Go to your repository on GitHub
2. Click **Settings** → **Pages** (left sidebar)
3. Under **Source**, select:
   - Branch: `main`
   - Folder: `/static` ← **Important!**
4. Click **Save**

### 3. Wait for Deployment

GitHub will build and deploy your site. This takes 1-2 minutes.

Your site will be available at:
```
https://YOUR_USERNAME.github.io/gmail-rag-assistant/
```

Replace `YOUR_USERNAME` with your GitHub username.

### 4. Update Repository Link (Optional)

If you want the demo banner to link to your repo, edit [`static/index.html`](static/index.html) line 6 and replace `YOUR_USERNAME` with your GitHub username.

## How It Works

### Automatic Mode Detection

When the page loads, `app.js` tries to fetch `/api/status`:

- **Backend available** (local dev): Full RAG system with Ollama
- **Backend unavailable** (GitHub Pages): Switches to static demo mode automatically

### Static Mode Features

✅ **Loads `fake_emails.json`** - 16 emails for 3 users  
✅ **Keyword-based retrieval** - searches emails by text matching  
✅ **Mock streaming** - types out hardcoded answers token-by-token  
✅ **Isolation testing** - verifies user data never leaks  
✅ **Demo data viewer** - modal showing all emails

### What Gets Mocked

| Feature | Backend Mode | Static Mode |
|---------|-------------|-------------|
| Data source | ChromaDB vector DB | `fake_emails.json` |
| Retrieval | Embedding similarity | Keyword matching |
| LLM | Ollama (llama3) | Hardcoded answers |
| Streaming | Real SSE from Ollama | Simulated with delays |
| Gmail ingestion | Real OAuth + API | Disabled |

## Customization

### Add More Mock Answers

Edit [`static/app.js`](static/app.js) around line 115:

```javascript
const MOCK_ANSWERS = {
  "api budget": "The API integration project has been allocated $50,000 for Q4.",
  "benefit enrollment": "The health insurance enrollment window closes on Friday...",
  // Add your own:
  "new keyword": "Your custom answer here",
};
```

### Change Demo Data

Edit [`fake_emails.json`](fake_emails.json) to add more synthetic emails. The static mode will load and search through whatever's in that file.

## Troubleshooting

### "Backend unreachable" shows on localhost

Your FastAPI server isn't running. Start it with:
```bash
uvicorn app:app --port 8100
```

### Static mode doesn't activate on GitHub Pages

1. Check that `/static` is selected as the source folder (not `/` or `/docs`)
2. Verify `fake_emails.json` is in the `static/` folder
3. Check browser console for errors (F12)

### Mock answers don't match questions

The keyword matching is simple. Add more entries to `MOCK_ANSWERS` or improve the `staticRetrieve()` function in `app.js`.

## Local Testing

To test static mode locally without deploying:

1. Stop the backend server if it's running
2. Open `static/index.html` directly in your browser (file:// URL)
3. The page should show the gold "Static Demo Mode" banner
4. Click "Load demo dataset" → should load fake_emails.json

Or use a simple HTTP server:

```bash
cd static
python -m http.server 8000
# Open http://localhost:8000
```

## Full App vs Static Demo

| | Full App (Local) | Static Demo (GitHub Pages) |
|-|------------------|----------------------------|
| **Backend** | FastAPI + Python | None (client-side only) |
| **LLM** | Ollama (llama3) | Hardcoded responses |
| **Data** | Real Gmail + ChromaDB | 16 synthetic emails |
| **Retrieval** | Semantic (embeddings) | Keyword matching |
| **Speed** | ~15-20s per query | ~2-3s (simulated) |
| **Hosting** | localhost:8100 | GitHub Pages (free) |
| **Purpose** | Real RAG system | Portfolio showcase |

---

**Questions?** Check the main [README.md](README.md) or open an issue!
