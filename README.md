

# 🚀 Multi-Agent RAG System (MAR-RAG)

## 🧠 Overview

**MAR-RAG (Multi-Agent Retrieval-Augmented Generation)** is a microservice-based system designed for intelligent query processing. It leverages a dynamic set of autonomous agents—including retrievers, language models, and domain-specific services—to deliver high-quality, context-aware answers.

A central **Query Coordinator** orchestrates workflows and dynamically determines which agents to involve based on query intent, user context, and system state.

---

## 🏗️ System Architecture

The MAR-RAG system is modular and horizontally scalable, consisting of five main layers:

### 1. **API & Load Balancing**

* **API Gateway** (Kong or Nginx): Manages incoming queries and routes them securely.
* **Load Balancer** (HAProxy): Ensures high availability and traffic distribution.

### 2. **Core Agents**

* `QueryCoordinatorService`: Central brain that routes tasks to agents.
* `QueryAgentService`: Parses and classifies incoming queries.
* `RetrievalAgentService`: Embedding-based document retriever.
* `ResponseGenerationAgentService`: Uses LLMs to generate natural language responses.
* `ContextSynthesisAgentService`: Adds memory and multi-turn context understanding.

### 3. **Supporting Services**

* **Vector DB**: `ChromaDB` or `Faiss` for similarity search.
* **LLM Backend**: `Ollama`, `LLaMA2`, or other open models.
* **Embedding Service**: SentenceTransformers-based encoding.
* **Cache Layer**: Redis for session and context storage.
* **Authentication**: OAuth2.
* **Monitoring**: Prometheus + Grafana.
* **Logging**: ELK stack (Elasticsearch, Logstash, Kibana).
* **Configuration Management**: Consul.

### 4. **Data Layer**

* **Object Storage**: MinIO or AWS S3 for document storage.
* **Metadata DB**: PostgreSQL.
* **Vector Index**: Faiss/Annoy.
* **Session Store**: Redis Cluster.

### 5. **Infrastructure**

* Containerized with **Docker**.
* Orchestrated using **Kubernetes**.
* Secured and observable through **Istio Service Mesh**.

---

## 🔁 Dynamic Agent Involvement

For every query, the `QueryCoordinatorService` dynamically selects agents based on:

* 🧠 Query intent
* 📚 Available context
* 🧩 Domain knowledge
* ⚙️ Service availability and health

### Agent Involvement Examples

| Scenario                  | Agents Involved                                               |
| ------------------------- | ------------------------------------------------------------- |
| Simple factual query      | `["QueryAgent", "RetrieverAgent", "ResponseGenerationAgent"]` |
| Cybersecurity domain      | `["ThreatIntelAgent", "RetrieverAgent", "SecurityLLM"]`       |
| Multi-turn conversation   | `["RetrieverAgent", "ContextSynthesisAgent", "LLM"]`          |
| Domain-specific retrieval | `["QueryAgent", "VectorDBService", "LLM"]`                    |

---

## 📥 Input / 📤 Output Examples

Below are real API examples showcasing how the system responds to various queries.

---

### ✅ Example 1: Machine Learning

**Input**

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the key features of machine learning?",
    "user_id": "user123"
  }'
```

**Output**

```json
{
  "user_id": "user123",
  "query": "What are the key features of machine learning?",
  "answer": "Key features include learning from data, adapting, predicting outcomes, and improving performance over time.",
  "retrieved_documents": [
    {
      "title": "Introduction to Machine Learning",
      "source": "Wikipedia",
      "content_snippet": "Machine learning enables systems to learn from data, identify patterns..."
    }
  ],
  "agents_involved": ["RetrieverAgent", "LLMAnswerAgent"]
}
```

---

### ✅ Example 2: DevOps CI/CD

**Input**

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is CI/CD in DevOps?",
    "user_id": "abdo_dev"
  }'
```

**Output**

```json
{
  "user_id": "abdo_dev",
  "query": "What is CI/CD in DevOps?",
  "answer": "CI/CD refers to Continuous Integration and Continuous Deployment...",
  "retrieved_documents": [
    {
      "title": "CI/CD Pipeline Explained",
      "source": "DevOps Handbook",
      "content_snippet": "CI/CD automates software delivery, ensuring reliable, frequent deployments."
    }
  ],
  "agents_involved": ["RetrieverAgent", "PipelineAgent", "AnswerAgent"]
}
```

---

### ✅ Example 3: Cybersecurity - Phishing

**Input**

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How can we detect phishing attacks?",
    "user_id": "soc_team"
  }'
```

**Output**

```json
{
  "user_id": "soc_team",
  "query": "How can we detect phishing attacks?",
  "answer": "Phishing can be detected through filters, anomaly detection, DNS analysis, and training.",
  "retrieved_documents": [
    {
      "title": "Phishing Detection Techniques",
      "source": "MITRE ATT&CK",
      "content_snippet": "Analysis of headers, domains, and behavior are key phishing indicators."
    }
  ],
  "agents_involved": ["ThreatIntelAgent", "RetrieverAgent", "SecurityLLM"]
}
```

---

### ✅ Example 4: HR Domain

**Input**

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are common reasons for employee turnover?",
    "user_id": "hr_admin"
  }'
```

**Output**

```json
{
  "user_id": "hr_admin",
  "query": "What are common reasons for employee turnover?",
  "answer": "Lack of growth, poor management, and toxic culture are key turnover drivers.",
  "retrieved_documents": [
    {
      "title": "Top Causes of Employee Turnover",
      "source": "Harvard Business Review",
      "content_snippet": "Surveys show poor leadership and lack of recognition as major exit factors."
    }
  ],
  "agents_involved": ["HRDomainAgent", "RetrieverAgent", "LLMAnswerAgent"]
}
```

---

### ✅ Example 5: Financial KPI Query

**Input**

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the main KPIs in financial performance?",
    "user_id": "finance_bot"
  }'
```

**Output**

```json
{
  "user_id": "finance_bot",
  "query": "What are the main KPIs in financial performance?",
  "answer": "Revenue, net profit, ROI, and EBITDA are essential KPIs for financial performance.",
  "retrieved_documents": [
    {
      "title": "Financial KPIs Overview",
      "source": "Investopedia",
      "content_snippet": "KPIs include ROA, current ratio, and gross profit margin..."
    }
  ],
  "agents_involved": ["FinanceAgent", "RetrieverAgent", "SummaryAgent"]
}
```

---

## 📊 Monitoring & Observability

* **Prometheus + Grafana**: Real-time metrics, latency, throughput.
* **ELK Stack**: Centralized logs for agents and microservices.
* **Kubernetes Dashboard**: Health checks, autoscaling, failover, deployments.

---

## 🔐 Security

* **OAuth2 Authentication**
* **Role-Based Access Control (RBAC)**
* **API Gateway Rate Limiting**

---

## 🧰 Deployment Stack

* **Docker & Kubernetes**
* **Istio Service Mesh**
* **PostgreSQL, Redis, MinIO, ChromaDB, Faiss**

---
