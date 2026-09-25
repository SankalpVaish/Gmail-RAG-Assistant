# Gmail RAG Assistant

**Search your email with AI — everything runs locally on your computer.**

Ask questions like "What's my API budget?" or "When is my flight?" and get instant answers from your Gmail, powered by a local AI model. Your data never leaves your machine.

![Python](https://img.shields.io/badge/Python-3.10+-blue) ![License](https://img.shields.io/badge/License-MIT-green) ![Ollama](https://img.shields.io/badge/Ollama-Local_LLM-orange)

---

## ✨ What It Does

- 📧 **Connects to your Gmail** and indexes your emails locally
- 🔍 **Smart semantic search** - finds relevant emails even if they don't contain exact keywords
- 🤖 **AI-powered answers** using Ollama (runs on your computer, not the cloud)
- 🔒 **100% private** - no data sent to external servers after initial email fetch
- 👥 **Multi-user support** - each person's data is strictly isolated
- 🌐 **Beautiful web interface** - modern chat UI with streaming responses

---

## 🚀 Quick Start

### 1. Install Requirements

**You need:**
- Python 3.10 or newer
- [Ollama](https://ollama.com/download) (free, runs the AI locally)

**Install Ollama:**
```bash
# Download from ollama.com/download or:

# Mac/Linux:
curl -fsSL https://ollama.com/install.sh | sh

# Windows: download the installer from ollama.com
```

**Pull the AI model:**
```bash
ollama pull llama3
```

### 2. Install the App

```bash
# Clone this repo
git clone https://github.com/SankalpVaish/Gmail-RAG-Assistant
cd gmail-rag-assistant

# Install Python dependencies
pip install -r requirements.txt
```

### 3. Try the Demo

**No Gmail setup needed!** Start with synthetic data:

```bash
python app.py
```

Open **http://127.0.0.1:8100** in your browser, then:
1. Click **"Load demo dataset"** (16 sample emails)
2. Ask: *"How much is the API budget?"*
3. Watch the AI answer with sources!

---

## 📊 Demo vs Real Mode

### 🎮 Demo Mode (No Setup)
- Uses 16 synthetic emails
- Try it instantly
- See how it works

### 🔐 Real Mode (Your Gmail)
See [SETUP.md](SETUP.md) for Gmail integration — it's optional!

---

## 💬 Example Questions

Once loaded (demo or real Gmail):

- "What's my Stripe payout?"
- "When is my flight to Austin?"
- "Show me security alerts"
- "Summarize recent emails"
- "What's my hotel confirmation number?"

The AI only answers from your actual emails — if it doesn't know, it says so.

---

## 🛡️ Privacy & Security

- ✅ **Emails stay on your computer** - stored in a local database
- ✅ **AI runs locally** - Ollama never sends your data anywhere
- ✅ **Multi-user isolation** - if multiple people use it, data never mixes
- ✅ **Read-only Gmail access** - can't modify or delete emails

After the initial Gmail sync, you can **disconnect from the internet** and everything still works.

---

## 🎨 Screenshots

### Chat Interface
<img src="docs/screenshot-chat.png" width="600" alt="Chat interface showing a question and AI response with sources">

*Ask questions naturally and get instant answers with email sources*

### Demo Data Viewer
<img src="docs/screenshot-demo.png" width="600" alt="Modal showing 16 demo emails">

*Preview the demo dataset before loading*

### Isolation Test
<img src="docs/screenshot-isolation.png" width="600" alt="Security test showing data isolation">

*Verify that user data never leaks*

---

## 🛠️ Technical Stack

Built with modern, privacy-focused tools:

- **[FastAPI](https://fastapi.tiangolo.com/)** - Fast, modern web framework
- **[ChromaDB](https://www.trychroma.com/)** - Local vector database for search
- **[Ollama](https://ollama.com/)** - Run AI models locally (llama3)
- **[SentenceTransformers](https://www.sbert.net/)** - Semantic search embeddings
- **Vanilla JavaScript** - No framework bloat, just clean code

---

## 📖 Documentation

- **[SETUP.md](SETUP.md)** - Full Gmail integration guide
- **[GITHUB_PAGES_SETUP.md](GITHUB_PAGES_SETUP.md)** - Deploy a demo to GitHub Pages
- **[QUICKSTART.md](QUICKSTART.md)** - Detailed installation steps

---

## 🤝 Contributing

Found a bug? Want to add a feature? PRs welcome!

1. Fork the repo
2. Create a feature branch
3. Make your changes
4. Test with the demo mode
5. Submit a PR

---

## 📄 License

MIT License - see [LICENSE](LICENSE) for details

---

## 🙏 Credits

- Gmail API integration
- ChromaDB for vector storage
- Ollama for local LLM inference
- Built as a technical demonstration of RAG (Retrieval-Augmented Generation)

---

## ⭐ Star This Repo

If you find this useful, give it a star! It helps others discover the project.

---

**Questions?** Open an issue or check the [documentation](SETUP.md).

Made with ❤️ for privacy-conscious AI enthusiasts.
