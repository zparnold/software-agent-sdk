#!/bin/bash
# categorize-upstream.sh
# Lists all upstream commits since the last sync point, groups them by area
# and PR number, flags conflict risk, and outputs JSON for the cherry-pick script.
#
# Usage:
#   ./scripts/categorize-upstream.sh              # human-readable output
#   ./scripts/categorize-upstream.sh --json        # JSON output for tooling
#   ./scripts/categorize-upstream.sh --write-batches # write per-area batch files to batches/

set -uo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
UPSTREAM_REMOTE="upstream"
UPSTREAM_BRANCH="main"
LOCAL_BRANCH="main"
MARKER_FILE="${REPO_DIR}/.last-upstream-sync"
OUTPUT_JSON=false
WRITE_BATCHES=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --json) OUTPUT_JSON=true; shift ;;
        --write-batches) WRITE_BATCHES=true; shift ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

cd "$REPO_DIR"

# Ensure upstream is fresh
git fetch "$UPSTREAM_REMOTE" --quiet 2>/dev/null

# Determine sync base
if [ -f "$MARKER_FILE" ]; then
    SYNC_BASE=$(cat "$MARKER_FILE" | tr -d '[:space:]')
    if ! git cat-file -e "$SYNC_BASE" 2>/dev/null; then
        SYNC_BASE=""
    fi
fi
if [ -z "${SYNC_BASE:-}" ]; then
    SYNC_BASE=$(git merge-base "${LOCAL_BRANCH}" "${UPSTREAM_REMOTE}/${UPSTREAM_BRANCH}" 2>/dev/null || echo "")
    if [ -z "$SYNC_BASE" ]; then
        echo "ERROR: Could not determine sync base" >&2
        exit 1
    fi
fi

RANGE="${SYNC_BASE}..${UPSTREAM_REMOTE}/${UPSTREAM_BRANCH}"

# Custom (local-only) files for conflict detection
LOCAL_FILES=$(git diff --name-only "${UPSTREAM_REMOTE}/${UPSTREAM_BRANCH}..${LOCAL_BRANCH}" 2>/dev/null | sort)

# Classify a commit into an area based on its changed files
classify_commit() {
    local sha="$1"
    local files
    files=$(git diff-tree --no-commit-id --name-only -r "$sha" 2>/dev/null)

    # Priority order: most specific first
    if echo "$files" | grep -q '^\.github/'; then
        echo "ci-cd"
    elif echo "$files" | grep -q '^tests/'; then
        echo "tests"
    elif echo "$files" | grep -q '^openhands-agent-server/'; then
        echo "agent-server"
    elif echo "$files" | grep -q '^openhands-workspace/'; then
        echo "workspace"
    elif echo "$files" | grep -q '^openhands-tools/'; then
        echo "tools"
    elif echo "$files" | grep -q '^openhands-sdk/'; then
        echo "sdk"
    else
        echo "other"
    fi
}

# Extract PR number from commit message (e.g., "(#142)" or "Merge pull request #142")
extract_pr() {
    local msg="$1"
    local pr
    pr=$(echo "$msg" | grep -oP '#\d+' | head -1)
    echo "${pr:-none}"
}

# Check conflict risk for a commit
check_conflict_risk() {
    local sha="$1"
    local commit_files
    commit_files=$(git diff-tree --no-commit-id --name-only -r "$sha" 2>/dev/null | sort)
    local overlap
    overlap=$(comm -12 <(echo "$commit_files") <(echo "$LOCAL_FILES") | wc -l)

    if [ "$overlap" -gt 3 ]; then
        echo "high"
    elif [ "$overlap" -gt 0 ]; then
        echo "medium"
    else
        echo "none"
    fi
}

# Collect all commits with metadata
declare -A AREA_COMMITS  # area -> list of JSON objects
declare -A AREA_ORDER
AREA_ORDER=([ci-cd]=1 [tests]=2 [sdk]=3 [tools]=4 [workspace]=5 [agent-server]=6 [other]=7)

# Initialize area arrays
for area in ci-cd tests sdk tools workspace agent-server other; do
    AREA_COMMITS[$area]=""
done

# Process each commit
COMMITS=$(git rev-list --reverse --no-merges "$RANGE" 2>/dev/null)
TOTAL=$(echo "$COMMITS" | grep -c . || true)

