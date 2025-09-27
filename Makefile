FLAKE8_CONFIG := $(shell \
	if python -c "import toml" 2>/dev/null; then \
		python -c "import toml; data = toml.load('pyproject.toml'); flake8 = data.get('tool', {}).get('flake8', {}); max_line_length = flake8.get('max-line-length', 128); ignores = ' '.join(['--ignore=' + i for i in flake8.get('ignore', [])]); print(f'--max-line-length {max_line_length} {ignores}')"; \
	else \
		echo "--max-line-length 128"; \
	fi)

target:
	@echo -e "\033[1mtagify v$(shell grep -oP '(?<=__version__ = ")[^"]*' tagify/__init__.py)\033[0m" \
	"\nUse 'make \033[0;36mtarget\033[0m' where \033[0;36mtarget\033[0m is one of the following:"
	@awk -F ':|##' '/^[^\t].+?:.*?##/ { printf " \033[0;36m%-15s\033[0m %s\n", $$1, $$NF }' $(MAKEFILE_LIST)

# Production tools
install:  ## Install the package
	pip install .

uninstall:  ## Uninstall the package
	pip uninstall -y tagify

reinstall: uninstall install  ## Reinstall the package

# Development tools
install_dev:	 ## Install the package in development mode
	uv sync --all-extras || pip install .[dev]

test:	## Run tests with pytest
	@cd tests && uv run test_basics.py

venv:  ## Create a virtual environment
	uv venv || python -m venv .venv

type:  ## Run pyright on the package
	@uv run pyright tagify --pythonversion 3.11 || pyright tagify --pythonversion 3.11

lint:  ## Run ruff linter
	@uv run ruff check --config pyproject.toml || ruff check --config pyproject.toml

clean:  ## Clean the project
	@rm -rf build dist *.egg-info .venv docs/_build
	@rm uv.lock

# Maintainer-only commands
upload_pypi:  ## Maintainer only - Upload latest version to PyPi
	@echo Uploading to PyPi...
	uv build
	uvx uv-publish
	@echo Done!
