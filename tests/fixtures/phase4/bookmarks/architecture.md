# TaskFlow architecture

A Python FastAPI service (taskflow-api) owns tasks, comments and reports and stores data in PostgreSQL. Redis caches board reads and search results. A worker (notify-worker) sends emails and the daily digest. A React web app (taskflow-web) is the only public entry point. Expected load: 200 teams, 50 requests/second peak.

## Components
- ARCH-001 taskflow-api: service, runtime python3.12, repo acme/taskflow-api
- ARCH-002 taskflow-web: frontend, runtime node22, repo acme/taskflow-web
- ARCH-003 taskflow-db: database, runtime postgres16, repo -
- ARCH-004 taskflow-cache: cache, runtime redis7, repo -
- ARCH-005 notify-worker: worker, runtime python3.12, repo acme/taskflow-api