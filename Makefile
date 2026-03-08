# Set PROXY to use an HTTP proxy for pip inside the Docker build.
# Required in sandbox environments; leave unset for direct access (Mac/CI default).
# Example: make test PROXY=http://host.docker.internal:3128
PROXY ?=

ifdef PROXY
PROXY_ARGS := --build-arg HTTP_PROXY=$(PROXY) --build-arg HTTPS_PROXY=$(PROXY)
# Pass the proxy CA cert as a BuildKit secret if the file exists locally.
ifneq (,$(wildcard proxy-ca.crt))
PROXY_ARGS += --secret id=proxy_cert,src=proxy-ca.crt
endif
else
PROXY_ARGS :=
endif

.PHONY: test build-test test-local venv run

build-test:
	docker build --platform linux/amd64 \
		$(PROXY_ARGS) \
		-f Dockerfile.test -t cfb-bot-test .

# Run tests inside a linux/amd64 Docker container (matches production).
test: build-test
	docker run --rm --platform linux/amd64 cfb-bot-test

# Sentinel: create/update the venv when requirements.txt changes.
.venv/bin/python3: requirements.txt
	python3 -m venv .venv
	.venv/bin/pip install --upgrade pip -q
	.venv/bin/pip install -r requirements.txt

# Run the bot. Creates/updates the venv automatically if needed.
run: .venv/bin/python3
	.venv/bin/python3 main.py

# Set up the local virtual environment with all dependencies (including dev).
venv:
	python3 -m venv .venv
	.venv/bin/pip install --upgrade pip -q
	.venv/bin/pip install -r requirements.txt -r requirements-dev.txt

# Run tests in the local venv (fast feedback; requires OR-Tools to work natively).
# Run `make venv` first if the venv doesn't exist yet.
test-local:
	.venv/bin/pytest --tb=short -q
