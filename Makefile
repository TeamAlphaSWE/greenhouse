.PHONY: build run test clean

ROOT := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
UV := $(HOME)/.local/bin/uv

build:
	@if [ -f "$(ROOT)backend/requirements.txt" ]; then \
		test -d "$(ROOT)backend/.venv" || $(UV) venv "$(ROOT)backend/.venv"; \
		$(UV) pip install --python "$(ROOT)backend/.venv/bin/python" -r "$(ROOT)backend/requirements.txt"; \
	fi
# 	@if [ -f "$(ROOT)frontend/requirements.txt" ]; then \
# 		test -d "$(ROOT)frontend/.venv" || $(UV) venv "$(ROOT)frontend/.venv"; \
# 		$(UV) pip install --python "$(ROOT)frontend/.venv/bin/python" -r "$(ROOT)frontend/requirements.txt"; \
# 	fi
	@echo "Build complete."

run:
	python3 "$(ROOT)scripts/run.py"

test:
	@if [ -x "$(ROOT)backend/.venv/bin/python" ]; then \
		cd "$(ROOT)backend" && .venv/bin/python -m pytest -v; \
	else \
		echo "Backend environment not found. Run 'make build' first."; \
		exit 1; \
	fi

clean:
	rm -rf "$(ROOT)backend/.venv"
# 	rm -rf "$(ROOT)frontend/.venv"
	@echo "Clean complete."