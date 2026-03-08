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

.PHONY: test build-test

build-test:
	docker build --platform linux/amd64 \
		$(PROXY_ARGS) \
		-f Dockerfile.test -t cfb-bot-test .

test: build-test
	docker run --rm --platform linux/amd64 cfb-bot-test

# Run tests directly in the local venv (faster feedback; requires OR-Tools to work natively).
test-local:
	.venv/bin/pytest --tb=short -q
