SHELL := /bin/bash

PYTHON ?= python3
VENV := .venv
VENV_PYTHON := $(VENV)/bin/python
VENV_RUFF := $(VENV)/bin/ruff
WEB_DIR := apps/web
WEB_READY := $(WEB_DIR)/node_modules/.package-lock.json
CHAPTER ?=
VARIANT ?= start
PYTHON_LAB_SOLUTIONS := $(wildcard labs/chapter-*/solution/exercise.py)
GO_LAB_SOLUTIONS := $(wildcard labs/chapter-*/solution/main.go)
TS_LAB_SOLUTIONS := $(wildcard labs/chapter-*/solution/exercise.ts)

JSONSCHEMA_VERSION := 4.25.1

.PHONY: help bootstrap web-bootstrap check-tools check-python check-go check-node \
	test agent-test go-test go-race web-test \
	lint contract-test fixture-test fixture-baseline fake-e2e eval-unit eval-fixtures \
	chapter-list chapter-prepare chapter-check chapter-lab-test \
	chapter-python-solutions chapter-go-solutions chapter-web-solutions \
	require-chapter clean

help:
	@echo "RepoFix deterministic commands:"
	@echo "  make bootstrap         install pinned Python and Web dependencies"
	@echo "  make test              run Agent, Go, Web, Eval, and contract tests"
	@echo "  make lint              run Python and Go formatting checks"
	@echo "  make fixture-baseline  assert the authored fixture has exactly one known failure"
	@echo "  make fake-e2e          run the zero-cloud Go control-plane E2E"
	@echo "  make eval-unit         run the zero-cloud independent-oracle tests"
	@echo "  make chapter-list      list the 19 chapter labs"
	@echo "  make chapter-prepare CHAPTER=chapter-05"
	@echo "  make chapter-check   CHAPTER=chapter-05"
	@echo "  make chapter-lab-test  validate lab structure and safe paths"
	@echo "Cloud targets are added only when their implementation checkpoint is published."

require-chapter:
	@if [[ -z "$(CHAPTER)" ]]; then \
		echo "ERROR: set CHAPTER=chapter-NN"; \
		exit 2; \
	fi

chapter-list:
	@$(PYTHON) scripts/chapter_lab.py list

chapter-prepare: require-chapter
	@$(PYTHON) scripts/chapter_lab.py prepare "$(CHAPTER)" --variant "$(VARIANT)"

chapter-check: require-chapter
	@$(PYTHON) scripts/chapter_lab.py check "$(CHAPTER)"

chapter-lab-test:
	@$(PYTHON) -m unittest discover -s scripts/tests -p 'test_*.py'

chapter-python-solutions: check-python
	@for file in $(PYTHON_LAB_SOLUTIONS); do $(PYTHON) "$$file"; done

chapter-go-solutions: check-go
	@for file in $(GO_LAB_SOLUTIONS); do \
		test -z "$$(gofmt -l "$$file")" || { echo "$$file needs gofmt"; exit 1; }; \
		go run "$$file"; \
	done

chapter-web-solutions: check-node $(WEB_READY)
	@$(WEB_DIR)/node_modules/.bin/tsc --noEmit --strict --target ES2024 \
		--moduleDetection force $(TS_LAB_SOLUTIONS)
	@for file in $(TS_LAB_SOLUTIONS); do node "$$file"; done

bootstrap: check-tools $(VENV)/.ready $(WEB_READY)
	@echo "RepoFix bootstrap complete. Run: make test"

web-bootstrap: check-node $(WEB_READY)

check-tools:
	@$(MAKE) --no-print-directory check-python check-go check-node
	@echo "Toolchain check passed: Python 3.14, Go 1.26, Node.js 24 LTS"

check-python:
	@$(PYTHON) -c 'import sys; assert sys.version_info[:2] == (3, 14), "RepoFix requires Python 3.14.x"'

check-go:
	@go version | grep -Eq 'go1\.26(\.| )' || { echo "RepoFix requires Go 1.26.x"; exit 1; }

check-node:
	@node -e 'const major = Number(process.versions.node.split(".")[0]); if (major !== 24) { throw new Error("RepoFix requires Node.js 24.x LTS") }'

$(VENV)/.ready: Makefile services/agent/pyproject.toml
	@$(PYTHON) -m venv $(VENV)
	@$(VENV_PYTHON) -m pip install --disable-pip-version-check --quiet \
		jsonschema==$(JSONSCHEMA_VERSION) \
		-e 'services/agent[dev,service]'
	@touch $(VENV)/.ready

$(WEB_READY): $(WEB_DIR)/package.json $(WEB_DIR)/package-lock.json
	@cd $(WEB_DIR) && npm ci

test: agent-test go-test web-test eval-unit contract-test chapter-lab-test \
	chapter-python-solutions chapter-go-solutions chapter-web-solutions

agent-test: check-python $(VENV)/.ready
	@cd services/agent && ../../$(VENV_PYTHON) -m pytest
	@cd services/agent && ../../$(VENV_PYTHON) -m repofix_agent

go-test: check-go
	@go test ./services/control/...

go-race: check-go
	@go test -race ./services/control/...

web-test: check-node $(WEB_READY)
	@cd $(WEB_DIR) && npm run typecheck
	@cd $(WEB_DIR) && npm test
	@cd $(WEB_DIR) && npm run build

eval-unit: check-python $(VENV)/.ready
	@$(VENV_PYTHON) -m pytest -q evals/tests

eval-fixtures: eval-unit
	@echo "PASS: eval metadata, forbidden paths, and hidden oracle are verified"

fake-e2e: check-go
	@go test ./services/control -run '^TestFakeControlPlaneE2E$$'

lint: check-python check-go $(VENV)/.ready
	@paths=(); \
	for path in fixtures services evals scripts labs; do [[ -d "$$path" ]] && paths+=("$$path"); done; \
	if (( $${#paths[@]} )); then $(VENV_RUFF) check "$${paths[@]}"; else echo "No Python paths to lint yet"; fi
	@unformatted="$$(gofmt -l services/control)"; \
	if [[ -n "$$unformatted" ]]; then echo "Go files need gofmt:"; echo "$$unformatted"; exit 1; fi

contract-test: check-python $(VENV)/.ready
	@$(VENV_PYTHON) contracts/validate.py

fixture-test: check-python $(VENV)/.ready
	@$(VENV_PYTHON) -m pytest -q fixtures/buggy-calculator/tests

fixture-baseline: check-python $(VENV)/.ready
	@output_file="$$(mktemp)"; \
	set +e; \
	$(VENV_PYTHON) -m pytest -q fixtures/buggy-calculator/tests >"$$output_file" 2>&1; \
	status=$$?; \
	set -e; \
	cat "$$output_file"; \
	if [[ $$status -ne 1 ]]; then \
		echo "ERROR: fixture exit code was $$status; expected pytest test-failure code 1"; \
		rm -f "$$output_file"; \
		exit 1; \
	fi; \
	if ! grep -Eq '1 failed, 1 passed' "$$output_file"; then \
		echo "ERROR: fixture must have exactly one failing and one passing test"; \
		rm -f "$$output_file"; \
		exit 1; \
	fi; \
	if ! grep -Eq '^FAILED .*::test_fractional_division' "$$output_file"; then \
		echo "ERROR: the expected failing node is test_fractional_division"; \
		rm -f "$$output_file"; \
		exit 1; \
	fi; \
	rm -f "$$output_file"; \
	echo "PASS: buggy-calculator has exactly one failure and one pass before repair"

clean:
	@rm -rf "$(CURDIR)/$(VENV)"
