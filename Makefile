BASE_IMAGE := continuumio/miniconda3:4.8.2
IMAGE_TAG := 1.0.0

.PHONY: build
build:
	docker build \
		-t nimbus16.llnl.gov:8443/public/keycloak-notifier:$(IMAGE_TAG) \
		--build-arg BASE_IMAGE=$(BASE_IMAGE) \
		.
