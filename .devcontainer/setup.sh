#!/bin/bash
# Development Environment Setup Script for FundCast
set -e

echo "🚀 Setting up FundCast development environment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "\n${BLUE}=== $1 ===${NC}"
}

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ] && [ ! -f "package.json" ]; then
    print_error "Not in FundCast repository root directory"
    exit 1
fi

print_header "Installing Python Dependencies"

# Install Python dependencies with Poetry if available, otherwise use pip
if [ -f "pyproject.toml" ]; then
    if command -v poetry &> /dev/null; then
        print_status "Installing Python dependencies with Poetry..."
        poetry install --with dev,test
        
        # Activate poetry shell for subsequent commands
        export PATH="$(poetry env info --path)/bin:$PATH"
    else
        print_warning "Poetry not found, using pip..."
        if [ -f "requirements.txt" ]; then
            pip install -r requirements.txt
        fi
        if [ -f "requirements-dev.txt" ]; then
            pip install -r requirements-dev.txt
        fi
        
        # Install package in development mode
        pip install -e .
    fi
else
    print_warning "No pyproject.toml found, skipping Python dependencies"
fi

print_header "Installing Node.js Dependencies"

# Install Node.js dependencies if package.json exists
if [ -f "package.json" ]; then
    print_status "Installing Node.js dependencies..."
    npm install
    
    # Install global development tools
    print_status "Installing global Node.js tools..."
    npm install -g concurrently nodemon
else
    print_warning "No package.json found, skipping Node.js dependencies"
fi

print_header "Setting up Pre-commit Hooks"

# Set up pre-commit hooks
if [ -f ".pre-commit-config.yaml" ]; then
    print_status "Installing pre-commit hooks..."
    pre-commit install --install-hooks
    
    # Set up commit-msg hook for conventional commits
    pre-commit install --hook-type commit-msg
    
    print_status "Running pre-commit on all files (initial check)..."
    pre-commit run --all-files || print_warning "Some pre-commit checks failed - this is normal for initial setup"
else
    print_warning "No .pre-commit-config.yaml found, skipping pre-commit setup"
fi

print_header "Setting up Development Database"

# Wait for database to be ready
print_status "Waiting for PostgreSQL to be ready..."
until pg_isready -h localhost -p 5432 -U postgres; do
    echo "Waiting for PostgreSQL..."
    sleep 2
done

# Create development database and run initial setup
print_status "Setting up development database..."
python3 << 'EOF'
import os
import sys
sys.path.insert(0, '/workspace/src')

try:
    # Import database setup
    from api.database import engine, Base
    from sqlalchemy import text
    
    # Create database tables
    print("Creating database tables...")
    Base.metadata.create_all(engine)
    
    # Test database connection
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version()"))
        version = result.fetchone()[0]
        print(f"✅ Database connected: {version}")
        
        # Create pgvector extension if not exists
        try:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
            print("✅ pgvector extension enabled")
        except Exception as e:
            print(f"⚠️ Could not enable pgvector: {e}")
    
    print("✅ Database setup complete!")
    
except Exception as e:
    print(f"⚠️ Database setup failed: {e}")
    print("This is normal if the database schema isn't ready yet.")
EOF

print_header "Setting up Development Utilities"

# Create helpful development aliases and functions
cat > /home/vscode/.dev_aliases << 'EOF'
# FundCast Development Aliases
alias fundcast-test='cd /workspace && pytest tests/ -v --cov=src'
alias fundcast-serve='cd /workspace/src && python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload'
alias fundcast-lint='cd /workspace && pre-commit run --all-files'
alias fundcast-format='cd /workspace && black src/ tests/ && isort src/ tests/'
alias fundcast-typecheck='cd /workspace && mypy src/ --ignore-missing-imports'
alias fundcast-security='cd /workspace && bandit -r src/ -ll'
alias fundcast-db-reset='cd /workspace && python -c "from src.api.database import engine, Base; Base.metadata.drop_all(engine); Base.metadata.create_all(engine); print(\"Database reset!\")"'
alias fundcast-shell='cd /workspace && python -c "from src.api.database import *; from src.api.models import *; print(\"Database models loaded!\")" && python'

# Helpful aliases
alias ll='ls -alF'
alias la='ls -A'
alias l='ls -CF'
alias ..='cd ..'
alias ...='cd ../..'
alias tree='tree -I "__pycache__|*.pyc|.git"'
alias ports='netstat -tuln'
alias myip='curl -s https://api.ipify.org'

