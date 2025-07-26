# Log Dawg - Azure Deployment
## **1. Goals**

* Deploy the **FastAPI backend**, **React frontend**, and **database** in Azure.
* Migrate from disk-based repo management to an **API-based Git manager** (remote fetch).
* Replace disk-based report storage with **database-backed report storage**.
* Support **multi-tenant architecture** with secure credential storage and scalability.

---

## **2. Proposed Azure Architecture**

### **2.1 High-Level Overview**

1. **Frontend (React/Vite):**

   * Deployed as static files in **Azure Static Web Apps** or **Azure Blob Storage (Static website hosting)** behind Azure CDN.
   * Communicates with the FastAPI backend via API Gateway.

2. **Backend (FastAPI):**

   * Containerized and deployed to **Azure App Service (Linux)** or **Azure Kubernetes Service (AKS)** for scalability.
   * Handles webhooks, analysis jobs, API endpoints.

3. **Database:**

   * Use **Azure Database for PostgreSQL Flexible Server** (or Azure SQL if preferred).
   * Stores:

     * Repository metadata & credentials (encrypted).
     * Analysis reports.
     * User accounts & configuration.

4. **Storage (optional):**

   * Any large binary artifacts (if not suitable for DB) go to **Azure Blob Storage** with signed URL access.

5. **Secrets:**

   * All credentials (PATs, DB connection string, encryption keys) stored in **Azure Key Vault**.

6. **Queues / Workers (for scalability):**

   * Use **Azure Queue Storage** or **Azure Service Bus** for job dispatch.
   * Workers run the Git analysis jobs asynchronously.

---

### **2.2 Diagram**

```
[Frontend - React/Vite]  -->  [Azure Static Web Apps/CDN]
                                  |
                                  v
                             [API Gateway]
                                  |
                          [Azure App Service]
                             (FastAPI backend)
                                  |
          ------------------------------------------------
          |                        |                    |
    [Azure DB (Postgres)]   [Azure Blob Storage]   [Azure Service Bus]
         (reports, repos)      (optional large          (jobs)
                                  artifacts)
```

---

## **3. Backend Changes (FastAPI)**

### **3.1 Git Manager Migration**

* Replace disk-based bare repo management with an **API abstraction layer**.
* Implement provider clients:

  * **GitHubClient** (Trees API, Contents API, commits API)
  * **AzureDevOpsClient** (Get Items, Get Tree APIs)
* Each client implements a shared interface:

  ```python
  class GitProvider:
      async def list_files(self, repo_id, ref: str) -> List[FileMeta]: ...
      async def get_file_content(self, repo_id, path, ref: str) -> bytes: ...
      async def list_commits(self, repo_id) -> List[CommitMeta]: ...
  ```
* **Authentication:**

  * Store provider tokens encrypted in DB.
  * Fetch and inject tokens into API calls.

> This change removes the dependency on local disk and allows the app to scale horizontally without shared file storage.

---

### **3.2 Report Storage Migration**

* Move reports from disk to **database table**:

  ```sql
  reports (
    id UUID,
    repo_id UUID,
    commit_hash TEXT,
    created_at TIMESTAMP,
    status ENUM('pending','complete','failed'),
    report_data JSONB
  )
  ```

* Large artifacts (if needed) can be stored in **Azure Blob Storage** and referenced by URL in the table.

* FastAPI endpoints update to read/write reports through DB rather than the filesystem.

---

### **3.3 Async Job Handling**

* Introduce background jobs via **Azure Service Bus**:

  * When a webhook or user action triggers analysis, push a job onto the queue.
  * Worker pods (FastAPI with Celery or RQ) consume jobs and write results back to DB.

---

## **4. Frontend Changes (React/Vite)**

* Deploy static build output (`dist/`) to **Azure Static Web Apps** or Blob Storage.
* Update API URLs to point to backend App Service domain.
* Add frontend support for:

  * Showing report status from DB.
  * Allowing users to manage repository credentials.

---

## **5. Azure Deployment Details**

### **5.1 Backend**

* **Option A (Simpler):** Azure App Service for Containers:

  * Build FastAPI Docker image (`Dockerfile`) and deploy with CI/CD.
  * Scale up/down easily.
* **Option B (More scalable):** AKS (Kubernetes):

  * Deploy backend + workers as pods.
  * Requires more DevOps overhead.

### **5.2 Database**

* Use **Azure Database for PostgreSQL - Flexible Server**.
* Configure VNet integration for private access from backend.

### **5.3 Secrets**

* **Azure Key Vault**:

  * Store encryption key (for token storage) and service credentials.
  * FastAPI loads secrets at runtime via Azure Managed Identity.

### **5.4 CI/CD**

* Use **GitHub Actions** or **Azure DevOps Pipelines** to:

  1. Build and deploy frontend → Static Web Apps.
  2. Build and deploy backend → App Service or AKS.
  3. Apply DB migrations (e.g., Alembic for SQLAlchemy).

---

## **6. Security**

* **Encryption at rest**:

  * Encrypted access tokens in DB using a master key from Azure Key Vault.
  * Reports stored as JSONB (already encrypted by Postgres at rest).
* **Scoped access tokens:**

  * Support GitHub Apps & Azure DevOps OAuth instead of user PATs for enterprise readiness.
* **Network isolation:**

  * Use private endpoints for DB and Key Vault.
* **HTTPS only:**

  * Frontend and backend endpoints behind TLS.

---

## **7. Multi-Tenancy**

* Partition data by `org_id` or `repo_id` in the database.
* Ensure strict access control in all queries (e.g., `WHERE org_id = current_user.org_id`).
* This allows single backend + database instance to serve multiple customers.

---

## **8. Next Steps**

1. **Implement the Git API abstraction layer** (GitHub + Azure DevOps to start).
2. **Add DB models & migrations for reports**.
3. **Refactor report write/read logic to use DB instead of disk**.
4. **Containerize FastAPI backend**.
5. **Provision Azure infrastructure** (App Service, Postgres, Key Vault, Service Bus, Static Web Apps).
6. **Setup CI/CD pipeline**.

---

👉 **Do you want me to write a full Terraform or Bicep deployment plan for Azure** (provisions App Service, Postgres, Key Vault, etc.) or just show how to containerize + deploy the backend and frontend manually?

Also, should I sketch **the DB schema with Alembic migration code** and the new **Git manager class structure**?
