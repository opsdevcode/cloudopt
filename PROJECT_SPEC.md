# CloudOpt.dev

CloudOpt.dev is an AI-powered FinOps platform designed to analyze and optimize cloud infrastructure costs, with a primary focus on AWS and Kubernetes.

The platform will ingest cloud billing data and infrastructure signals, analyze them using AI, and generate actionable cost optimization recommendations. Later versions will automatically create Terraform changes and GitHub pull requests to implement cost-saving improvements.

The target users are platform engineers, DevOps teams, and FinOps teams managing AWS infrastructure.

Primary differentiator: deep Kubernetes and Karpenter optimization.

---

## MVP Goals

The first version should provide:

1. AWS cost data ingestion
2. Infrastructure analysis
3. Cost optimization findings
4. API access to findings
5. CLI scan commands

Example output:

Top savings opportunities:

1. Reduce EKS node size
Savings: $1,284/month

2. Delete unused EBS volumes
Savings: $412/month

3. Switch workloads to spot
Savings: $2,900/month

---

## Technology Stack

Backend
- Python 3.11+
- FastAPI
- PostgreSQL
- SQLAlchemy
- Alembic
- Redis (job queue)
- Docker

CLI
- Typer

AI Layer
- OpenAI or Anthropic API

Infrastructure Signals
- AWS Cost Explorer
- AWS CUR (Cost Usage Reports)
- EKS API
- EC2 API
- CloudWatch metrics

---

## Architecture

CloudOpt consists of three main components:

API Server
Handles authentication, APIs, and orchestration.

Worker Service
Processes analysis jobs and generates cost findings.

CLI Tool
Allows engineers to run scans locally or trigger analysis jobs.

Flow:

AWS Data Sources
↓
Ingestion Service
↓
Normalized Cost Database
↓
Analysis Engine
↓
AI Recommendation Engine
↓
Findings API + CLI

---

## Initial Features

Cost Spike Analysis
Detect and explain sudden increases in AWS spend.

Kubernetes Cost Analysis
Analyze:
- pod resource requests vs usage
- node utilization
- Karpenter node pools

Infrastructure Waste Detection
Identify:

- unattached EBS volumes
- idle load balancers
- orphaned ENIs
- unused snapshots

Right-Sizing Recommendations
Example:

Change instance:
m6i.2xlarge → m6i.xlarge

Estimated savings:
$2,134/month

---

## Repository Structure

cloudopt/
  apps/
    api/
    worker/
    cli/
  packages/
    core/
    aws/
    ai/
    finops/
  docs/
  infra/
  tests/

---

## CLI

CLI command:

cloudopt scan

Example output:

CloudOpt Scan Results

Cluster: production

Recommendation:
Reduce node size from m6i.2xlarge → m6i.xlarge

Savings:
$2,134/month

---

## Future Features

Terraform PR automation

Example:

CloudOpt generates:

terraform diff

removes unused EBS volumes
reduces node sizes
changes autoscaling settings

Then opens a GitHub pull request.

---

## Product Vision

CloudOpt.dev should become an AI-powered autonomous FinOps engineer.

Instead of dashboards, it should:

Detect cost issues
Explain root causes
Recommend optimizations
Optionally implement fixes