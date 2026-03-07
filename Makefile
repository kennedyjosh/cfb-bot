PROXY := http://host.docker.internal:3128

.PHONY: test build-test

build-test:
	docker build --platform linux/amd64 \
		--build-arg HTTP_PROXY=$(PROXY) \
		--build-arg HTTPS_PROXY=$(PROXY) \
		-f Dockerfile.test -t cfb-bot-test .

test: build-test
	docker run --rm cfb-bot-test
