# Recipes use bash features (`source`). Without this, make runs them with
# /bin/sh, which is dash on Ubuntu, and `make venv-dev` fails there.
SHELL := /bin/bash

.PHONY: venv-dev
venv-dev:
	@echo Building Python virtual environment for developer
	set -e ;\
	python3 -m venv venv-dev ;\
	source venv-dev/bin/activate ;\
	pip install --upgrade pip ;\
	pip install -r requirements.txt -r requirements.dev.txt

.PHONY: fresh-requirements
fresh-requirements:
	@echo Freshening requirements files
	set -e ;\
	python3 -m piptools compile -o requirements.txt pyproject.toml ;\
	python3 -m piptools compile --extra dev -o requirements.dev.txt pyproject.toml

submodules: third_party/dogwood/Cargo.toml

third_party/dogwood/Cargo.toml:
	git submodule update --init --recursive

.PHONY: quick
quick: submodules
	@echo Performing 'quick' build
	set -e ;\
	maturin develop ;\
	$(MAKE) stubtest ;\
	pytest

.PHONY: stubtest
stubtest:
	@echo Checking dogwoodpy.pyi against the built module
	python3 -m mypy.stubtest dogwoodpy --allowlist stubtest-allowlist.txt

.PHONY: release
release: submodules
	@echo Building a release
	set -e ;\
	maturin build --release ;\
	WHEEL=$$(ls -1t target/wheels/dogwoodpy-*.whl | head -1) ;\
	echo "Installing $$WHEEL for test" ;\
	python3 -m pip install --force-reinstall --no-deps "$$WHEEL" ;\
	$(MAKE) stubtest ;\
	pytest
