# 🤖 AI Agent Portfolio
### Rajat Gupta — Principal Data Platform Consultant → AI Architect

![Scripts Complete](https://img.shields.io/badge/Scripts%20Complete-4%20of%2016-blue)
![Projects Complete](https://img.shields.io/badge/Projects%20Complete-1%20of%205-green)
![Target Rate](https://img.shields.io/badge/Target%20Rate-%24120--150%2Fhr-orange)

> Building from data platform expert to AI architect contractor.
> Combining 9 years of Databricks/Azure/Fabric experience with hands-on AI agent engineering.

---

# AI Agent Portfolio — Learning Plan & Progress
## Rajat Gupta | Principal Data Platform Consultant → AI Architect Contractor

---

## Goal
Become an AI Architect/Engineer contractor targeting $120-150/hr contracts.
Unique angle: AI on top of data platforms (Databricks, Microsoft Fabric, Azure) — combining 9 years of data platform expertise with hands-on AI agent engineering.

---

## Progress Tracker

### ✅ COMPLETED

#### Hermes Agent — Real Estate News Agent (13 May 2026)
- Installed Hermes Agent v0.12 on local Windows/WSL machine
- Configured Claude Haiku as the AI brain via Anthropic API
- Created SOUL.md — sharp Australian property investor personality
- Created aus-realestate-news SKILL — fetches live RSS feeds from ABC, Domain, realestate.com.au, AFR
- Built Python RSS scraper with investor-focused filtering and scoring
- Connected Telegram bot @aupropertynews_rajat_bot
- Tested — live Australian property news delivered to Telegram
- Next step: Deploy to Hostinger VPS ($8/mo) for 24/7 autonomous delivery

#### Week 1 — Foundation Scripts (01-claude-api-basics/)

**Script 1 ✅ — 01_hello_claude.py**
- Direct Claude API call from Python
- Concepts: API client, messages format, response parsing, token counting
- Key learning: Foundation of every AI application

**Script 2 ✅ — 02_chat_with_memory.py**
- Conversation with persistent memory across messages
- Concepts: conversation_history list, role/content format, why Claude has no built-in memory
- Key learning: Claude re-reads full conversation history on every API call — that IS the memory
- Proved: Claude correctly recalled name and profession 3 messages later

**Script 3 ✅ — 03_claude_with_tools.py**
- AI agent that can take actions using tools
- Concepts: tool schemas, tool_use stop_reason, agentic loop, execute_tool()
- Professional structure: tools/ folder, schemas/ folder, separation of concerns
- Key learning: Claude decides WHEN and WHICH tools to use — that is agentic reasoning
- Proved: Claude called calculate() twice autonomously to solve a property profit question

**Script 4 ✅ — 04_streaming.py**
- Real-time streaming responses word by word
- Concepts: client.messages.stream(), flush=True, end="", token growth with history
- System prompt as personality (equivalent to SOUL.md in Hermes)
- Key learning: Token costs grow with conversation length — context management is critical
- Context management strategy: keep last 10 messages only (MAX_HISTORY = 10)

---

### 🔄 IN PROGRESS

**Script 5 — 05_structured_output.py**
- Claude returns JSON instead of plain text
- Concepts: JSON mode, json.loads(), batch processing, saving results to file
- Use case: Extract structured property data, feed directly into databases/dashboards
- Why it matters: Bridge between Claude and Databricks/databases/APIs

---

### 📋 REMAINING — Week 1

**Script 6 — 06_context_management.py**
- Proper conversation summarisation to reduce token costs
- Concepts: sliding window, summarisation strategy, prompt caching
- Why it matters: Production apps cannot grow context forever

---

### 📋 REMAINING — Week 2 (LangChain + RAG)

**Script 7 — LangChain basics**
- Chains, prompt templates, LLM wrappers
- Why: LangChain manages memory/tools/agents automatically — now you understand what it does

**Script 8 — LangChain agent with tools**
- Reproduce Script 3 using LangChain in 10 lines instead of 100
- Why: This is what clients and job postings mean by "LangChain experience"

**Script 9 — RAG part 1: Document loading and chunking**
- Load PDFs, split into chunks, understand chunk size/overlap
- Why: Foundation of every enterprise AI knowledge base

**Script 10 — RAG part 2: Embeddings and vector search**
- Create embeddings, store in ChromaDB, semantic search
- Why: How AI finds relevant context from thousands of documents

**Script 11 — RAG part 3: Full Q&A pipeline**
- Complete RAG: load docs → chunk → embed → store → query → answer with citations
- Why: Most requested skill in AI architect job postings

**Script 12 — RAG on Databricks (your unique angle)**
- Connect RAG pipeline directly to Delta Lake tables
- Natural language queries over your lakehouse data
- Why: Your 9 years of data platform experience becomes a premium differentiator

---

### 📋 REMAINING — Week 3 (Production + Deployment)

**Script 13 — CrewAI multi-agent system**
- 3 agents: Researcher, Analyst, Writer
- Build an automated property market research report
- Why: Multi-agent systems are the most requested skill in 2026 AI contracts

**Script 14 — Streamlit UI**
- Add a web interface to your RAG pipeline
- Why: Clients need to see and use the app, not just run terminal scripts

**Script 15 — Docker containerisation**
- Package your app into a Docker container
- Why: How every production AI app is deployed

**Script 16 — Azure deployment**
- Deploy to Azure Container Apps
- Connect Azure OpenAI instead of direct Anthropic API
- Why: You already know Azure — this closes the gap between your CV and reality

---

## 5 Portfolio Projects

| # | Project | Status | Tech Stack |
|---|---------|--------|------------|
| 1 | AU Real Estate News Agent | ✅ Working locally | Hermes, Claude, RSS, Telegram |
| 2 | RAG Chatbot over Property Documents | 📋 Week 2 | LangChain, ChromaDB, Azure OpenAI |
| 3 | AI Agent on Databricks Lakehouse | 📋 Week 2 | LangChain, Delta Lake, PySpark |
| 4 | CrewAI Property Research System | 📋 Week 3 | CrewAI, Claude, Web Search |
| 5 | Full Azure Deployment with UI | 📋 Week 3 | Streamlit, Docker, Azure |

---

## Key Concepts Learned So Far

| Concept | Where learned | Why it matters |
|---------|--------------|----------------|
| API client setup | Script 1 | Foundation of all AI apps |
| Conversation memory | Script 2 | How every chatbot works |
| Tool use / agentic loop | Script 3 | What makes an agent vs chatbot |
| Streaming | Script 4 | Required for all production UIs |
| Context management | Script 4 | Controls cost in production |
| Separation of concerns | Script 3 | Senior engineer signal |
| Token cost awareness | Script 4 | Production thinking from day 1 |

---

## Tools & Technologies

### Learned
- Anthropic Python SDK
- Claude API (messages, streaming, tools)
- Git + GitHub + SSH authentication
- VS Code + Claude Code extension
- Hermes Agent framework
- WSL (Windows Subsystem for Linux)

### Coming Next
- LangChain + LangGraph
- ChromaDB (vector database)
- CrewAI
- Streamlit
- Docker
- Azure Container Apps
- Azure OpenAI

---

## Target Contract Profile

**Title:** AI Solution Architect / AI Agent Engineer  
**Rate:** $120-150/hr  
**Pitch:** "I build AI on top of enterprise data platforms — Databricks, Microsoft Fabric, Azure. I combine 9 years of data platform architecture with hands-on AI agent engineering."  
**Unique angle:** Most AI engineers don't know data platforms. Most data engineers don't know AI. You bridge both.

---

## GitHub Repository
https://github.com/rajat301/ai-agent-portfolio

## Contact
- LinkedIn: linkedin.com/in/rajat-gupta-353a6579
- Email: rajatgupta301200@gmail.com
- Location: Sydney, NSW, Australia
