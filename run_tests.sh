#!/bin/bash

# Run tests for Secret Toulouse Spots project

echo "==================================="
echo "Running Secret Toulouse Spots Tests"
echo "==================================="

# Install test dependencies if needed
if ! python3 -c "import pytest" 2>/dev/null; then
    echo "Installing test dependencies..."
    pip install -r requirements-test.txt
fi

# Run different test suites
echo -e "\n📋 Running unit tests..."
python3 -m pytest tests/ -m unit -v

echo -e "\n🔧 Running integration tests..."
python3 -m pytest tests/ -m integration -v

echo -e "\n⚡ Running async tests..."
python3 -m pytest tests/ -m async -v

echo -e "\n📊 Running all tests with coverage..."
python3 -m pytest tests/ --cov=scrapers --cov-report=term-missing

echo -e "\n✅ Test run complete!"

# Generate HTML coverage report
echo -e "\n📈 Generating coverage report..."
python3 -m pytest tests/ --cov=scrapers --cov-report=html --quiet

echo "Coverage report available at: htmlcov/index.html"