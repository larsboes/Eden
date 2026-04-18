# AstroFarm Mission Control
# Multiplayer Claude Code for hackathon teams

# --- Infrastructure ---

deploy: ## Deploy EC2 instance (run once)
	@echo "Sourcing AWS creds and deploying..."
	cd infra && source ../setup-bedrock.sh && uv run pulumi up --stack dev --yes

destroy: ## Tear down EC2 instance
	cd infra && source ../setup-bedrock.sh && uv run pulumi destroy --stack dev --yes

preview: ## Preview infra changes
	cd infra && source ../setup-bedrock.sh && uv run pulumi preview --stack dev

# --- Connection ---

IP := $(shell cd infra && source ../setup-bedrock.sh 2>/dev/null && uv run pulumi stack output public_ip --stack dev 2>/dev/null)

ssh: ## SSH into the EC2 instance
	ssh -i astrofarm-key.pem ubuntu@$(IP)

key: ## Export SSH key from Pulumi (run after deploy)
	cd infra && source ../setup-bedrock.sh 2>/dev/null && uv run pulumi stack output ssh_private_key --show-secrets --stack dev > ../astrofarm-key.pem
	chmod 600 astrofarm-key.pem
	@echo "Key saved to astrofarm-key.pem — share with your team"

ip: ## Show EC2 public IP
	@echo $(IP)

status: ## Check if EC2 bootstrap is done
	ssh -i astrofarm-key.pem -o StrictHostKeyChecking=no ubuntu@$(IP) "cat ~/setup-complete 2>/dev/null && claude --version || echo 'STILL BOOTSTRAPPING...'"

# --- On the EC2 (run after SSH) ---
# launch         → start multiplayer Claude session (first person only)
# mc-lars        → attach as Lars
# mc-pj          → attach as PJ
# mc-johannes    → attach as Johannes
# mc-bryan       → attach as Bryan
# mc             → attach to main session
# farm           → cd ~/astrofarm
# team-status    → list tmux sessions

# --- AgentCore ---

deploy-agentcore: ## Deploy AgentCore Gateway + Runtime (after pulumi up)
	./scripts/deploy-agentcore.sh

deploy-agentcore-gateway: ## Deploy only AgentCore Gateway (skip Runtime)
	./scripts/deploy-agentcore.sh --skip-runtime

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help
.PHONY: deploy destroy preview ssh key ip status help deploy-agentcore deploy-agentcore-gateway
