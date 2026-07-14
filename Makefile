.PHONY: dev build test lint clean docker-up docker-down deploy

# ── Development ──
dev:
	@echo "Starting development servers..."
	@cd backend && uvicorn api.main:app --reload --port 8000 &
	@cd frontend && npm run dev &
	@wait

dev-backend:
	@cd backend && uvicorn api.main:app --reload --port 8000

dev-frontend:
	@cd frontend && npm run dev

dev-celery:
	@cd backend && celery -A celery_app worker --loglevel=info --concurrency=2

# ── Build ──
build:
	@cd frontend && npm install && npm run build
	@docker compose build

# ── Testing ──
test:
	@cd backend && pytest tests/ -v --asyncio-mode=auto

test-coverage:
	@cd backend && pytest tests/ --cov=. --cov-report=term --cov-report=html --asyncio-mode=auto

test-e2e:
	@python scripts/validate_demo.py

# ── Linting ──
lint:
	@cd backend && ruff check .
	@cd frontend && npx tsc --noEmit

format:
	@cd backend && ruff format .

# ── Docker ──
docker-up:
	@docker compose up -d

docker-down:
	@docker compose down

docker-logs:
	@docker compose logs -f

# ── Database ──
db-init:
	@cd backend && python -c "from core.state import init_db; init_db(); print('Database initialized')"

db-migrate:
	@cd backend && alembic upgrade head

# ── Production ──
deploy:
	@kubectl apply -f k8s/

deploy-status:
	@kubectl -n taskpilot get all

# ── Cleanup ──
clean:
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete
	@find . -type f -name ".coverage" -delete
	@find . -type d -name htmlcov -exec rm -rf {} + 2>/dev/null || true
	@rm -rf frontend/dist
	@echo "Cleaned up"

.PHONY: help
help:
	@echo "TaskPilot AI Development Commands"
	@echo "================================="
	@echo "make dev            Start all dev servers"
	@echo "make dev-backend    Start backend only"
	@echo "make dev-frontend   Start frontend only"
	@echo "make dev-celery     Start Celery worker"
	@echo "make test           Run all tests"
	@echo "make test-coverage  Run tests with coverage"
	@echo "make test-e2e       Run demo validation"
	@echo "make lint           Run linters"
	@echo "make format         Format code"
	@echo "make build          Build Docker images"
	@echo "make docker-up      Start Docker Compose"
	@echo "make docker-down    Stop Docker Compose"
	@echo "make db-init        Initialize database"
	@echo "make deploy         Deploy to Kubernetes"
	@echo "make clean          Clean build artifacts"
