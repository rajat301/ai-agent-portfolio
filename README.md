# AI Agent Portfolio

A hands-on portfolio of production-ready AI agent systems, built to demonstrate practical expertise in designing, building, and deploying intelligent automation solutions. Created by an AI architect contractor specialising in enterprise AI integration and agentic workflows.

---

## Projects

### 01 — Claude API Basics
Direct integration with Anthropic's Claude API. Covers authentication, prompt engineering, streaming responses, and building a solid foundation for any Claude-powered application.

### 02 — LangChain Agents
Autonomous agents built with LangChain — tool use, memory, chains, and multi-step reasoning. Shows how to wire up external tools (search, calculators, APIs) into a coherent agent loop.

### 03 — RAG Pipeline
Retrieval-Augmented Generation system using ChromaDB as a vector store. Demonstrates how to ingest documents, embed them, and give an LLM access to a private knowledge base at query time.

### 04 — CrewAI Multi-Agent System
Orchestrated multi-agent workflows using CrewAI. Multiple specialised agents collaborate — researcher, analyst, writer — to complete complex tasks that no single agent could handle alone.

### 05 — Azure Deployment
End-to-end deployment of an AI agent to Azure using Azure OpenAI Service. Covers infrastructure setup, environment configuration, and production-grade serving patterns.

---

## Stack

| Layer | Technologies |
|---|---|
| LLM APIs | Anthropic Claude, OpenAI, Azure OpenAI |
| Agent Frameworks | LangChain, CrewAI |
| Vector Store | ChromaDB |
| UI | Streamlit |
| Cloud | Azure |
| Language | Python 3.11+ |

## Setup

```bash
# Clone the repo
git clone <repo-url>
cd ai-agent-portfolio

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment variables
cp .env .env.local  # then fill in your real API keys
```

Each project folder contains its own README with instructions specific to that module.

---

*Portfolio maintained by Rajat Gupta — AI Architect | [ignition-data.com](https://ignition-data.com)*