if [ "$TOTAL" -eq 0 ]; then
    if [ "$OUTPUT_JSON" = true ]; then
        echo '{"batches":[],"total":0}'
    else
        echo "No upstream commits to process."
    fi
    exit 0
fi

# Process commits
while IFS= read -r sha; do
    [ -z "$sha" ] && continue
    msg=$(git log -1 --format="%s" "$sha" 2>/dev/null)
    area=$(classify_commit "$sha")
    pr=$(extract_pr "$msg")
    risk=$(check_conflict_risk "$sha")
    short="${sha:0:9}"

    if [ "$OUTPUT_JSON" = true ]; then
        entry="{\"sha\":\"${sha}\",\"short\":\"${short}\",\"message\":$(echo "$msg" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read().strip()))'),\"pr\":\"${pr}\",\"conflict_risk\":\"${risk}\"}"
        if [ -n "${AREA_COMMITS[$area]}" ]; then
            AREA_COMMITS[$area]="${AREA_COMMITS[$area]},${entry}"
        else
            AREA_COMMITS[$area]="$entry"
        fi
    else
        printf "  %-9s [%-6s] %-6s %s\n" "$short" "$risk" "$pr" "$msg"
        # Store for batch writing
        if [ -n "${AREA_COMMITS[$area]}" ]; then
            AREA_COMMITS[$area]="${AREA_COMMITS[$area]}|${sha}"
        else
            AREA_COMMITS[$area]="$sha"
        fi
    fi
done <<< "$COMMITS"

if [ "$OUTPUT_JSON" = true ]; then
    # Build JSON output
    echo -n '{"total":'
    echo -n "$TOTAL"
    echo -n ',"sync_base":"'
    echo -n "$SYNC_BASE"
    echo -n '","batches":['

    first=true
    for area in ci-cd tests sdk tools workspace agent-server other; do
        commits="${AREA_COMMITS[$area]}"
        [ -z "$commits" ] && continue

        count=$(echo "$commits" | tr ',' '\n' | wc -l)

        if [ "$first" = true ]; then
            first=false
        else
            echo -n ","
        fi

        echo -n "{\"area\":\"${area}\",\"order\":${AREA_ORDER[$area]},\"count\":${count},\"commits\":[${commits}]}"
    done

    echo "]}"
else
    # Human-readable output
    echo "=========================================="
    echo " Upstream Commit Categories"
    echo " Total: $TOTAL commits (since ${SYNC_BASE:0:9})"
    echo "=========================================="
    echo ""

    for area in ci-cd tests sdk tools workspace agent-server other; do
        commits="${AREA_COMMITS[$area]}"
        [ -z "$commits" ] && continue

        count=$(echo "$commits" | tr '|' '\n' | wc -l)
        echo "--- $area ($count commits) ---"

        # Re-display commits for this area
        IFS='|' read -ra sha_list <<< "$commits"
        for sha in "${sha_list[@]}"; do
            msg=$(git log -1 --format="%s" "$sha" 2>/dev/null)
            risk=$(check_conflict_risk "$sha")
            pr=$(extract_pr "$msg")
            printf "  %-9s [%-6s] %-6s %s\n" "${sha:0:9}" "$risk" "$pr" "$msg"
        done
        echo ""
    done

    # Write batch files if requested
    if [ "$WRITE_BATCHES" = true ]; then
        BATCH_DIR="${REPO_DIR}/batches"
        mkdir -p "$BATCH_DIR"
        for area in ci-cd tests sdk tools workspace agent-server other; do
            commits="${AREA_COMMITS[$area]}"
            [ -z "$commits" ] && continue

            batch_file="${BATCH_DIR}/${area}.txt"
            echo "# Batch: $area" > "$batch_file"
            echo "# Generated: $(date '+%Y-%m-%d %H:%M')" >> "$batch_file"
            IFS='|' read -ra sha_list <<< "$commits"
            for sha in "${sha_list[@]}"; do
                msg=$(git log -1 --format="%s" "$sha" 2>/dev/null)
                echo "${sha}  # ${msg}" >> "$batch_file"
            done
            echo "Wrote $batch_file (${#sha_list[@]} commits)"
        done
    fi
fi
