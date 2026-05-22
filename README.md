# Vivian CLI

> **v1.0.0** — AI-powered terminal assistant with multi-provider AI support, a built-in penetration testing toolkit, and optional desktop/web GUIs.

```bash
git clone https://github.com/g91/vivian_cli.git
cd vivian_cli
pip install -r requirements.txt
python -m vivian_cli
```

---

## Table of Contents

- [What is Vivian?](#what-is-vivian)
- [Quick Start](#quick-start)
- [First-Launch Setup Wizard](#first-launch-setup-wizard)
- [AI Providers](#ai-providers)
- [Commands Reference](#commands-reference)
- [Tool System](#tool-system)
- [Security & Penetration Testing](#security--penetration-testing)
- [GUIs](#guis)
- [Companion System](#companion-system)
- [Voice Mode](#voice-mode)
- [Cost & Token Tracking](#cost--token-tracking)
- [Remote Bridge](#remote-bridge)
- [Project Structure](#project-structure)
- [Configuration](#configuration)
- [CLI Flags](#cli-flags)
- [License](#license)

---

## What is Vivian?

Vivian CLI is a terminal-first AI assistant that blends **conversational AI**, **developer tooling**, and a full **penetration testing suite** into a single cohesive interface. It runs directly in your terminal, but also ships optional PyQt6 desktop and web GUIs.

Key highlights:

- **Multi-provider AI** — switch between Vivian (default), Ollama, OpenAI, Groq, Gemini, Anthropic, Mistral, Cohere, Perplexity, Together, HuggingFace, and OpenRouter without restarting
- **100+ slash commands** — git, code review, security scans, cost tracking, session memory, and more
- **40+ built-in tools** — the AI can call tools (bash, file I/O, web search, SSH, LSP, MCP, pen-test scanners…) autonomously during a conversation
- **First-launch wizard** — guided interactive setup on the very first run
- **Plugin & skill system** — extend Vivian with custom plugins and MCP skills
- **Session memory** — the assistant remembers context across conversations

---

## Quick Start

**Requirements:** Python 3.10+, Windows/Linux/macOS

```bash
# Clone
git clone https://github.com/g91/vivian_cli.git
cd vivian_cli

# Install
pip install -r requirements.txt

# Run (setup wizard auto-launches on first start)
python -m vivian_cli

# Windows shortcut
vivian.bat
```

On first run the setup wizard walks you through choosing an AI provider and entering credentials. You can skip it with `--no-wizard` or re-run it at any time with `/setup`.

### Uninstall

```bash
./install.sh --uninstall    # Linux/macOS
.\install.ps1 -Uninstall    # Windows
```

---

## First-Launch Setup Wizard

When no configuration file exists at `~/.vivian/config.json`, Vivian automatically launches an interactive setup wizard:

1. **Provider selection** — choose from 12 providers; free options are labelled clearly
2. **Credentials** — enter your API key (or server URL for Ollama); existing environment variables are detected automatically
3. **Model selection** — pick from a numbered list of recommended models, or enter any custom model name
4. **Optional settings** — theme, companion (buddy) toggle
5. **Summary** — review and confirm before saving

Skip the wizard:

```bash
python -m vivian_cli --no-wizard
```

Re-run the wizard at any time from inside the REPL:

```
/setup
```

---

## AI Providers

Vivian supports **12 AI providers** out of the box. Switch with `/provider use <id>`:

| ID | Provider | Free Tier | Auth | Notes |
|----|----------|-----------|------|-------|
| `vivian` | **Vivian** (default) | ✅ | API key | `https://api-vivian.d0a.net` |
| `ollama` | **Ollama** | ✅ Free | None | Run models locally |
| `groq` | **Groq** | ✅ Free tier | API key | Very fast inference |
| `gemini` | **Google Gemini** | ✅ Free tier | API key | Google AI Studio key |
| `openrouter` | **OpenRouter** | ✅ Many free | API key | 200+ models |
| `mistral` | **Mistral AI** | ✅ Free tier | API key | Strong coding models |
| `huggingface` | **HuggingFace** | ✅ Free | HF token | Thousands of open models |
| `anthropic` | **Anthropic** | Paid | API key | Claude 3/4 direct access |
| `openai` | **OpenAI** | Paid | API key | GPT-4o, o1, o3 |
| `together` | **Together AI** | Trial credits | API key | Starter credits |
| `perplexity` | **Perplexity AI** | Paid | API key | Web-augmented answers |
| `cohere` | **Cohere** | Trial | API key | Enterprise NLP/RAG |

### Provider Commands

```
/provider                        List all providers and current selection
/provider info <id>              Show provider details and required credentials
/provider use <id>               Switch to a different provider live
/provider set-key <id> <key>     Set or update an API key
/provider set-url <id> <url>     Override the base URL (e.g. custom Ollama host)
/provider set-model <id> <model> Set a default model for a provider
```

Environment variables are also honoured automatically:

```
OPENAI_API_KEY    GROQ_API_KEY      GEMINI_API_KEY     ANTHROPIC_API_KEY
MISTRAL_API_KEY   OPENROUTER_API_KEY TOGETHER_API_KEY  PERPLEXITY_API_KEY
HF_TOKEN          COHERE_API_KEY    VIVIAN_PROVIDER    OLLAMA_HOST
```

---

## Commands Reference

Type any command in the REPL, or pass `--prompt "..."` for one-shot mode.

### Session & Navigation

| Command | Description |
|---------|-------------|
| `/help` | Show all commands |
| `/clear` | Clear the screen and conversation |
| `/compact` | Compress conversation history to save tokens |
| `/exit` | Exit Vivian |
| `/resume` | Resume the last session |
| `/session` | Session management |

### Configuration

| Command | Description |
|---------|-------------|
| `/config` | View and edit configuration |
| `/model` | Switch AI model |
| `/provider` | Switch AI provider |
| `/setup` | Re-run the setup wizard |
| `/theme` | Change the colour theme |
| `/output-style` | Change output formatting |
| `/permissions` | Manage tool permissions |
| `/hooks` | Configure lifecycle hooks |
| `/keybindings` | Keyboard shortcut editor |
| `/vim` | Toggle VIM input mode |

### Git & Version Control

| Command | Description |
|---------|-------------|
| `/init` | Initialise a git repo with AI-generated .gitignore |
| `/commit` | Generate a commit message and commit |
| `/cpr` | Commit → push → open pull request |
| `/review` | AI code review of staged/unstaged changes |
| `/security-review` | Security-focused code review |
| `/diff` | Show and summarise a git diff |
| `/branch` | Branch management helpers |

### Code Analysis

| Command | Description |
|---------|-------------|
| `/doctor` | Diagnose and auto-fix issues in the codebase |
| `/advisor` | Architectural and design advice |
| `/insights` | Analytics and code metrics |
| `/brief` | Generate a session/project brief |
| `/effort` | Estimate effort for a task |

### AI Memory

| Command | Description |
|---------|-------------|
| `/session-memory` | View/edit this session's memory |
| `/team-memory` | Shared team memory across sessions |

### Cost & Usage

| Command | Description |
|---------|-------------|
| `/cost` | Show token usage and cost for this session |
| `/usage` | Usage statistics |
| `/limits` | View API rate limits and quotas |
| `/token-count` | Count tokens in the current context |

### Files & Context

| Command | Description |
|---------|-------------|
| `/add-dir` | Add a directory to AI context |
| `/context` | View and manage context window |
| `/files` | Browse workspace files |
| `/copy` | Copy output to clipboard |
| `/export` | Export conversation |

### Tools & Plugins

| Command | Description |
|---------|-------------|
| `/mcp` | Manage Model Context Protocol servers |
| `/plugin` | Install/manage plugins |
| `/skills` | List available skills |

---

## Tool System

During a conversation, Vivian can autonomously invoke tools to complete tasks. Tools run within your configured permission level and can be restricted with `/permissions`.

### Core Development Tools

- **`bash`** — Execute shell commands
- **`file_read` / `file_write` / `file_edit`** — Full file system access
- **`glob` / `grep` / `list_directory`** — File discovery and search
- **`notebook_edit`** — Jupyter notebook editing
- **`lsp`** — Language Server Protocol integration (go-to-definition, diagnostics)
- **`repl`** — Persistent Python/shell REPL for multi-step scripts

### Web & Research

- **`web_fetch`** — Fetch and parse any URL
- **`web_search`** — Web search integration
- **`todo_write`** — Create and manage TODO items

### MCP & Extension

- **`mcp`** — Call any connected MCP server tool
- **`skill`** — Execute loaded skills
- **`tool_search`** — Discover available tools dynamically

### Task & Team Coordination

- **`task_create` / `task_list` / `task_get` / `task_stop`** — Async task management
- **`team_create` / `team_delete`** — Multi-agent team setup
- **`schedule_cron`** — Schedule recurring tasks

### Remote & Infrastructure

- **`ssh`** — SSH into remote hosts and execute commands
- **`remote_trigger`** — Trigger remote commands
- **`send_message`** — Message relay between agents

---

## Security & Penetration Testing

Vivian ships a built-in security toolset designed for authorised security assessments:

| Tool | Description |
|------|-------------|
| `autopentest` | Fully autonomous pen-test: port scan → enumerate services → find and exploit vulnerabilities |
| `vulnscanner` | Static analysis (SAST) across PHP, Java, Python, JS, C/C++, Go, Ruby, .NET with taint tracking |
| `webaudit` | OWASP Top 10 web application scanner (SQLi, XSS, SSRF, XXE, IDOR, and more) |
| `codeaudit` | Deep code review with compliance mapping (OWASP, CWE, CVE cross-referencing) |
| `ssh` | Remote administration and interactive exploitation |
| `parsecvision` | Vision-based analysis with OpenCV (screen parsing, UI fuzzing) |
| `dmamemory` | Direct memory access analysis |
| `tryhackme` | TryHackMe CTF integration — spawn rooms, interact with targets |
| `thmwriteup` | Auto-generate CTF writeups |

```bash
# Examples
vivian -p "auto_pwn 10.10.10.5"
vivian -p "quick_scan 192.168.1.0/24"
```

> **Important:** These tools are for authorised security testing only. Always obtain explicit written permission before testing systems you do not own.

---

## GUIs

Vivian ships three optional graphical interfaces in addition to the default terminal UI.

### Terminal UI (default)

Rich terminal interface using `prompt_toolkit`. Includes syntax highlighting, theming, companion rendering, and full streaming chat — no extra dependencies required.

### Desktop GUI

```bash
python -m vivian_cli --gui
```

A PyQt6-based IDE-style desktop application:

- VS Code-style layout: activity bar, sidebar, multi-tab editor, AI chat panel
- File explorer and full-text search
- Source Control Management panel
- Build runner with ESP32/Arduino support
- Settings dialog

### Web GUI

```bash
python -m vivian_cli --web-gui
# Custom host/port:
python -m vivian_cli --web-gui --web-port 8080 --web-host 0.0.0.0
```

Flask-based web interface. Auto-opens in your browser unless `--no-open-browser` is passed.

### Desktop Web GUI

```bash
python -m vivian_cli --desktop-gui
# Desktop shell on port 7979, web IDE on port 7878
```

---

## Companion System

Vivian includes an AI companion (buddy) with a deterministic sprite generated from your configuration:

- Generated via a seeded Mulberry32 PRNG — the same seed always produces the same companion
- Attributes: species, eye type, hat, and rarity tier
- Rarity tiers: **Common → Uncommon → Rare → Epic → Legendary**
- Renders in both the TUI and desktop GUI
- Toggle on/off during setup or with `/config`

---

## Voice Mode

```
/voice          Toggle voice input on/off
```

Speech-to-text streaming is handled by the voice subsystem. Configure keyword detection and STT settings in `/config → voice`.

---

## Cost & Token Tracking

Every session tracks token usage and estimated cost:

```
/cost           Session cost summary
/usage          Historical usage
/token-count    Count tokens currently in context
```

The cost tracker records input/output/cached tokens per model, model-specific pricing, web search request counts, and running totals across the session.

---

## Remote Bridge

The bridge system connects Vivian to a remote session daemon, enabling:

- WebSocket/SSE transport for remote AI sessions
- JWT-based authentication
- Multi-client session sharing
- Automatic reconnection and backoff
- REPL bridging for interactive remote access

```bash
python -m vivian_cli.bridge.bridgeMain   # Start bridge daemon
/bridge status                           # Check bridge state from the REPL
```

---

## Project Structure

```
vivian_cli/
├── cli_main.py            # Main application entry point
├── vivian.bat             # Windows launcher
├── api/
│   ├── client.py          # VivianClient (OpenAI-compatible HTTP client)
│   └── providers/
│       └── registry.py    # 12-provider registry + resolution logic
├── commands/              # 100+ /slash-command implementations
├── tools/                 # 40+ tool implementations
├── services/              # Feature services (memory, MCP, OAuth, voice, limits…)
├── utils/
│   ├── config_file.py     # Config load/save, first-launch detection
│   └── setup_wizard.py    # Interactive first-launch setup wizard
├── bridge/                # Remote bridge daemon
├── buddy/                 # AI companion sprite system
├── tui/                   # Terminal UI (prompt_toolkit)
├── gui/                   # Desktop GUI (PyQt6)
├── web_gui/               # Web interface (Flask)
├── desktop_webgui/        # Desktop web app
├── tasks/                 # Async task management
├── plugins/               # Plugin registry and bundled plugins
├── skills/                # Skill extensions (MCP-style)
├── entrypoints/           # Alternative entry points (CLI, MCP server, SDK)
├── bootstrap/             # App state initialisation
├── coordinator/           # Multi-agent coordinator mode
├── hooks/                 # Lifecycle hook system
├── memdir/                # Memory directory management
├── output_styles/         # Output formatting and themes
├── query_engine.py        # Core query lifecycle and streaming
├── cost_tracker.py        # Token usage and cost tracking
├── state/                 # Application state store
├── vim/                   # VIM mode input engine
└── voice/                 # Speech-to-text subsystem
```

---

## Configuration

Configuration is stored at `~/.vivian/config.json` and is created automatically by the setup wizard.

Key fields:

```json
{
  "provider": "vivian",
  "provider_keys": { "groq": "gsk_...", "openai": "sk-..." },
  "provider_urls": { "ollama": "http://localhost:11434" },
  "provider_models": { "ollama": "llama3.2" },
  "api_url": "https://api-vivian.d0a.net",
  "model": "vivian-sonnet-4-20250514",
  "theme": "cyberpunk",
  "setup_complete": true
}
```

Edit live with `/config`, or delete `~/.vivian/config.json` to trigger the setup wizard again on next launch.

---

## CLI Flags

```
python -m vivian_cli [options]

  --prompt, -p TEXT       One-shot prompt (non-interactive)
  --model TEXT            Override the default model
  --provider TEXT         Override the active provider
  --gui                   Launch the desktop GUI
  --web-gui               Launch the web interface
  --web-port INT          Web GUI port (default 5000)
  --web-host TEXT         Web GUI host (default 127.0.0.1)
  --no-open-browser       Don't auto-open the browser with --web-gui
  --desktop-gui           Launch the cyberpunk desktop GUI
  --desktop-port INT      Desktop GUI port (default 7979)
  --no-wizard             Skip the first-launch setup wizard
  --version, -v           Print version and exit
  --json                  Output responses as JSON (pipe-friendly)
  --admin-login           Admin authentication flow
```

---

## License

MIT — see [LICENSE](LICENSE) for details.
