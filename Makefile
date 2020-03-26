# Configuration
APP_ROOT := $(abspath $(lastword $(MAKEFILE_LIST))/..)
APP_NAME := flyingpigeon

# end of configuration

.DEFAULT_GOAL := help

.PHONY: all
all: help

.PHONY: help
help:
	@echo "Please use 'make <target>' where <target> is one of:"
	@echo "  help              to print this help message. (Default)"
	@echo "  install           to install app by running 'pip install -e .'"
	@echo "  develop           to install with additional development requirements."
	@echo "  start             to start $(APP_NAME) service as daemon (background process)."
	@echo "  stop              to stop $(APP_NAME) service."
	@echo "  restart           to restart $(APP_NAME) service."
	@echo "  status            to show status of $(APP_NAME) service."
	@echo "  clean             to remove all files generated by build and tests."
	@echo "\nTesting targets:"
	@echo "  test              to run tests (but skip long running tests)."
	@echo "  test-all          to run all tests (including long running tests)."
	@echo "  lint              to run code style checks with flake8."
	@echo "\nSphinx targets:"
	@echo "  docs              to generate HTML documentation with Sphinx."
	@echo "\nDeployment targets:"
	@echo "  dist              to build source and wheel package."

## Build targets

.PHONY: install
install:
	@echo "Installing application ..."
	@-bash -c 'pip install -e .'
	@echo "\nStart service with \`make start'"

.PHONY: develop
develop:
	@echo "Installing development requirements for tests and docs ..."
	@-bash -c 'pip install -e ".[dev]"'

.PHONY: start
start:
	@echo "Starting application ..."
	@-bash -c "$(APP_NAME) start -d"

.PHONY: stop
stop:
	@echo "Stopping application ..."
	@-bash -c "$(APP_NAME) stop"

.PHONY: restart
restart: stop start
	@echo "Restarting application ..."

.PHONY: status
status:
	@echo "Show status ..."
	@-bash -c "$(APP_NAME) status"

.PHONY: clean
clean: clean-build clean-pyc clean-test ## remove all build, test, coverage and Python artifacts

.PHONY: clean-build
clean-build:
	@echo "Remove build artifacts ..."
	@-rm -fr build/
	@-rm -fr dist/
	@-rm -fr .eggs/
	@-find . -name '*.egg-info' -exec rm -fr {} +
	@-find . -name '*.egg' -exec rm -f {} +
	@-find . -name '*.log' -exec rm -fr {} +
	@-find . -name '*.sqlite' -exec rm -fr {} +

.PHONY: clean-pyc
clean-pyc:
	@echo "Remove Python file artifacts ..."
	@-find . -name '*.pyc' -exec rm -f {} +
	@-find . -name '*.pyo' -exec rm -f {} +
	@-find . -name '*~' -exec rm -f {} +
	@-find . -name '__pycache__' -exec rm -fr {} +

.PHONY: clean-test
clean-test:
	@echo "Remove test artifacts ..."
	@-rm -fr .pytest_cache

.PHONY: clean-dist
clean-dist: clean
	@echo "Run 'git clean' ..."
	@git diff --quiet HEAD || echo "There are uncommited changes! Not doing 'git clean' ..."
	@-git clean -dfx

## Test targets

.PHONY: test
test:
	@echo "Running tests (skip slow and online tests) ..."
	@bash -c 'pytest -v -m "not slow and not online" tests/'

.PHONY: test-all
test-all:
	@echo "Running all tests (including slow and online tests) ..."
	@bash -c 'pytest -v tests/'

.PHONY: test-nb
test-nb:
	@echo "Running notebook-based tests"
	@bash -c "source $(ANACONDA_HOME)/bin/activate $(CONDA_ENV);env FLYINGPIGEON_WPS_URL=$(FLYINGPIGEON_WPS_URL) pytest --nbval $(CURDIR)/docs/source/notebooks/ --sanitize-with $(CURDIR)/docs/source/output_sanitize.cfg --ignore $(CURDIR)/docs/source/notebooks/.ipynb_checkpoints"

.PHONY: lint
lint:
	@echo "Running flake8 code style checks ..."
	@bash -c 'flake8'

## Sphinx targets

.PHONY: docs
docs:
	@echo "Generating docs with Sphinx ..."
	@-bash -c '$(MAKE) -C $@ clean html'
	@echo "open your browser: open file://$(APP_ROOT)/docs/build/html/index.html"

## Deployment targets

.PHONY: dist
dist: clean
	@echo "Builds source and wheel package ..."
	@-python setup.py sdist
	@-python setup.py bdist_wheel
	ls -l dist
