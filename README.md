# Multi-Agent RAG System (MAR-RAG)

## 🧠 Overview

This project implements a **Multi-Agent Retrieval-Augmented Generation (MAR-RAG)** system using a microservices architecture.

User queries are processed by a central **Query Coordinator**, which delegates tasks to intelligent agents such as retrieval, generation, synthesis, or domain-specific services (e.g., ThreatIntel). The response includes a dynamic list of agents involved for traceability.

---

## 📐 System Architecture

The system is composed of the following layers:

### 1. **API & Load Balancing Layer**
- **API Gateway (Kong/Nginx)**: Entry point for client queries.
- **Load Balancer (HAProxy)**: Distributes traffic to internal services.

### 2. **Core Microservices (Agents)**
- `QueryCoordinatorService`: Orchestrates the workflow.
- `QueryAgentService`: Analyzes and classifies queries.
- `RetrievalAgentService`: Fetches relevant documents via embeddings.
- `ResponseGenerationAgentService`: Uses an LLM to generate answers.
- `ContextSynthesisAgentService`: Merges session or contextual info when needed.

### 3. **Supporting Services**
- `Vector Database (ChromaDB)`
- `LLM Service (Ollama/Llama2)`
- `Embedding Service (SentenceTransformers)`
- `Cache Service (Redis)`
- `Authentication Service (OAuth2)`
- `Monitoring (Prometheus + Grafana)`
- `Logging (ELK Stack)`
- `Config Management (Consul)`

### 4. **Data Layer**
- `Document Storage (MinIO/S3)`
- `Metadata DB (PostgreSQL)`
- `Vector Index (Faiss/Annoy)`
- `Session Store (Redis Cluster)`

### 5. **Infrastructure**
- Containerized with **Docker**
- Managed with **Kubernetes**
- Secured and observed via **Istio Service Mesh**

---

## 🔁 Dynamic Agent Involvement

Each query results in a custom list of agents being called based on the query type.

### ✅ Examples

#### Example A: Simple Factual Query
```json
"agents_involved": ["QueryAgent", "RetrieverAgent", "ResponseGenerationAgent"]
Example B: Cybersecurity Question
json
Copier
Modifier
"agents_involved": ["ThreatIntelAgent", "RetrieverAgent", "SecurityLLM"]
Example C: Multi-turn Chat / Contextual
json
Copier
Modifier
"agents_involved": ["RetrieverAgent", "ContextSynthesisAgent", "LLM"]
Example D: Pre-embedded Domain Retrieval
json
Copier
Modifier
"agents_involved": ["QueryAgent", "VectorDBService", "LLM"]
The "agents_involved" field in the API response is generated dynamically by the QueryCoordinatorService depending on:

Query intent

Available context

Required domain knowledge

System health and service availability

📌 Use Case Examples
✅ Example 1: Machine Learning
Input

bash
Copier
Modifier
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the key features of machine learning?",
    "user_id": "user123"
  }'
Output

json
Copier
Modifier
{
  "user_id": "user123",
  "query": "What are the key features of machine learning?",
  "answer": "Key features of machine learning include the ability to learn from data, adapt to new information, make predictions, and improve performance over time without explicit programming.",
  "retrieved_documents": [
    {
      "title": "Introduction to Machine Learning",
      "source": "Wikipedia",
      "content_snippet": "Machine learning focuses on enabling systems to learn from data, identify patterns, and make decisions..."
    }
  ],
  "agents_involved": ["RetrieverAgent", "LLMAnswerAgent"]
}
✅ Example 2: DevOps CI/CD
Input

bash
Copier
Modifier
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is CI/CD in DevOps?",
    "user_id": "abdo_dev"
  }'
Output

json
Copier
Modifier
{
  "user_id": "abdo_dev",
  "query": "What is CI/CD in DevOps?",
  "answer": "CI/CD stands for Continuous Integration and Continuous Deployment. It's a DevOps practice that enables teams to integrate code changes regularly, automatically test them, and deploy to production faster and more reliably.",
  "retrieved_documents": [
    {
      "title": "CI/CD Pipeline Explained",
      "source": "DevOps Handbook",
      "content_snippet": "CI/CD automates the software delivery process, ensuring code changes are automatically built, tested, and deployed."
    }
  ],
  "agents_involved": ["RetrieverAgent", "PipelineAgent", "AnswerAgent"]
}
✅ Example 3: Cybersecurity - Phishing
Input

bash
Copier
Modifier
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How can we detect phishing attacks?",
    "user_id": "soc_team"
  }'
Output

json
Copier
Modifier
{
  "user_id": "soc_team",
  "query": "How can we detect phishing attacks?",
  "answer": "Phishing attacks can be detected using email filters, anomaly detection algorithms, DNS analysis, and employee awareness training. SOC tools like SIEMs often flag suspicious emails or traffic.",
  "retrieved_documents": [
    {
      "title": "Phishing Detection Techniques",
      "source": "MITRE ATT&CK",
      "content_snippet": "Detection methods include analyzing headers, domains, payload behavior, and user interaction patterns."
    }
  ],
  "agents_involved": ["ThreatIntelAgent", "RetrieverAgent", "SecurityLLM"]
}
✅ Example 4: HR Question
Input

bash
Copier
Modifier
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are common reasons for employee turnover?",
    "user_id": "hr_admin"
  }'
Output

json
Copier
Modifier
{
  "user_id": "hr_admin",
  "query": "What are common reasons for employee turnover?",
  "answer": "Common reasons for employee turnover include lack of career growth, poor management, low compensation, toxic work culture, and lack of work-life balance.",
  "retrieved_documents": [
    {
      "title": "Top Causes of Employee Turnover",
      "source": "Harvard Business Review",
      "content_snippet": "Survey results show poor leadership and lack of recognition as key drivers of voluntary exits."
    }
  ],
  "agents_involved": ["HRDomainAgent", "RetrieverAgent", "LLMAnswerAgent"]
}
✅ Example 5: Financial RAG
Input

bash
Copier
Modifier
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the main KPIs in financial performance?",
    "user_id": "finance_bot"
  }'
Output

json
Copier
Modifier
{
  "user_id": "finance_bot",
  "query": "What are the main KPIs in financial performance?",
  "answer": "The main KPIs include revenue, net profit margin, operating cash flow, ROI, and EBITDA. These metrics provide insight into a company’s profitability, efficiency, and financial stability.",
  "retrieved_documents": [
    {
      "title": "Financial KPIs Overview",
      "source": "Investopedia",
      "content_snippet": "Key indicators include return on assets (ROA), current ratio, and gross profit margin..."
    }
  ],
  "agents_involved": ["FinanceAgent", "RetrieverAgent", "SummaryAgent"]
}
📊 Monitoring & Logging
Prometheus + Grafana: Metrics, latency, and load visualization.

ELK Stack: Centralized logging for all agents and services.

Kubernetes: Horizontal auto-scaling, failover, rolling updates.

🔐 Security & Access
OAuth2 for authentication.

Role-based agent permissions.

Rate limiting at API Gateway.

📦 Deployment Stack
Docker

Kubernetes (K8s)

Istio Service Mesh

ChromaDB, Faiss, MinIO, PostgreSQL, Redis

