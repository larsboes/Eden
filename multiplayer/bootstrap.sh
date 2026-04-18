#!/bin/bash
# AstroFarm Mission Control - EC2 bootstrap (runs as user data on boot)
set -euxo pipefail
export DEBIAN_FRONTEND=noninteractive

# --- System deps ---
apt-get update
apt-get install -y tmux git curl build-essential unzip jq

# --- Node.js 22 LTS ---
curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
apt-get install -y nodejs

# --- AWS CLI v2 ---
curl -s "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o /tmp/awscli.zip
unzip -q /tmp/awscli.zip -d /tmp && /tmp/aws/install && rm -rf /tmp/aws*

# --- Claude Code ---
npm install -g @anthropic-ai/claude-code

# --- AWS config (instance profile provides creds, just need region) ---
mkdir -p /home/ubuntu/.aws
cat > /home/ubuntu/.aws/config << 'EOF'
[profile astrofarm]
region = us-west-2
[default]
region = us-west-2
EOF

# --- Claude Code user-level config (overrides repo settings on EC2) ---
mkdir -p /home/ubuntu/.claude
cat > /home/ubuntu/.claude/settings.json << 'EOF'
{
  "env": {
    "CLAUDE_CODE_USE_BEDROCK": "1",
    "AWS_REGION": "us-west-2",
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1",
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "us.anthropic.claude-opus-4-6-v1",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "us.anthropic.claude-sonnet-4-6",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "us.anthropic.claude-haiku-4-5-20251001-v1:0"
  },
  "permissions": {
    "allow": [
      "Bash(*)",
      "Read", "Edit", "Write", "Glob", "Grep",
      "WebFetch(*)", "WebSearch(*)", "Agent(*)"
    ]
  }
}
EOF

# --- Shell aliases & env ---
cat >> /home/ubuntu/.bashrc << 'RCEOF'

# === AstroFarm Mission Control ===
export CLAUDE_CODE_USE_BEDROCK=1
export AWS_REGION=us-west-2
export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1
export ANTHROPIC_DEFAULT_OPUS_MODEL="us.anthropic.claude-opus-4-6-v1"
export ANTHROPIC_DEFAULT_SONNET_MODEL="us.anthropic.claude-sonnet-4-6"
export ANTHROPIC_DEFAULT_HAIKU_MODEL="us.anthropic.claude-haiku-4-5-20251001-v1:0"

alias farm='cd ~/astrofarm'
alias launch='~/astrofarm/multiplayer/launch.sh'
alias mc='tmux attach -t astrofarm 2>/dev/null || echo "Run: launch"'
alias mc-lars='~/astrofarm/multiplayer/join.sh lars'
alias mc-pj='~/astrofarm/multiplayer/join.sh pj'
alias mc-johannes='~/astrofarm/multiplayer/join.sh johannes'
alias mc-bryan='~/astrofarm/multiplayer/join.sh bryan'
alias mc-lead='~/astrofarm/multiplayer/join.sh lead'
RCEOF

# --- Project dir (team will git clone into this) ---
mkdir -p /home/ubuntu/astrofarm

# --- Ownership ---
chown -R ubuntu:ubuntu /home/ubuntu/astrofarm /home/ubuntu/.aws /home/ubuntu/.claude

echo "READY" > /home/ubuntu/setup-complete
