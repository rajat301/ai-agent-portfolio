# 🤖 AI Agent Portfolio
### Rajat Gupta — Principal Data Platform Consultant → AI Architect

![Scripts Complete](https://img.shields.io/badge/Scripts%20Complete-4%20of%2023-blue)
![Projects Complete](https://img.shields.io/badge/Projects%20Complete-1%20of%208-green)
![Target Rate](https://img.shields.io/badge/Target%20Rate-%24120--150%2Fhr-orange)
![Platforms](https://img.shields.io/badge/Platforms-Databricks%20%7C%20Snowflake%20%7C%20Fabric%20%7C%20Azure%20%7C%20AWS-purple)
![Frameworks](https://img.shields.io/badge/Frameworks-LangGraph%20%7C%20CrewAI%20%7C%20Agent%20Framework%20%7C%20AgentCore-red)

> **The pitch that wins $120–150/hr contracts:**
> "I build production-grade AI agents on top of enterprise data platforms.
> 9 years of Databricks / Azure / Fabric + hands-on agentic engineering across
> every major framework and cloud platform — Databricks, Snowflake, Fabric, Azure, AWS."
>
> **Not surface level. Not demos. Production systems with governance, observability, and real data.**

---

# Full Learning Plan & Progress

---

## Why This Portfolio Is Different

Every major enterprise platform now has a native agentic AI layer:

| Platform | Native Agent Stack | Your existing experience |
|----------|--------------------|--------------------------|
| Databricks | Mosaic AI Agent Framework + MLflow + Unity Catalog | ✅ 9 years |
| Snowflake | Cortex Agents + Cortex Analyst + Cortex Search | ✅ experienced |
| Microsoft Fabric | Fabric Data Agents + Copilot Studio + Semantic Kernel | ✅ 9 years |
| Azure | Azure AI Foundry + Microsoft Agent Framework 1.0 | ✅ 9 years |
| AWS | Bedrock AgentCore (Runtime + Memory + Gateway + Observability) | working knowledge |

Clients don't just want AI. They want AI that connects to **their** platform, respects **their** governance, and deploys inside **their** existing infrastructure. This portfolio proves you can do all five.

---

## The Five Platform Ecosystems You Will Master

---

### 🔵 DATABRICKS — Mosaic AI Agent Framework

**What Databricks built:** A complete agent platform sitting on top of Delta Lake and Unity Catalog. Every component is integrated — you don't stitch things together.

**The native stack:**
- **LangGraph + ChatDatabricks** — build stateful agents using `databricks-langchain`, deploy to Model Serving in one step
- **Mosaic AI Vector Search** — managed vector index, auto-synced to Delta Lake tables
- **Unity Catalog tool registry** — register Python functions as governed agent tools with access controls
- **MLflow tracing** — every agent run is traced, cost attributed per call, full audit trail
- **Agent Evaluation + Review App** — human-in-the-loop feedback loop built into the platform
- **MCP (Model Context Protocol)** — agents connect to any API, database, or SaaS application
- **Lakebase** — persistent agent memory stored inside your lakehouse

**How agents are built on Databricks:**
```python
from databricks_langchain import ChatDatabricks
from langgraph.prebuilt import create_react_agent
import mlflow

mlflow.langchain.autolog()  # automatic tracing of every agent step

llm = ChatDatabricks(endpoint="databricks-claude-sonnet-4-5")
agent = create_react_agent(llm, tools=[your_unity_catalog_tool])
# Deploy to Databricks Model Serving → production in one step
```

**Your unique angle:** You already know Delta Lake, Unity Catalog, and MLflow deeply. Adding the agent layer takes weeks, not months. No pure AI engineer can compete on this ground.

---

### ❄️ SNOWFLAKE — Cortex AI Agent Stack

**What Snowflake built:** A native agentic stack for structured + unstructured enterprise data, powered by Claude (Snowflake + Anthropic partnership).

**The native stack:**
- **Cortex Agents** — REST API that orchestrates structured + unstructured data with LLMs in one call
- **Cortex Analyst** — text-to-SQL agent: generates SQL, reasons about correctness, fixes errors, runs it. GA with Claude powering it
- **Cortex Search** — semantic search over unstructured data. Beats OpenAI embeddings by 12%+ on benchmarks
- **Arctic + LLM access** — Snowflake's own LLM plus Claude, Llama, Mistral, Gemini — all inside Snowflake's security boundary
- **Semantic Model** — describe your data schema + business context so agents understand your tables correctly

**How agents are built on Snowflake:**
```python
import requests

# Cortex Agents REST API — structured + unstructured in one call
response = requests.post(
    f"{snowflake_host}/api/v2/cortex/agent:run",
    headers={"Authorization": f"Bearer {token}"},
    json={
        "model": "claude-sonnet-4-5",
        "tools": [
            {"tool_type": "cortex_analyst_text_to_sql",
             "tool_spec": {"semantic_model_file": "@stage/model.yaml"}},
            {"tool_type": "cortex_search",
             "tool_spec": {"service_name": "property_docs_search"}}
        ],
        "messages": [{"role": "user", "content": user_query}]
    }
)
```

**Your angle:** Any Snowflake client with complex data schemas needs someone who understands both the platform and how to build agents on top of it. Cortex Analyst especially — text-to-SQL that actually works requires understanding the semantic layer, which requires data platform expertise.

---

### 🟧 MICROSOFT FABRIC — Data Agents + Copilot Studio

**What Microsoft built:** Fabric Data Agents connect directly to OneLake and deploy into Teams/Microsoft 365 via Copilot Studio using the Agent-to-Agent (A2A) protocol.

**The native stack:**
- **Fabric Data Agents** — AI agents that understand your enterprise data schema, enforce governance policies, answer natural language questions about OneLake data
- **Copilot Studio** — low-code agent builder that connects Fabric agents via MCP server; publish to Teams, websites, M365
- **Microsoft Agent Framework 1.0** (GA April 2026) — AutoGen + Semantic Kernel unified into one production-ready framework
- **Semantic Kernel** — the underlying orchestration engine; supports Python and C#. Powers Azure AI Foundry and Fabric agents
- **A2A Protocol** — Copilot Studio agents talk directly to Fabric agents, M365 agents, and third-party agents
- **Multi-agent example**: Fabric agent pulls live sales data → M365 agent drafts a Word proposal → Azure agent schedules Outlook follow-up

**How agents are built on Fabric:**
```python
from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.connectors.ai.azure_ai_inference import AzureAIInferenceChatCompletion

# Semantic Kernel agent backed by Fabric data
kernel = sk.Kernel()
kernel.add_service(AzureAIInferenceChatCompletion("gpt-4o", client))
kernel.add_plugin(FabricDataPlugin(), plugin_name="FabricData")

agent = ChatCompletionAgent(kernel=kernel, name="FabricAnalyst",
    instructions="Answer questions about enterprise data using the FabricData plugin.")
```

**Your angle:** You know Microsoft Fabric deeply. Connecting a Fabric Data Agent to Copilot Studio and deploying it to Teams is a complete enterprise AI solution — and almost nobody builds this end-to-end.

---

### 🔷 AZURE — Azure AI Foundry + Microsoft Agent Framework

**What Azure built:** A full enterprise AI platform — model serving, governed LLM routing, agent orchestration, deployment, and monitoring in one stack.

**The native stack:**
- **Azure AI Foundry** — model catalog (Claude, GPT-4o, Llama, Mistral), AI Agent Service (GA), AI Gateway for governed LLM routing and cost attribution
- **Microsoft Agent Framework 1.0** — sequential, concurrent, handoff, group chat, Magentic-One multi-agent patterns. Supports Claude, Azure OpenAI, Bedrock, Gemini
- **Azure AI Search** — vector + hybrid search + semantic reranking; feeds RAG pipelines
- **Azure OpenAI** — GPT-4o, o1, o3 inside Azure's security boundary
- **OpenTelemetry + Azure Monitor** — native observability for every agent run
- **Entra ID** — agent identity, access control, authentication
- **Azure Container Apps** — deploy LangGraph or CrewAI agents as auto-scaling microservices

**How agents are built on Azure:**
```python
# pip install agent-framework azure-ai-projects
from microsoft.agents import AgentFramework, Agent
from azure.ai.projects import AIProjectClient

# Azure AI Foundry connection
client = AIProjectClient.from_connection_string(conn_str, DefaultAzureCredential())

agent = Agent(
    name="PropertyAnalyst",
    model="azure-openai/gpt-4o",
    tools=[azure_search_tool, fabric_tool],
    memory=AzureMemoryProvider()
)
framework = AgentFramework(agents=[agent], observability=AzureMonitorProvider())
```

**Deployment path:**
```
LangGraph agent (local)
  → Docker container
  → Azure Container Apps (auto-scaling, Entra ID auth)
  → Azure AI Foundry Model Serving
  → Azure Monitor + LangSmith observability
```

**Your angle:** Azure is your home turf. You understand Azure networking, security, cost management, and governance that pure AI engineers don't. A LangGraph agent deployed to Azure Container Apps with Entra ID and Azure Monitor is a complete enterprise deliverable.

---

### 🟡 AWS — Amazon Bedrock AgentCore

**What AWS built:** A framework-agnostic, serverless production platform for deploying any agent at enterprise scale. GA October 2025. No infrastructure management required.

**The native stack:**
- **AgentCore Runtime** — serverless, low-latency agent execution. Deploy LangGraph, CrewAI, LlamaIndex, Strands in seconds. Session isolation, multimodal, long-running agents supported
- **AgentCore Memory** — short-term (session state via LangGraph checkpointing) + long-term (cross-session preferences, summaries). Integrates directly with LangGraph via `AgentCoreMemorySaver`
- **AgentCore Gateway** — wraps Lambda functions, APIs, OpenAPI specs as MCP-compatible agent tools. Instant tool exposure without rewriting code
- **AgentCore Observability** — step-by-step execution visualization, metadata tagging, trajectory inspection, custom scoring
- **AgentCore Identity** — IAM-based agent auth to AWS services + third-party tools (GitHub, Salesforce, Slack)
- **AgentCore Browser + Code Interpreter** — managed browser + sandboxed code execution for agents
- **Strands Agents** — AWS's own open-source framework; simple config-based agent definition, fastest path to Bedrock deployment
- **MCP + A2A** — both protocols supported natively

**LangGraph + AgentCore pattern (production-ready):**
```python
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from langgraph_checkpoint_aws import AgentCoreMemorySaver, AgentCoreMemoryStore
from langgraph.prebuilt import create_react_agent
from langchain.chat_models import init_chat_model

app = BedrockAgentCoreApp()

llm = init_chat_model(
    "us.anthropic.claude-3-5-haiku-20241022-v1:0",
    model_provider="bedrock_converse"
)
# Short-term memory — session state persisted across container restarts
checkpointer = AgentCoreMemorySaver(MEMORY_ID, region_name="ap-southeast-2")
# Long-term memory — cross-session preferences + summaries
store = AgentCoreMemoryStore(MEMORY_ID, region_name="ap-southeast-2")

agent = create_react_agent(llm, tools=tools, checkpointer=checkpointer, store=store)

# Deploy: agentcore launch → serverless in Sydney region in seconds
```

**Your angle:** Sydney (ap-southeast-2) is one of AgentCore's launch regions. Australian enterprise clients on AWS need someone who can deploy a production agent with proper IAM, persistent memory, and observability. That's you.

---

## Agentic Framework Comparison — Know All of Them

| Framework | Best for | Use when |
|-----------|----------|----------|
| **LangGraph** | Stateful agents, loops, checkpointing, HITL | Your core framework — use on every platform |
| **CrewAI** | Role-based multi-agent collaboration | Autonomous research/reporting workflows |
| **Microsoft Agent Framework 1.0** | Azure/Fabric/M365 enterprise agents | Any Microsoft-stack client |
| **Semantic Kernel** | Azure AI Foundry + Fabric integration, .NET + Python | Inside Microsoft deployments |
| **LlamaIndex** | Large-scale document ingestion, enterprise knowledge bases | Data-heavy RAG on Databricks or Snowflake |
| **Strands Agents** | Fast, simple AWS deployments | AWS clients wanting low-overhead agents |
| **Bedrock Agents** (native) | Fully managed AWS agents, zero infrastructure | AWS clients wanting no framework complexity |

**The senior engineer signal:** You know *when to use which framework and why* — not just how to use one.

---

## Progress Tracker

### ✅ COMPLETED

#### Hermes Agent — AU Real Estate News Agent (13 May 2026)
- Claude Haiku brain + RSS feeds (ABC, Domain, REA, AFR) + Telegram delivery
- **Pending:** Deploy to Hostinger VPS for 24/7 autonomous delivery

#### Week 1 — Foundation Scripts

**Script 1 ✅** — Direct Claude API call, token counting
**Script 2 ✅** — Conversation memory (history list = memory)
**Script 3 ✅** — Tool schemas, agentic loop, tool execution
**Script 4 ✅** — Streaming responses, token cost awareness

---

### 🔄 IN PROGRESS

**Script 5** — Structured output: Claude returns JSON, batch processing, save to file

---

### 📋 PHASE 1: FINISH FOUNDATIONS

**Script 6 — Context Management**
- Sliding window, conversation summarisation, prompt caching
- Deep concept: Token budget control in production

---

### 📋 PHASE 2: CORE AGENTIC STACK + DATA PLATFORMS

**Script 7 — LangChain Basics**
- Chains, LCEL, prompt templates, retrievers
- Why: Understand components before LangGraph abstracts them

**Script 8 — LangGraph: Stateful Agents** ← CRITICAL
- StateGraph, nodes, edges, TypedDict, checkpointing
- Prove it: Agent fails mid-task, resumes from exact checkpoint without restarting

**Script 9 — LangGraph: Human-in-the-Loop** ← ENTERPRISE REQUIREMENT
- interrupt_before, interrupt_after, state inspection, resume after approval
- Prove it: Agent pauses before sending email, human approves, agent continues

**Script 10 — RAG Part 1: Chunking**
- PDF loading, chunk size/overlap tradeoffs, metadata enrichment
- Deep concept: Chunk quality determines RAG quality end-to-end

**Script 11 — RAG Part 2: Embeddings + Vector Search**
- ChromaDB, semantic search, similarity scoring
- Deep concept: Embeddings as vectors in space — similarity = relevance

**Script 12 — RAG Part 3: Full Q&A Pipeline**
- Load → chunk → embed → store → query → answer with citations
- Prove it: Show exactly which chunks retrieved and why

**Script 13 — RAG Evaluation with RAGAS** ← SENIOR ENGINEER SIGNAL
- Faithfulness, answer relevancy, context precision, context recall
- Deep concept: How do you prove your RAG works? This is how.

**Script 14 — Agentic RAG (Self-Correcting)**
- Agent decides when to retrieve, evaluates chunk quality, rewrites query if poor, retries
- LangGraph graph: retrieve → score → rewrite if needed → answer

**Script 15 — RAG on Databricks (Mosaic AI)**
- Mosaic AI Vector Search, Unity Catalog tools, MLflow tracing, ChatDatabricks
- Prove it: Natural language query over a Delta Lake table, fully traced in MLflow

**Script 16 — Snowflake Cortex Agents**
- Cortex Analyst (text-to-SQL) + Cortex Search (unstructured) in one agent
- Prove it: "Which properties had highest rental yield last quarter?" → agent writes + executes SQL

---

### 📋 PHASE 3: MULTI-AGENT + MICROSOFT STACK

**Script 17 — CrewAI: Role-Based Multi-Agent**
- 3 agents: Researcher, Analyst, Writer — automated property market report
- Deep concept: CrewAI vs LangGraph — when each makes sense

**Script 18 — Microsoft Agent Framework + Azure AI Foundry**
- Microsoft Agent Framework 1.0: multi-agent handoff workflow
- Connect to Azure AI Foundry (model serving + AI Gateway)
- Prove it: Researcher → Analyst → Writer handoff chain, fully governed via Azure

**Script 19 — Fabric Data Agent + Copilot Studio**
- Build Fabric Data Agent over a lakehouse dataset
- Connect to Copilot Studio via MCP server (A2A protocol)
- Deploy to Microsoft Teams
- Prove it: Business user asks question in Teams, Fabric agent answers from OneLake

---

### 📋 PHASE 4: AWS + PRODUCTION DEPLOYMENT

**Script 20 — LangGraph on AWS Bedrock AgentCore**
- LangGraph + AgentCoreMemorySaver (persistent memory across sessions)
- AgentCore Gateway wrapping a Lambda function as an MCP tool
- Deploy to AgentCore Runtime (Sydney region)
- Prove it: Serverless agent, memory survives container restart, deployed in seconds

**Script 21 — Observability Across Platforms**
- LangSmith for LangGraph tracing
- MLflow for Databricks agent runs
- AgentCore Observability for AWS agent runs
- Azure Monitor for Azure deployments
- Deep concept: You can explain every decision every agent made in production

**Script 22 — Streamlit UI**
- Web interface for RAG pipeline — business users click buttons, not terminals

**Script 23 — Docker + Azure Container Apps**
- Containerise LangGraph agent, deploy to Azure Container Apps
- Entra ID auth, auto-scaling, Azure Monitor logging

---

## 8 Portfolio Projects

| # | Project | Platform | Framework | What it proves |
|---|---------|----------|-----------|----------------|
| 1 | AU Real Estate News Agent | Local / Telegram | Hermes + Claude | Autonomous agents, real delivery |
| 2 | Stateful Research Agent + HITL | Azure | LangGraph | Production stateful agents + human approval gates |
| 3 | RAG Chatbot with RAGAS Evaluation | Local → Azure | LangChain + LangGraph | RAG that's provably working, not just built |
| 4 | Agentic AI on Databricks Lakehouse | Databricks | LangGraph + Mosaic AI | Your 9-year data platform differentiator |
| 5 | Snowflake Cortex Agent | Snowflake | Cortex Agents + Claude | Structured + unstructured enterprise data |
| 6 | Fabric + Copilot Studio Multi-Agent | Fabric + Teams | Semantic Kernel + A2A | Full Microsoft enterprise AI stack |
| 7 | LangGraph Agent on AWS AgentCore | AWS Sydney | LangGraph + AgentCore | Cross-cloud, serverless, persistent memory |
| 8 | Full Production System | Azure | CrewAI + LangSmith + Docker | Build → evaluate → deploy → observe |

---

## Key Concepts Map

### What Gets You $120-150/hr (Not $80/hr)

The difference isn't knowing more tools. It's being able to answer production questions:

| Client asks | Your answer |
|-------------|-------------|
| "How do you know your RAG is working?" | RAGAS evaluation scores + retrieval quality metrics |
| "What if the agent fails mid-task?" | LangGraph checkpointing — resumes from exact failure point |
| "Can a human approve before it acts?" | Human-in-the-loop interrupt gates — built and demonstrated |
| "How do we monitor it in production?" | LangSmith / MLflow / AgentCore Observability — full audit trail |
| "We're on Databricks" | Mosaic AI + ChatDatabricks + Unity Catalog tools |
| "We're on Snowflake" | Cortex Agents + Cortex Analyst text-to-SQL |
| "We use Microsoft Fabric and Teams" | Fabric Data Agent + Copilot Studio A2A deployment |
| "We're AWS-based" | LangGraph on Bedrock AgentCore, Sydney region |
| "We need it on Azure" | Azure AI Foundry + Container Apps + Entra ID |

---

## Target Contract Profile

**Title:** AI Solution Architect / AI Agent Engineer
**Rate:** $120-150/hr
**Pitch:**
*"I build production-grade AI agents on top of enterprise data platforms. I've spent 9 years architecting on Databricks, Microsoft Fabric, and Azure — and I now build agentic AI systems on top of that infrastructure. I work across every major platform: Mosaic AI on Databricks, Cortex Agents on Snowflake, Fabric Data Agents for Microsoft clients, Azure AI Foundry, and AWS Bedrock AgentCore. I don't just build demos — I build agents with proper governance, evaluation, observability, and deployment."*

**Unique angle:** Most AI engineers don't know data platforms. Most data engineers don't know agents. You know both — across five platforms — and you go deep.

---

## GitHub Repository
https://github.com/rajat301/ai-agent-portfolio

## Contact
- LinkedIn: linkedin.com/in/rajat-gupta-353a6579
- Email: rajatgupta301200@gmail.com
- Location: Sydney, NSW, Australia