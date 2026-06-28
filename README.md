# 👾 Nedster CLI Coding Agent

<div align="center">
  <p>
    <a href="#"><img src="https://img.shields.io/badge/AI-100%25%20Local-00E676?style=flat-square" alt="100% Local"></a>
    <a href="#"><img src="https://img.shields.io/badge/VRAM-8GB%2B-6200EA?style=flat-square" alt="8GB VRAM"></a>
    <a href="#"><img src="https://img.shields.io/badge/Context-256K-FF5722?style=flat-square" alt="256K Context"></a>
    <a href="#"><img src="https://img.shields.io/badge/KV_Compression-TurboQuant-3F51B5?style=flat-square" alt="TurboQuant"></a>
  </p>
</div>

<!--
  SEO Tags (Hidden):
  - Keywords: local coding agent, ollama coding agent, local ai developer, private coding assistant, devin alternative local, chromadb python rag, autonomous local agent, git /undo agent, litellm python agent, unchained ai software engineer, local-first coding assistant, watchdog python incremental index, world graph ast analyzer, python agent event bus
  - Purpose: Fully local, 100% private AI software engineer running on consumer hardware (RTX GPUs) with zero-cost cloud or local inference, direct tool execution, auto-verifying critic loops, and git-based action rollback.
-->

**An unstoppable, fully local, open-source coding agent that runs on your consumer GPU.**

**Tags:** `ollama` `coding-agent` `local-ai` `cli` `rag` `chromadb` `python` `qwen` `litellm`

Are you trying to use local LLMs to autonomously write code, read files, and manage your projects, only to watch them suffer from "tool amnesia," hallucinate XML tags, or get stuck in infinite execution loops? 

**Nedster** solves this instantly.

Nedster is a highly autonomous, CLI-based AI software engineer designed for privacy-conscious developers. Powered by Ollama or your paid Cloud APIs (Gemini, OpenAI, Anthropic via LiteLLM) and augmented with **TurboQuant 4-bit KV Cache Compression**, it doesn't just chat—it *acts*. It searches your codebase, edits files precisely, and scaffolds entire projects without ever sending a single line of your code to the cloud.

---

## ✨ Features

*   **🛡️ Bulletproof Tool Execution:** A highly fortified, single-pass regex parser catches broken XML, malformed JSON, and markdown fallbacks. If the model meant to run a tool, Nedster executes it.
*   **🧠 Amnesia Correction:** If the LLM forgets it has filesystem access and apologizes, Nedster dynamically intercepts the refusal, injects a system correction, and forces a retry.
*   **🗜️ 256K Context on 8GB VRAM:** Integrated with Google's TurboQuant. Feed Nedster massive log files and entire codebases without triggering out-of-memory errors.
*   **📚 Built-in Local RAG:** Comes with a standalone ChromaDB engine to vectorize and semantically search your project directories effortlessly.
*   **🔁 Iteration Budgets:** Hard limits on autonomous loops and continuity watchdogs ensure the model stays on track and never hangs your terminal.
*   **🔌 Smart Boot & LiteLLM Integration:** Boot Nedster globally and choose between Local (Ollama) or Cloud (LiteLLM) backends. Change providers or models mid-session securely.
*   **⚡ Event-Driven Micro-Kernel:** A reactive pub/sub event bus with priority queues and hot-reload deduplication guarantees clean event hooks without memory leaks.
*   **🔄 Auto-Discovering Plugin Manager:** Drops-in new skills/ and plugins/ on-the-fly, wrapping existing tool setups automatically without rewrites.
*   **🗺️ Live World Graph:** Maps Python imports, function declarations, and file-level Git commit history in real-time.
*   **👁️ Watchdog Incremental Indexing:** Detects file saves on-the-fly and automatically updates ChromaDB embeddings and BM25 Keyword indexes for the modified file only.
*   **⏪ Advisory Execution Replay:** Caches successful workflow DAGs and suggests past paths inside the planner prompt to speed up reasoning.
*   **🕵️ Connected Critic Loop:** Automates security, performance, and coverage reviews (via persona reviewers and mutation tests) on every file write before the change is marked done.
*   **⏪ Git-Based `/undo` safety net:** Initialize a git repository on startup and instantly reset files to the last safe commit if Nedster makes a mistake.

---

## 🛠️ Quick Start

It takes just a few commands to get your local coding agent up and running.

**Windows:**
```bat
git clone https://github.com/unrealumanga/Nedster.git
cd Nedster
setup.bat
start.bat
```

**Linux / Mac:**
```bash
git clone https://github.com/unrealumanga/Nedster.git
cd Nedster
chmod +x setup.sh start.sh
./setup.sh
./start.sh
```

**Global Command Installation:**
Make Nedster accessible globally by running our installer script:
```bash
./install_global.sh
```
Once installed, you can launch Nedster from any directory on your system simply by typing:
```bash
nedster
```

### Navigating the CLI
Once running, choose your backend (Local or Cloud) and type your request naturally:
```text
Nedster> fix the auth logic in src/auth.py to use the requests library
Nedster> scaffold a new React project in the frontend/ folder
Nedster> /models
Nedster> /undo
```

## 📈 System Monitoring
Nedster includes a beautiful Terminal UI (TUI) that provides real-time tracking of your CPU RAM, ChromaDB vectors, and GPU VRAM polling (via `nvidia-smi`), keeping you in total control of your hardware.
