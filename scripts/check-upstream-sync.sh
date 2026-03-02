#!/bin/bash
# check-upstream-sync.sh
# Checks if main branch is behind upstream/main and reports the delta.
# Run daily via cron to stay aware of upstream changes.
#
# Uses a marker file (.last-upstream-sync) to track the last synced upstream commit SHA.
# After a merge, run: ./scripts/check-upstream-sync.sh --mark
# to update the marker to the current upstream/main HEAD.
#
# Usage: ./scripts/check-upstream-sync.sh [--quiet|--mark]
# --quiet: Only output if there are new commits (for cron notifications)
# --mark:  Record current upstream/main HEAD as the last-synced point

set -uo pipefail
trap "" PIPE

REPO_DIR="/home/zach/development/claude_workspace/software-agent-sdk"
UPSTREAM_REMOTE="upstream"
UPSTREAM_BRANCH="main"
LOCAL_BRANCH="main"
MARKER_FILE="${REPO_DIR}/.last-upstream-sync"
ARG="${1:-}"

cd "$REPO_DIR"

# Ensure upstream remote exists
if ! git remote | grep -q "^${UPSTREAM_REMOTE}$"; then
    echo "Adding upstream remote..."
    git remote add "$UPSTREAM_REMOTE" "https://github.com/OpenHands/software-agent-sdk.git"
fi

# Fetch upstream (quietly)
git fetch "$UPSTREAM_REMOTE" --quiet 2>/dev/null

# Handle --mark: save current upstream HEAD as synced point
if [ "$ARG" = "--mark" ]; then
    UPSTREAM_HEAD=$(git rev-parse "${UPSTREAM_REMOTE}/${UPSTREAM_BRANCH}")
    echo "$UPSTREAM_HEAD" > "$MARKER_FILE"
    echo "Marked $(echo "$UPSTREAM_HEAD" | head -c 9) as last synced upstream commit"
    exit 0
fi

# Determine the base commit to compare from
if [ -f "$MARKER_FILE" ]; then
    SYNC_BASE=$(cat "$MARKER_FILE" | tr -d '[:space:]')
    # Verify the commit still exists
    if ! git cat-file -e "$SYNC_BASE" 2>/dev/null; then
        echo "WARNING: Marker commit $SYNC_BASE not found, falling back to merge-base"
        SYNC_BASE=""
    fi
fi

if [ -z "${SYNC_BASE:-}" ]; then
    # Fallback: use merge-base (works for real merges, not squash merges)
    SYNC_BASE=$(git merge-base "${LOCAL_BRANCH}" "${UPSTREAM_REMOTE}/${UPSTREAM_BRANCH}" 2>/dev/null || echo "")
    if [ -z "$SYNC_BASE" ]; then
        echo "ERROR: Could not find merge base between $LOCAL_BRANCH and $UPSTREAM_REMOTE/$UPSTREAM_BRANCH"
        exit 1
    fi
fi

BEHIND=$(git rev-list --count "${SYNC_BASE}..${UPSTREAM_REMOTE}/${UPSTREAM_BRANCH}" 2>/dev/null || echo "0")

if [ "$BEHIND" = "0" ]; then
    if [ "$ARG" != "--quiet" ]; then
        echo "$(date '+%Y-%m-%d %H:%M') | main is up to date with upstream/main"
    fi
    exit 0
fi

# Get commit summaries
echo "=========================================="
echo " Upstream Sync Report - $(date '+%Y-%m-%d %H:%M')"
echo "=========================================="
echo ""
echo "main is $BEHIND commit(s) behind upstream/main"
echo "(since $(echo "$SYNC_BASE" | head -c 9))"
echo ""

# Show custom (ahead) commits
AHEAD=$(git rev-list --count "${UPSTREAM_REMOTE}/${UPSTREAM_BRANCH}..${LOCAL_BRANCH}" 2>/dev/null || echo "0")
if [ "$AHEAD" -gt 0 ]; then
    echo "Custom commits (ahead of upstream): $AHEAD"
    git log --oneline --no-merges "${UPSTREAM_REMOTE}/${UPSTREAM_BRANCH}..${LOCAL_BRANCH}"
    echo ""
fi

echo "New upstream commits:"
echo "---"
git log --oneline --no-merges "${SYNC_BASE}..${UPSTREAM_REMOTE}/${UPSTREAM_BRANCH}" | head -30
if [ "$BEHIND" -gt 30 ]; then
    echo "... and $((BEHIND - 30)) more"
fi
echo ""

# Categorize by area
RANGE="${SYNC_BASE}..${UPSTREAM_REMOTE}/${UPSTREAM_BRANCH}"
SDK_COUNT=$(git log --oneline --no-merges "$RANGE" -- 'openhands-sdk/' | wc -l)
TOOLS_COUNT=$(git log --oneline --no-merges "$RANGE" -- 'openhands-tools/' | wc -l)
SERVER_COUNT=$(git log --oneline --no-merges "$RANGE" -- 'openhands-agent-server/' | wc -l)
WORKSPACE_COUNT=$(git log --oneline --no-merges "$RANGE" -- 'openhands-workspace/' | wc -l)
CI_COUNT=$(git log --oneline --no-merges "$RANGE" -- '.github/' | wc -l)
TESTS_COUNT=$(git log --oneline --no-merges "$RANGE" -- 'tests/' | wc -l)

echo "Breakdown:"
echo "  SDK:         $SDK_COUNT"
echo "  Tools:       $TOOLS_COUNT"
echo "  Agent Server: $SERVER_COUNT"
echo "  Workspace:   $WORKSPACE_COUNT"
echo "  CI/CD:       $CI_COUNT"
echo "  Tests:       $TESTS_COUNT"
echo ""

# Files changed summary
echo "Files changed: $(git diff --stat "${SYNC_BASE}..${UPSTREAM_REMOTE}/${UPSTREAM_BRANCH}" | tail -1)"
echo ""

# Potential conflict check
CUSTOM_FILES=$(git diff --name-only "${UPSTREAM_REMOTE}/${UPSTREAM_BRANCH}..${LOCAL_BRANCH}" 2>/dev/null)
UPSTREAM_FILES=$(git diff --name-only "${SYNC_BASE}..${UPSTREAM_REMOTE}/${UPSTREAM_BRANCH}" 2>/dev/null)
BOTH_MODIFIED=$(comm -12 <(echo "$CUSTOM_FILES" | sort) <(echo "$UPSTREAM_FILES" | sort))
CONFLICT_COUNT=$(echo "$BOTH_MODIFIED" | grep -c . || true)

if [ "$CONFLICT_COUNT" -gt 0 ]; then
    echo "Potential conflict files ($CONFLICT_COUNT files modified on both sides):"
    echo "$BOTH_MODIFIED" | head -20
    if [ "$CONFLICT_COUNT" -gt 20 ]; then
        echo "... and $((CONFLICT_COUNT - 20)) more"
    fi
    echo ""
fi

echo "Run the merge guide: docs/upstream-merge-guide.md"
echo "=========================================="
