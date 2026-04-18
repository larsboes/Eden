#!/bin/bash
# Join AstroFarm — finds your agent pane, breaks it into its own window, fullscreen
# Usage: ./join.sh lars (or pj, johannes, bryan, lead)
set -e

NAME="${1,,}"
SESSION="astrofarm"

if [ -z "$NAME" ]; then
    echo "Usage: ./multiplayer/join.sh <name>"
    echo "  lars | pj | johannes | bryan | lead"
    exit 1
fi

if ! tmux has-session -t $SESSION 2>/dev/null; then
    echo "No session. Run: launch"
    exit 1
fi

MY_SESSION="${SESSION}-${NAME}"

# Already joined before? Just reattach
if tmux has-session -t "$MY_SESSION" 2>/dev/null; then
    tmux attach -t "$MY_SESSION"
    exit 0
fi

# Already broken out into its own window? Create grouped session for it
if tmux list-windows -t $SESSION -F "#{window_name}" 2>/dev/null | grep -qx "$NAME"; then
    tmux new-session -d -t $SESSION -s "$MY_SESSION"
    tmux select-window -t "$MY_SESSION:$NAME"
    tmux attach -t "$MY_SESSION"
    exit 0
fi

# Map name to the label Claude puts at the pane bottom
case "$NAME" in
    lars)     LABEL="@Lars-Agent" ;;
    pj)       LABEL="@PJ-Agent" ;;
    johannes) LABEL="@Johannes-Agent" ;;
    bryan)    LABEL="@Bryan-Agent" ;;
    lead)     LABEL="@team-lead" ;;
    *)        echo "Unknown: $NAME"; exit 1 ;;
esac

# Find pane: teammate panes have ONLY their own @Name-Agent label
# The lead pane lists ALL agents — so we match panes with exactly 1 unique agent label
TARGET=""
for win in $(tmux list-windows -t $SESSION -F "#{window_index}"); do
    for i in $(tmux list-panes -t "$SESSION:$win" -F "#{pane_index}"); do
        content=$(tmux capture-pane -t "$SESSION:$win.$i" -p 2>/dev/null)
        labels=$(echo "$content" | grep -oE "@(Lars|PJ|Johannes|Bryan)-Agent" | sort -u)
        count=$(echo "$labels" | grep -c . || true)

        if [ "$NAME" = "lead" ]; then
            # Lead has multiple agent labels
            if [ "$count" -gt 1 ]; then
                TARGET="$win.$i"
                break 2
            fi
        else
            # Teammate has exactly 1 label matching itself
            if [ "$count" -eq 1 ] && echo "$labels" | grep -q "$LABEL"; then
                TARGET="$win.$i"
                break 2
            fi
        fi
    done
done

if [ -z "$TARGET" ]; then
    echo "Can't find pane for '$NAME'."
    echo "Available:"
    for win in $(tmux list-windows -t $SESSION -F "#{window_index}"); do
        for i in $(tmux list-panes -t "$SESSION:$win" -F "#{pane_index}"); do
            l=$(tmux capture-pane -t "$SESSION:$win.$i" -p 2>/dev/null | grep -oE "@(Lars|PJ|Johannes|Bryan)-Agent|@team-lead" | tail -1)
            echo "  window $win pane $i: ${l:-?}"
        done
    done
    tmux attach -t $SESSION
    exit 0
fi

# Break pane into its own window
tmux break-pane -d -s "$SESSION:$TARGET" -n "$NAME"

# Grouped session viewing that window
tmux new-session -d -t $SESSION -s "$MY_SESSION"
tmux select-window -t "$MY_SESSION:$NAME"
tmux attach -t "$MY_SESSION"
