SHELL := /bin/bash

PACKAGE ?= webservice
XRD_DIR := apis/webservices
COMPOSITION := $(XRD_DIR)/composition.yaml
DEFINITION := $(XRD_DIR)/definition.yaml
CONFIGURATION := $(XRD_DIR)/configuration.yaml
EXAMPLE_DEFAULT := examples/webservices/standard.yaml
RENDER_TESTS := $(wildcard tests/test-*)
E2E_TESTS := $(wildcard tests/e2etest-*)

clean:
	rm -rf _output
	rm -rf .up
	rm -f $(CONFIGURATION)

build:
	up project build

generate-configuration:
	@set -euo pipefail; \
	hops validate generate-configuration --path . --api-path "$(XRD_DIR)"

# Examples list - mirrors GitHub Actions workflow
# Format: example_path::observed_resources_path (observed_resources_path is optional)
EXAMPLES := examples/webservices/minimal.yaml:: \
    examples/webservices/public.yaml:: \
    examples/webservices/cluster.yaml:: \
    examples/webservices/authenticated.yaml:: \
    examples/webservices/configured.yaml:: \
    examples/webservices/import.yaml::

# up writes generated models into one shared .up directory; serialize examples.
render\:all:
	@set -euo pipefail; for entry in $(EXAMPLES); do \
		example=$${entry%%::*}; observed=$${entry#*::}; \
		flags=(--extra-resources=examples/platform.yaml); if [ -n "$$observed" ]; then flags+=(--observed-resources="$$observed"); fi; \
		up composition render --xrd=$(DEFINITION) $(COMPOSITION) "$$example" "$${flags[@]}"; \
	done

validate\:all: generate-configuration
	@set -euo pipefail; for entry in $(EXAMPLES); do \
		example=$${entry%%::*}; observed=$${entry#*::}; \
		flags=(--extra-resources=examples/platform.yaml); if [ -n "$$observed" ]; then flags+=(--observed-resources="$$observed"); fi; \
		up composition render --xrd=$(DEFINITION) $(COMPOSITION) "$$example" "$${flags[@]}" --include-full-xr --quiet | \
			crossplane resource validate $(XRD_DIR) --error-on-missing-schemas -; \
	done

# Shorthand aliases
.PHONY: render validate generate-configuration
render: ; @$(MAKE) 'render:all'
validate: ; @$(MAKE) generate-configuration 'validate:all'

# Single example targets
render\:%:
	@example="examples/webservices/$*.yaml"; \
	up composition render --xrd=$(DEFINITION) $(COMPOSITION) $$example --extra-resources=examples/platform.yaml

validate\:%: generate-configuration
	@set -euo pipefail; example="examples/webservices/$*.yaml"; \
	up composition render --xrd=$(DEFINITION) $(COMPOSITION) $$example --extra-resources=examples/platform.yaml \
		--include-full-xr --quiet | \
		crossplane resource validate $(XRD_DIR) --error-on-missing-schemas -

test:
	@if [ -z "$(RENDER_TESTS)" ]; then echo "No render tests found (tests/test-*). Skipping."; else up test run $(RENDER_TESTS); fi

e2e:
	up test run $(E2E_TESTS) --e2e

publish:
	@if [ -z "$(tag)" ]; then echo "Error: tag is not set. Usage: make publish tag=<version>"; exit 1; fi
	up project build --push --tag $(tag)

smoke-local:
	uv run scripts/local-smoke.py --context kind-hops
