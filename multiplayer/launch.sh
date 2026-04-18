#!/bin/bash
# AstroFarm Mission Control - fully automated multiplayer launch
# One command. Creates team, spawns 4 teammate panes, ready to go.
set -e

cd ~/astrofarm
SESSION="astrofarm"

# Bedrock
export CLAUDE_CODE_USE_BEDROCK=1
export AWS_REGION=us-west-2
export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1
export ANTHROPIC_DEFAULT_SONNET_MODEL="us.anthropic.claude-sonnet-4-6"
export ANTHROPIC_DEFAULT_OPUS_MODEL="us.anthropic.claude-opus-4-6-v1"
export ANTHROPIC_DEFAULT_HAIKU_MODEL="us.anthropic.claude-haiku-4-5-20251001-v1:0"

if tmux has-session -t $SESSION 2>/dev/null; then
    echo "Already running. Use: mc"
    tmux attach -t $SESSION
    exit 0
fi

# Clean old team state
rm -rf ~/.claude/teams/astrofarm ~/.claude/tasks/astrofarm 2>/dev/null

echo ""
echo "  === ASTROFARM MISSION CONTROL ==="
echo ""
echo "  Launching lead + auto-spawning 4 teammates..."
echo "  Teammates will appear as tmux panes."
echo ""

# Start tmux session
tmux new-session -d -s $SESSION -c ~/astrofarm

# The magic: pipe "go" into Claude. System prompt triggers team creation.
# Claude processes "go", spawns teammates as tmux panes, then stays interactive.
tmux send-keys -t $SESSION \
    "echo 'go' | claude --dangerously-skip-permissions --model sonnet --teammate-mode tmux --append-system-prompt \"\$(cat ~/astrofarm/multiplayer/prompts/coordinator.md)\"" Enter

echo "  Lead is starting. Team will spawn in ~30-60s."
echo ""
echo "  Commands:"
echo "    mc              — attach to session"
echo "    Ctrl+B q        — show pane numbers"
echo "    Ctrl+B <arrow>  — switch between panes"
echo "    Shift+Down      — cycle teammates (in lead pane)"
echo "    Ctrl+B d        — detach (keeps everything running)"
echo ""

sleep 3
tmux attach -t $SESSION
