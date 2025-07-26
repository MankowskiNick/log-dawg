# Log Dawg Azure Migration: Actionable Task Breakdown

This document splits the deployment plan into small, simple, actionable modifications. Each task is designed to be completed with minimal context or deep understanding of the overall project.

---

## 1. Backend Refactoring

### 1.1 Replace Disk-Based Git Manager
- Remove local disk repo management code.
- Create a `GitProvider` interface with methods:
  - `list_files(repo_id, ref)`
  - `get_file_content(repo_id, path, ref)`
  - `list_commits(repo_id)`
- Implement `GitHubClient` and `AzureDevOpsClient` classes using respective APIs.
- Refactor backend to use these clients for all repo operations.

### 1.2 Migrate Report Storage to Database
- Create a `reports` table in Postgres:
  - `id UUID`, `repo_id UUID`, `commit_hash TEXT`, `created_at TIMESTAMP`, `status ENUM`, `report_data JSONB`
- Refactor report read/write logic to use DB instead of disk.
- Update FastAPI endpoints to interact with DB for reports.

### 1.3 Integrate Async Job Handling
- Add Azure Service Bus or Queue Storage integration.
- Push analysis jobs to queue on webhook/user action.
- Set up worker (Celery/RQ) to consume jobs and write results to DB.

---

## 2. Database Changes

### 2.1 Database Creation & Models
- Create the PostgreSQL database instance in Azure (Flexible Server).
- Create models for:
  - Repository metadata
  - Credentials (encrypted)
  - Users
  - Reports
- Use Alembic for migrations.

### 2.2 Multi-Tenancy Support
- Add `org_id` or `repo_id` to all relevant tables.
- Ensure all queries filter by `org_id`.

---

## 3. Secrets Management

### 3.1 Integrate Azure Key Vault
- Store all credentials and encryption keys in Key Vault.
- Refactor backend to load secrets at runtime using Managed Identity.

---

## 4. Frontend Changes

### 4.1 Update API URLs
- Change API URLs to point to backend App Service domain.

### 4.2 Add Report Status UI
- Display report status from DB in frontend.

### 4.3 Add Credential Management UI
- Allow users to manage repository credentials in frontend.

---

## 5. Deployment & CI/CD

### 5.1 Containerize Backend
- Ensure Dockerfile is production-ready for FastAPI.

### 5.2 Set Up CI/CD
- Use GitHub Actions or Azure DevOps Pipelines to:
  - Build/deploy frontend to Static Web Apps
  - Build/deploy backend to App Service/AKS
  - Apply DB migrations

---

## 6. Security

### 6.1 Encryption
- Encrypt tokens in DB using key from Key Vault.

### 6.2 Network Isolation
- Use private endpoints for DB and Key Vault.

### 6.3 HTTPS
- Enforce TLS for all endpoints.

---

## 7. Azure Provisioning

### 7.1 Provision Resources
- App Service (or AKS)
- PostgreSQL Flexible Server
- Key Vault
- Service Bus
- Static Web Apps

---

## 8. Next Steps
- Implement each task above as a separate PR or commit.
- Track progress in project management tool.
