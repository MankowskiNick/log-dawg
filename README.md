# Log Dawg 🐕

**LLM-powered log diagnosis agent with git context and web dashboard**

Log Dawg is an intelligent log analysis tool that uses Large Language Models (LLMs) to diagnose error logs with the context of your git repository. It features a React TypeScript frontend dashboard for viewing diagnostic reports and a FastAPI backend for processing. The application automatically pulls the latest code changes and provides comprehensive analysis with actionable recommendations.

---

## Table of Contents

- [Architecture](#architecture)
- [Monorepo Development Setup](#monorepo-development-setup)
  - [Prerequisites](#prerequisites)
  - [Quick Start Commands](#quick-start-commands)
  - [Services](#services)
- [Project Structure](#project-structure)
- [Features](#features)
- [Configuration](#configuration)
  - [Backend Environment Variables](#backend-environment-variables-backendconfigenvexample)
  - [Frontend Environment Variables](#frontend-environment-variables-frontendenvexample)
  - [Configuration File](#configuration-file-backendconfigconfigyaml)
- [Usage](#usage)
  - [Diagnose Error Logs](#diagnose-error-logs)
- [API Endpoints](#api-endpoints)
- [Generated Reports](#generated-reports)
- [Supported Log Formats](#supported-log-formats)
- [Development](#development)
  - [Adding New LLM Providers](#adding-new-llm-providers)
- [Alternative: Run Without Docker (Advanced)](#alternative-run-without-docker-advanced)
- [Troubleshooting](#troubleshooting)
  - [Common Issues](#common-issues)
  - [Logging](#logging)
- [Contributing](#contributing)
- [License](#license)
- [Support](#support)

---

## Architecture

This is a monorepo containing:
- **Backend**: Python FastAPI service for log analysis and diagnosis
- **Frontend**: React TypeScript dashboard for viewing reports and system monitoring
- **Independent Configuration**: Separate environment configurations for each service

---

## Monorepo Development Setup

### Prerequisites
- Node.js 18+ (for frontend)
- Python 3.9+ (for backend)
- Git

### Quick Start Commands

```bash
# Clone repository
git clone https://github.com/MankowskiNick/log-dawg
cd log-dawg

# Backend setup
cd backend
pip install -r requirements.txt
cp config/.env.example .env  # Edit with your API keys
cd ..

# Frontend setup
cd frontend
npm install
cp .env.example .env  # Configure frontend environment
cd ..

# Run both services (from root)
# Backend (Terminal 1)
cd backend && python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Frontend (Terminal 2)
cd frontend && npm run dev
```

### Services
- **Frontend**: http://localhost:5173 (React TypeScript dashboard)
- **Backend API**: http://localhost:8000 (FastAPI service)
- **API Docs**: http://localhost:8000/docs

---

## Project Structure

```
log-dawg/
├── backend/           # Python FastAPI service
│   ├── src/          # Backend source code
│   ├── requirements.txt
│   ├── config/       # Configuration files and .env.example
│   ├── .env          # Backend environment variables
│   ├── Dockerfile
│   ├── reports/      # Generated diagnostic reports
│   ├── logs/         # Application logs
│   └── repo/         # Git repository clone
├── frontend/         # React TypeScript app
│   ├── src/          # Frontend source code
│   ├── package.json
│   ├── .env          # Frontend environment variables
│   └── vite.config.ts
```

---

## Features

- 🤖 **LLM-Powered Analysis**: Leverages LLMs (OpenAI, Anthropic, Langfuse) for in-depth root cause analysis.
- 🔄 **Git Integration**: Enriches diagnoses with context from recent commits and code changes.
- 🧠 **Context Discovery Engine**: Intelligently finds and includes relevant source code in the analysis.
- 📊 **Flexible Log Parsing**: Supports JSON, plain text, and common AWS log formats.
- **Markdown Reports**: Generates detailed and readable diagnosis reports.
- 🐳 **Docker Ready**: Simplified setup and deployment with Docker Compose.
- 🚀 **Async Processing**: Utilizes a background worker queue to handle concurrent diagnosis requests without blocking.
- 🧩 **Advanced Logging**: Provides per-diagnosis logs for complete traceability.

---

## Configuration

### Backend Environment Variables (`backend/config/.env.example`)

```bash
# LLM API Configuration
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Git Authentication (if using HTTPS with token)
GIT_TOKEN=your_git_token_here
GIT_USERNAME=your_git_username_here

# Server Configuration
LOG_LEVEL=INFO
DEBUG=False

# Optional: Custom LLM Provider Configuration
LANGFUSE_PUBLIC_KEY=your_langfuse_public_key
LANGFUSE_SECRET_KEY=your_langfuse_secret_key
LANGFUSE_HOST=https://cloud.langfuse.com
```

### Frontend Environment Variables (`frontend/.env.example`)

```bash
# API Configuration
VITE_API_BASE_URL=http://localhost:8000
VITE_API_TIMEOUT=10000

# App Configuration
VITE_APP_TITLE=Log Dawg Dashboard
VITE_APP_VERSION=1.0.0

# Development Configuration
VITE_DEBUG=true
VITE_LOG_LEVEL=INFO
```

### Configuration File (`backend/config/config.yaml`)

```yaml
repository:
  url: "https://github.com/MankowskiNick/malloc-craft.git"
  branch: "main"
  local_path: "./repo"
  auth_method: "token"  # Options: ssh, https, token

llm:
  provider: "anthropic"  # Options: openai, anthropic, langfuse
  model: "claude-sonnet-4-20250514"
  max_tokens: 2000
  temperature: 0.1
  timeout: 150
  retry_count: 5
  retry_backoff_base: 2
  retry_backoff_max: 30

reports:
  output_dir: "./reports"
  max_reports: 100
  filename_format: "diagnosis_{timestamp}_{hash}.md"

server:
  host: "0.0.0.0"
  port: 8000
  reload: false
  http_workers: 1
  diagnosis_worker_count: 4

git_analysis:
  max_commits_to_analyze: 5
  file_extensions_to_include: [".py", ".js", ".ts", ".java", ".go", ".rs", ".cpp", ".c"]

context_discovery:
  enabled: true
  max_iterations: 5
  confidence_threshold: 0.95
  file_size_limit_kb: 100
  max_total_context_size_kb: 500
  file_extensions_priority: [".py", ".js", ".ts", ".java", ".go", ".rs", ".cpp", ".c"]
  exclude_patterns: ["*.log", "*.tmp", "node_modules/*", "__pycache__/*", ".git/*"]
  min_confidence_improvement: 0.1

logging:
  level: "DEBUG"
  per_diagnosis_logging: true
  log_directory: "./logs"
  retention_days: 30
  max_log_size_mb: 100
  structured_format: true
  console_logging: true
  file_logging: true
  llm_interaction_logging:
    log_requests: true
    log_responses: true
    truncate_large_responses: false
    max_prompt_log_length: 50000
    max_response_log_length: 50000
```

---

## Usage

### Diagnose Error Logs

Send a POST request to `/api/v1/logs/diagnose`:

```bash
curl -X POST "http://localhost:8000/api/v1/logs/diagnose" \
  -H "Content-Type: application/json" \
  -d '{
    "log_data": {
      "content": "ERROR: Database connection failed - Connection timeout after 30 seconds",
      "source": "application",
      "timestamp": "2024-01-01T12:00:00Z"
    },
    "force_git_pull": true,
    "include_git_context": true
  }'
```

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Root endpoint with basic info |
| `/api/v1/logs/diagnose` | POST | Diagnose error logs |
| `/api/v1/logs/list` | GET | List diagnosis logs |
| `/api/v1/logs/{diagnosis_id}` | GET | Get diagnosis log by ID |
| `/api/v1/logs/cleanup` | POST | Clean up old diagnosis logs |
| `/api/v1/logs/stats` | GET | Get diagnosis logging statistics |
| `/api/v1/health` | GET | Health check |
| `/api/v1/config/validate` | GET | Validate configuration |
| `/api/v1/git/status` | GET | Get git repository status |
| `/api/v1/git/pull` | POST | Manually trigger git pull |
| `/api/v1/reports` | GET | List recent reports |
| `/api/v1/reports/{filename}` | GET | Get specific report content |
| `/api/v1/stats` | GET | Get system statistics |

---

## Generated Reports

Log Dawg generates comprehensive markdown root cause analysis reports for each error log submitted to `/api/v1/logs/diagnose`. These reports summarize the diagnosis, root cause, recommendations, and repository context.

---

## Supported Log Formats

- **JSON Logs**: CloudWatch, structured application logs
- **Plain Text**: Standard application logs, system logs
- **AWS Formats**: ALB logs, CloudWatch logs, Lambda logs

---

## Development


### Adding New LLM Providers

1. Extend the `LLMProvider` abstract class in `src/core/llm_engine/providers/base.py`
2. Implement the `generate_diagnosis` method
3. Update the provider factory in `src/core/llm_engine/engine.py`

---

## Alternative: Run Without Docker (Advanced)

Direct Python execution is supported for advanced users and development only.

```bash
# Install dependencies
pip install -r requirements.txt

# Run directly
python -m src.main

# Or with uvicorn
uvicorn src.main:app --host 0.0.0.0 --port 8000
```

> Docker is the recommended and supported way to run Log Dawg.

---

## Troubleshooting

### Common Issues

**Configuration validation failed**
- Check that your OpenAI or Anthropic API key is set
- Verify repository URL and authentication method
- Ensure the reports directory is writable

**Git pull failed**
- Verify repository URL and credentials
- Check SSH key configuration for SSH auth
- Ensure git token has proper permissions for HTTPS auth

**LLM provider errors**
- Verify API key is valid and has sufficient credits
- Check network connectivity to LLM provider
- Review rate limiting settings

### Logging

Log Dawg writes operational logs (for running this app) to both stdout and `log-dawg.log`. These logs help monitor and debug the application's behavior, not the logs being analyzed.

- **Operational Logs**: Track API requests, diagnosis processing, and system events.
- **Log Stats & Cleanup**: Use `/api/v1/logs/stats` to get statistics about the app's own logs and `/api/v1/logs/cleanup` to remove old operational logs.
- **Configuration**: Control log level and retention via `.env` and `config.yaml` (`LOG_LEVEL`, `reports.max_reports`, etc.).

Set `LOG_LEVEL=DEBUG` for detailed logging.

---

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

---

## License

This project is licensed under the MIT License (c) 2025 Nicholas Mankowski.  
See the [LICENSE](LICENSE) file for details.

---

## Support

For issues and questions:
- Create an issue on GitHub
- Check the documentation
- Review the logs for error details
