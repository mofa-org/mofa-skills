OMINIX_DIR ?= $(HOME)/home/OminiX-MLX
INSTALL_DIR ?= $(HOME)/.crew/skills/mofa-voice
DEPLOY_DIR ?= dist

.PHONY: all build build-skill build-server install clean dist deploy deploy-skill deploy-server deploy-status deploy-stop release

all: build

## Build both mofa-voice skill and ominix-api server
build: build-skill build-server

## Build mofa-voice skill binary (thin HTTP client)
build-skill:
	cargo build --release

## Build ominix-api server binary (ASR + TTS inference)
build-server:
	cd $(OMINIX_DIR) && cargo build --release -p ominix-api --features asr,tts

## Install into crew skills directory
install: build
	mkdir -p $(INSTALL_DIR)
	cp target/release/mofa-voice $(INSTALL_DIR)/main
	cp manifest.json $(INSTALL_DIR)/
	cp SKILL.md $(INSTALL_DIR)/
	@echo "Installed mofa-voice skill to $(INSTALL_DIR)"
	@echo ""
	@echo "ominix-api binary at: $(OMINIX_DIR)/target/release/ominix-api"
	@echo "To deploy ominix-api, run: make dist"

## Create deployable dist/ with both binaries
dist: build
	mkdir -p $(DEPLOY_DIR)
	cp target/release/mofa-voice $(DEPLOY_DIR)/
	cp $(OMINIX_DIR)/target/release/ominix-api $(DEPLOY_DIR)/
	cp $(OMINIX_DIR)/target/release/mlx.metallib $(DEPLOY_DIR)/
	cp manifest.json $(DEPLOY_DIR)/
	cp SKILL.md $(DEPLOY_DIR)/
	@echo ""
	@echo "Deployable package in $(DEPLOY_DIR)/:"
	@ls -lh $(DEPLOY_DIR)/
	@echo ""
	@echo "Deploy to remote:"
	@echo "  scp $(DEPLOY_DIR)/ominix-api $(DEPLOY_DIR)/mofa-voice user@host:~/.crew/skills/mofa-voice/"
	@echo "  # Rename mofa-voice to main on target: mv mofa-voice main"

## Deploy everything: skill + ominix-api server + models + launchd service
deploy:
	./scripts/deploy.sh all

## Deploy skill only (into ~/.crew/skills/mofa-voice/)
deploy-skill:
	./scripts/deploy.sh skill

## Deploy server only (build + models + launchd service)
deploy-server:
	./scripts/deploy.sh server

## Check ominix-api service status
deploy-status:
	./scripts/deploy.sh status

## Stop ominix-api service
deploy-stop:
	./scripts/deploy.sh stop

## Build and publish a GitHub release (usage: make release TAG=v1.0.0)
release:
	@test -n "$(TAG)" || (echo "Usage: make release TAG=v1.0.0" && exit 1)
	./scripts/release.sh $(TAG)

clean:
	cargo clean
	rm -rf $(DEPLOY_DIR)
