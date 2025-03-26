# FundTracker Makefile
# This file provides commands for development, testing, and deployment

# Variables
PYTHON = python
PIP = pip
NPM = npm
VITE = npx vite
FLASK = flask
BACKEND_DIR = backend
FRONTEND_DIR = frontend
DB_NAME = finance.db
EXPORT_DIR = db_exports
BACKUP_DIR = db_backups
REQUIREMENTS = $(BACKEND_DIR)/requirements.txt
DATE := $(shell date +%Y%m%d_%H%M%S)

# Default target
.PHONY: help
help:
	@echo "FundTracker Makefile"
	@echo "===================="
	@echo "Available commands:"
	@echo ""
	@echo "Development:"
	@echo "  make setup         - Install all dependencies"
	@echo "  make start         - Start both frontend and backend (in separate terminals)"
	@echo "  make start-backend - Start the backend server"
	@echo "  make start-frontend - Start the frontend development server"
	@echo "  make init-db       - Initialize the database"
	@echo ""
	@echo "Database Management:"
	@echo "  make export-db     - Export database to CSV files (renamed from backup-db)"
	@echo "  make import-db     - Import database from latest CSV export (renamed from restore-db)"
	@echo "  make backup-db     - Create a full database backup file"
	@echo "  make restore-db    - Restore database from a backup file"
	@echo "  make list-backups  - List all available database backups"
	@echo ""
	@echo "Deployment:"
	@echo "  make build         - Build the frontend for production"
	@echo "  make deploy        - Deploy the application (builds frontend and copies to backend)"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean         - Remove build artifacts and temporary files"
	@echo "  make update-deps   - Update dependencies"

# Setup commands
.PHONY: setup setup-backend setup-frontend
setup: setup-backend setup-frontend

setup-backend:
	@echo "Installing backend dependencies..."
	cd $(BACKEND_DIR) && $(PIP) install -r requirements.txt

setup-frontend:
	@echo "Installing frontend dependencies..."
	cd $(FRONTEND_DIR) && $(NPM) install

# Start commands
.PHONY: start start-backend start-frontend start-app
start:
	@echo "Please run 'make start-backend' and 'make start-frontend' in separate terminals"
	@echo "Or use: 'make start-app' to start both processes"

start-app:
	@echo "启动前端和后端服务..."
	@cd $(BACKEND_DIR) && $(PYTHON) app.py > backend.log 2>&1 & \
	cd $(FRONTEND_DIR) && $(NPM) run dev > frontend.log 2>&1 & \
	wait

start-backend:
	@echo "Starting backend server on port 5001..."
	cd $(BACKEND_DIR) && $(PYTHON) app.py

start-frontend:
	@echo "Starting frontend development server on port 3000..."
	cd $(FRONTEND_DIR) && $(NPM) run dev

# Database commands
.PHONY: init-db export-db import-db backup-db restore-db list-backups
init-db:
	@echo "Initializing database..."
	cd $(BACKEND_DIR) && $(PYTHON) init_db.py

# Renamed from backup-db to export-db
export-db:
	@echo "Exporting database to CSV files..."
	cd $(BACKEND_DIR) && $(PYTHON) scripts/export_db_to_csv.py

# Renamed from restore-db to import-db
import-db:
	@echo "Importing database from latest CSV export..."
	cd $(BACKEND_DIR) && $(PYTHON) scripts/import_csv_to_db.py

# New backup-db command for full database backup
backup-db:
	@echo "Creating full database backup..."
	@mkdir -p $(BACKEND_DIR)/$(BACKUP_DIR)
	cd $(BACKEND_DIR) && sqlite3 $(DB_NAME) ".backup '$(BACKUP_DIR)/$(DB_NAME).$(DATE).bak'"
	@echo "Database backed up to $(BACKEND_DIR)/$(BACKUP_DIR)/$(DB_NAME).$(DATE).bak"

# New restore-db command for restoring from backup
restore-db:
	@echo "Available backups:"
	@ls -lt $(BACKEND_DIR)/$(BACKUP_DIR) | grep -v "^total" | head -5
	@echo "Enter backup filename to restore (from list above):"
	@read backup_file && \
	echo "Restoring from $$backup_file..." && \
	cd $(BACKEND_DIR) && \
	sqlite3 $(DB_NAME) ".restore '$(BACKUP_DIR)/$$backup_file'"
	@echo "Database restored successfully."

# List available backups
list-backups:
	@echo "Available database backups:"
	@ls -lt $(BACKEND_DIR)/$(BACKUP_DIR) | grep -v "^total"

# Build and deployment commands
.PHONY: build deploy
build:
	@echo "Building frontend for production..."
	cd $(FRONTEND_DIR) && $(NPM) run build

deploy: build
	@echo "Deploying application..."
	@mkdir -p $(BACKEND_DIR)/static
	@rm -rf $(BACKEND_DIR)/static/*
	@cp -r $(FRONTEND_DIR)/dist/* $(BACKEND_DIR)/static/
	@echo "Deployment complete. The application is ready to serve from Flask."

# Maintenance commands
.PHONY: clean update-deps
clean:
	@echo "Cleaning up build artifacts and temporary files..."
	@rm -rf $(FRONTEND_DIR)/dist
	@rm -rf $(FRONTEND_DIR)/node_modules/.vite
	@find . -type d -name __pycache__ -exec rm -rf {} +
	@find . -type f -name "*.pyc" -delete

update-deps:
	@echo "Updating backend dependencies..."
	cd $(BACKEND_DIR) && $(PIP) install --upgrade -r requirements.txt
	@echo "Updating frontend dependencies..."
	cd $(FRONTEND_DIR) && $(NPM) update

# Development utilities
.PHONY: lint test
lint:
	@echo "Linting Python code..."
	cd $(BACKEND_DIR) && $(PYTHON) -m flake8

test:
	@echo "Running tests..."
	cd $(BACKEND_DIR) && $(PYTHON) -m pytest

# Production utilities
.PHONY: serve-prod
serve-prod: deploy
	@echo "Starting production server..."
	cd $(BACKEND_DIR) && FLASK_ENV=production $(PYTHON) app.py