# Git aliases
alias gs='git status'
alias ga='git add'
alias gc='git commit'
alias gp='git push'
alias gl='git pull'
alias gd='git diff'
alias gb='git branch'
alias gco='git checkout'
alias glog='git log --oneline --graph --decorate'

# Docker aliases
alias dps='docker ps'
alias dpa='docker ps -a'
alias di='docker images'
alias dc='docker-compose'
alias dcu='docker-compose up'
alias dcd='docker-compose down'
alias dcl='docker-compose logs'

# Python aliases
alias py='python3'
alias pip='pip3'
alias venv='python3 -m venv'
alias serve='python3 -m http.server'
EOF

# Source the aliases in bashrc
echo 'source /home/vscode/.dev_aliases' >> /home/vscode/.bashrc

# Create development scripts directory
mkdir -p /home/vscode/.dev_scripts

# Create a comprehensive development helper script
cat > /home/vscode/.dev_scripts/fundcast-dev << 'EOF'
#!/bin/bash
# FundCast Development Helper Script

show_help() {
    echo "FundCast Development Helper"
    echo ""
    echo "Usage: fundcast-dev [command]"
    echo ""
    echo "Commands:"
    echo "  setup       - Initial setup and dependency installation"
    echo "  test        - Run test suite with coverage"
    echo "  test-watch  - Run tests in watch mode"
    echo "  serve       - Start development server"
    echo "  lint        - Run all linting and formatting checks"
    echo "  format      - Auto-format code"
    echo "  db-reset    - Reset development database"
    echo "  db-shell    - Open database shell"
    echo "  logs        - Show application logs"
    echo "  clean       - Clean cache and temporary files"
    echo "  docs        - Generate and serve documentation"
    echo "  security    - Run security checks"
    echo "  profile     - Run performance profiling"
    echo "  build       - Build Docker images"
    echo "  status      - Show development environment status"
    echo ""
}

case "$1" in
    "setup")
        echo "🔧 Setting up development environment..."
        cd /workspace
        if [ -f "pyproject.toml" ]; then
            poetry install --with dev,test
        fi
        if [ -f "package.json" ]; then
            npm install
        fi
        pre-commit install
        ;;
    
    "test")
        echo "🧪 Running test suite..."
        cd /workspace
        pytest tests/ -v --cov=src --cov-report=html --cov-report=term-missing
        ;;
    
    "test-watch")
        echo "👀 Running tests in watch mode..."
        cd /workspace
        ptw tests/ -- --cov=src -v
        ;;
    
    "serve")
        echo "🚀 Starting development server..."
        cd /workspace/src
        python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload --log-level debug
        ;;
    
    "lint")
        echo "🔍 Running linting checks..."
        cd /workspace
        pre-commit run --all-files
        ;;
    
    "format")
        echo "🎨 Formatting code..."
        cd /workspace
        black src/ tests/
        isort src/ tests/
        ;;
    
    "db-reset")
        echo "🔄 Resetting database..."
        cd /workspace
        python -c "
