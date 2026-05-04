HAS_UV := $(shell command -v uv 2> /dev/null)

ifdef HAS_UV
    RUN := uv run
    VENV_CMD := uv venv
    INSTALL_DEV_CMD := uv sync --all-extras
else
    RUN :=
    VENV_CMD := python -m venv .venv
    INSTALL_DEV_CMD := pip install .[dev]
endif

target:
	@printf "\033[1mTagify v$(shell grep -oP '(?<=__version__ = ")[^"]*' tagify/__init__.py)\033[0m / Use 'make \033[0;36mtarget\033[0m' where \033[0;36mtarget\033[0m is one of the following:\n\n"
	@awk -F ':|##' '/^[^\t].+?:.*?##/ {t[++c]=$$1; d[c]=$$NF; type[c]=1; if(length($$1)>m) m=length($$1)} /^##@/ {type[++c]=0; text[c]=substr($$0, 5)} END {for(i=1;i<=c;i++) if(type[i]==1) printf "  \033[0;36m%-*s\033[0m %s\n", m, t[i], d[i]; else {if(h++) printf "\n"; printf "\033[1m%s\033[0m\n", text[i]}}' $(MAKEFILE_LIST)

# Production tools
install:  ## Install the package
	pip install .

uninstall:  ## Uninstall the package
	pip uninstall -y tagify

reinstall: uninstall install  ## Reinstall the package

# Development tools
install_dev:	 ## Install the package in development mode
	$(INSTALL_DEV_CMD)

venv:  ## Create a virtual environment
	$(VENV_CMD)

type:  ## Run pyright on the package
	@$(RUN) pyright discord_http --pythonversion 3.11

lint:  ## Run ruff linter
	@$(RUN) ruff check --config pyproject.toml

test:  ## Run automated tests with Python unittest
	@$(RUN) python -m unittest discover -s tests -p "test_*.py"

clean:  ## Clean the project
	@rm -rf build dist *.egg-info .venv docs/_build
	@rm uv.lock

# Maintainer-only commands
upload_pypi:  ## Maintainer only - Upload latest version to PyPi
	@echo Uploading to PyPi...
	uv build
	uvx uv-publish
	@echo Done!
