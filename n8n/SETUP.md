# n8n deterministic RAG setup

This workflow retrieves document context before every model call. FastAPI remains responsible for ingestion and semantic retrieval; n8n remains responsible for orchestration and final answer generation.

## Why retrieval is deterministic

The original prototype connected an HTTP Request Tool to an AI Agent. With the tested local `mistral:latest` model and n8n AI Agent v3.1, the model sometimes printed a tool call as plain JSON instead of emitting a structured tool call. The tool node was therefore skipped and the model answered from memory.

For a document question-answering MVP, retrieval should not be optional. The Version 1 workflow uses an ordinary HTTP Request node before the Basic LLM Chain so every answer receives retrieved evidence.

## Workflow shape

```text
Chat Trigger
     |
     v
HTTP Request: Search Knowledge Base
     |
     v
Basic LLM Chain ----- Local Ollama Chat Model
```

## Prerequisites

1. The Docker Compose stack is running.
2. At least one PDF has been indexed through `POST /documents/upload` or the batch ingestion script.
3. Ollama is running on the host and has `mistral:latest` installed.
4. A direct `POST /search` request returns relevant chunks.

## Import the included workflow

1. Open <http://localhost:5678>.
2. Select **Import from File**.
3. Import `n8n/workflows/docuagent-deterministic-rag.json`.
4. Open **Local Ollama Chat Model** and select an OpenAI-compatible credential configured as shown below.
5. Save the workflow and open the chat.

The exported workflow intentionally contains no credential ID or secret so it is safe to version-control and reuse on another n8n installation.

## Configure the local chat-model credential

The workflow uses n8n's OpenAI Chat Model node against Ollama's OpenAI-compatible endpoint.

| Field | Value |
| --- | --- |
| API key | `ollama` |
| Base URL | `http://host.docker.internal:11434/v1` |
| Model | `mistral:latest` |

The key is a required placeholder for the client. Ollama ignores it and all inference remains local.

## Manual node configuration

### 1. Chat Trigger

Add **When chat message received** and connect its main output to a regular **HTTP Request** node.

### 2. Search Knowledge Base

Use the regular HTTP Request node, not HTTP Request Tool.

| Field | Value |
| --- | --- |
| Name | `Search Knowledge Base` |
| Method | `POST` |
| URL | `http://api:8000/search` |
| Authentication | `None` |
| Send Body | enabled |
| Body Content Type | `JSON` |
| Response Format | `JSON` |

Add these body fields:

| Name | Value |
| --- | --- |
| `query` | `{{ $json.chatInput }}` |
| `top_k` | `4` |

If n8n runs outside this Compose project, use the matching URL:

| n8n location | Search URL |
| --- | --- |
| This project's Compose service | `http://api:8000/search` |
| Directly on the host | `http://localhost:8000/search` |
| Separate Docker container | `http://host.docker.internal:8000/search` |

### 3. Basic LLM Chain

Connect **Search Knowledge Base** to **Basic LLM Chain**. Set the prompt source to **Define below**, then paste the complete contents of `prompts/rag_answer_prompt.txt`.

### 4. Chat model

Attach **OpenAI Chat Model** to the Basic LLM Chain's model connector. Select the local Ollama credential and `mistral:latest`.

## Verification

Ask:

```text
What are the four core functions of the NIST AI RMF?
```

A successful execution must show:

1. Chat Trigger ran.
2. Search Knowledge Base called `/search`.
3. Its response includes `nist-ai-rmf-1.0.pdf`, page numbers, and scores.
4. Basic LLM Chain ran after retrieval.
5. The answer states `GOVERN`, `MAP`, `MEASURE`, and `MANAGE` and cites the retrieved file and pages.

Also test retrieval from the RAG paper:

```text
How do RAG-Sequence and RAG-Token differ?
```

And Thai retrieval:

```text
องค์กรควรจัดโครงสร้างการบริหารภายในเพื่อกำกับดูแล AI อย่างไร?
```

## Troubleshooting

### Search returns the wrong document

- Confirm the expected PDF was indexed; storing a PDF under `data/documents` does not automatically add it to Qdrant.
- Run the batch ingestion script or upload the file through the API.
- Confirm documents and queries use the same embedding provider, model, and Qdrant collection.

### FastAPI is unreachable

- From this Compose service, use `http://api:8000/search`.
- Confirm `docker compose ps` reports the API as healthy.
- Confirm <http://localhost:8000/health> returns `{"status":"ok"}`.

### Ollama is unreachable

- Confirm the Ollama desktop application is running.
- Confirm the credential Base URL is `http://host.docker.internal:11434/v1`.
- Confirm `mistral:latest` is installed locally.

### The answer invents a citation

- Inspect the Search Knowledge Base output before inspecting the final answer.
- Confirm each result contains `source` and `page`.
- Re-copy `prompts/rag_answer_prompt.txt` into the Basic LLM Chain.

## Optional agent experiment

`prompts/agent_system_prompt.txt` is retained for experimenting with a tool-capable hosted model or a local model verified to emit structured tool calls through n8n. It is not the default Version 1 workflow because retrieval reliability is more important than optional tool selection for this document-only assistant.