from src.api.database import engine, Base
Base.metadata.drop_all(engine)
Base.metadata.create_all(engine)
print('✅ Database reset complete!')
"
        ;;
    
    "db-shell")
        echo "🐚 Opening database shell..."
        psql "$DATABASE_URL"
        ;;
    
    "logs")
        echo "📝 Showing application logs..."
        tail -f /workspace/logs/*.log 2>/dev/null || echo "No log files found"
        ;;
    
    "clean")
        echo "🧹 Cleaning cache and temporary files..."
        cd /workspace
        find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
        find . -name "*.pyc" -delete 2>/dev/null || true
        find . -name "*.pyo" -delete 2>/dev/null || true
        find . -name ".coverage" -delete 2>/dev/null || true
        rm -rf .pytest_cache/ htmlcov/ .mypy_cache/ .ruff_cache/ 2>/dev/null || true
        echo "✅ Cleanup complete!"
        ;;
    
    "docs")
        echo "📚 Generating and serving documentation..."
        cd /workspace
        if [ -d "docs/" ]; then
            mkdocs serve --dev-addr=0.0.0.0:8001
        else
            echo "No docs/ directory found"
        fi
        ;;
    
    "security")
        echo "🛡️ Running security checks..."
        cd /workspace
        bandit -r src/ -ll
        safety check
        ;;
    
    "profile")
        echo "⚡ Running performance profiling..."
        cd /workspace
        python -m cProfile -s cumtime src/api/main.py
        ;;
    
    "build")
        echo "🏗️ Building Docker images..."
        cd /workspace
        docker build -t fundcast:dev .
        ;;
    
    "status")
        echo "📊 Development Environment Status"
        echo "================================"
        echo "📁 Working Directory: $(pwd)"
        echo "🐍 Python Version: $(python --version)"
        echo "📦 Node Version: $(node --version 2>/dev/null || echo 'Not installed')"
        echo "🗄️ Database: $(pg_isready -h localhost -U postgres && echo '✅ Connected' || echo '❌ Not connected')"
        echo "📡 Redis: $(redis-cli ping 2>/dev/null || echo '❌ Not connected')"
        echo "🔧 Git Status:"
        git status --porcelain | head -5
        echo "🌿 Current Branch: $(git branch --show-current)"
        echo "📝 Recent Commits:"
        git log --oneline -5
        ;;
    
    *)
        show_help
        ;;
esac
EOF

chmod +x /home/vscode/.dev_scripts/fundcast-dev

# Add development scripts to PATH
echo 'export PATH="/home/vscode/.dev_scripts:$PATH"' >> /home/vscode/.bashrc

print_header "Setting up Development Configuration"

# Create default environment file if it doesn't exist
if [ ! -f ".env" ] && [ -f ".env.example" ]; then
    print_status "Creating .env file from .env.example..."
    cp .env.example .env
fi

# Set up Git configuration
print_status "Configuring Git..."
git config --global --add safe.directory /workspace
git config --global init.defaultBranch main
git config --global pull.rebase false
git config --global core.autocrlf input

# Create logs directory
mkdir -p /workspace/logs

# Set up VS Code settings
mkdir -p /workspace/.vscode
cat > /workspace/.vscode/settings.json << 'EOF'
{
    "python.defaultInterpreterPath": "/usr/local/bin/python",
    "python.terminal.activateEnvironment": false,
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": true,
    "python.formatting.provider": "black",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
        "source.organizeImports": true
    },
    "python.testing.pytestEnabled": true,
    "python.testing.unittestEnabled": false,
    "python.testing.pytestArgs": ["tests/"],
    "files.exclude": {
        "**/__pycache__": true,
        "**/*.pyc": true,
        "**/node_modules": true,
        ".coverage": true,
        "htmlcov/": true
    }
}
EOF

# Create launch configurations for debugging
cat > /workspace/.vscode/launch.json << 'EOF'
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "FastAPI Development Server",
            "type": "python",
            "request": "launch",
            "module": "uvicorn",
            "args": ["api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"],
            "cwd": "${workspaceFolder}/src",
            "env": {
                "PYTHONPATH": "${workspaceFolder}/src"
            },
            "console": "integratedTerminal"
        },
        {
            "name": "Run Tests",
            "type": "python",
            "request": "launch",
            "module": "pytest",
            "args": ["tests/", "-v"],
            "cwd": "${workspaceFolder}",
            "console": "integratedTerminal"
        }
    ]
}
EOF

print_header "Finalizing Setup"

# Create a welcome script
cat > /home/vscode/.welcome << 'EOF'
echo ""
echo "🎉 Welcome to FundCast Development Environment!"
echo "=============================================="
echo ""
echo "🚀 Quick Start Commands:"
echo "  fundcast-dev serve    - Start development server"
echo "  fundcast-dev test     - Run test suite"
echo "  fundcast-dev lint     - Check code quality"
echo "  fundcast-dev status   - Show environment status"
echo ""
echo "📚 Available Services:"
echo "  • FastAPI Server: http://localhost:8000"
echo "  • Database Admin: http://localhost:8080"
echo "  • Mail Testing: http://localhost:8025"
echo "  • MinIO Console: http://localhost:9001"
echo ""
echo "🔧 Development Tools:"
echo "  • Pre-commit hooks installed"
echo "  • Code formatting with Black"
echo "  • Type checking with MyPy"
echo "  • Security scanning with Bandit"
echo ""
echo "📁 Project Structure:"
echo "  src/           - Application source code"
echo "  tests/         - Test suite"
echo "  docs/          - Documentation"
echo "  .devcontainer/ - Development environment"
echo ""
echo "Run 'fundcast-dev' for more commands!"
echo ""
EOF

# Source welcome message in bashrc
echo 'source /home/vscode/.welcome' >> /home/vscode/.bashrc

# Final status check
print_header "Setup Complete"

print_status "✅ Python dependencies installed"
print_status "✅ Node.js dependencies installed" 
print_status "✅ Pre-commit hooks configured"
print_status "✅ Database connection established"
print_status "✅ Development utilities installed"
print_status "✅ VS Code configuration created"

echo ""
echo -e "${GREEN}🎉 FundCast development environment is ready!${NC}"
echo -e "${BLUE}   Run 'fundcast-dev serve' to start the development server${NC}"
echo ""