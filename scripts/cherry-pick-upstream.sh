#!/bin/bash
# cherry-pick-upstream.sh
# Cherry-picks upstream commits individually or in batches, with conflict
# handling, progress tracking, and automatic test validation.
#
# Usage:
#   ./scripts/cherry-pick-upstream.sh --range <sha1>..<sha2>   # cherry-pick a range
#   ./scripts/cherry-pick-upstream.sh --file <batch-file>       # cherry-pick SHAs from a file (one per line)
#   ./scripts/cherry-pick-upstream.sh --resume                  # continue from last checkpoint
#   ./scripts/cherry-pick-upstream.sh --dry-run --range ...     # show what would be cherry-picked
#   ./scripts/cherry-pick-upstream.sh --test                    # run tests after each commit (default: batch end only)
#
# Progress is tracked in .cherry-pick-progress. On conflict, the script
# pauses and prints instructions for manual resolution.

set -uo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PROGRESS_FILE="${REPO_DIR}/.cherry-pick-progress"
UPSTREAM_REMOTE="upstream"
UPSTREAM_BRANCH="main"

# Defaults
MODE=""
RANGE=""
BATCH_FILE=""
DRY_RUN=false
TEST_EACH=false
RESUME=false

usage() {
    cat <<'USAGE'
Usage: cherry-pick-upstream.sh [OPTIONS]

Options:
  --range <sha1>..<sha2>   Cherry-pick commits in the given range
  --file <path>            Cherry-pick SHAs listed in file (one per line, # comments ok)
  --resume                 Resume from last checkpoint in .cherry-pick-progress
  --dry-run                Show commits that would be cherry-picked without applying
  --test                   Run 'make test && make lint' after each commit (default: end only)
  -h, --help               Show this help

Examples:
  # Cherry-pick CI/CD commits
  ./scripts/cherry-pick-upstream.sh --range abc1234..def5678

  # Cherry-pick from a batch file produced by categorize-upstream.sh
  ./scripts/cherry-pick-upstream.sh --file batches/ci-cd.txt

  # Resume after resolving a conflict
  ./scripts/cherry-pick-upstream.sh --resume

  # Preview what would happen
  ./scripts/cherry-pick-upstream.sh --dry-run --range abc1234..def5678
USAGE
    exit 0
}

# Parse args
while [[ $# -gt 0 ]]; do
    case "$1" in
        --range)
            MODE="range"
            RANGE="$2"
            shift 2
            ;;
        --file)
            MODE="file"
            BATCH_FILE="$2"
            shift 2
            ;;
        --resume)
            RESUME=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --test)
            TEST_EACH=true
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo "Unknown option: $1"
            usage
            ;;
    esac
done

cd "$REPO_DIR"

# Ensure upstream remote exists and is fresh
if ! git remote | grep -q "^${UPSTREAM_REMOTE}$"; then
    echo "ERROR: upstream remote not found. Add it with:"
    echo "  git remote add upstream https://github.com/OpenHands/software-agent-sdk.git"
    exit 1
fi
echo "Fetching upstream..."
git fetch "$UPSTREAM_REMOTE" --quiet 2>/dev/null

# Collect the list of SHAs to cherry-pick
collect_shas() {
    local shas=()

    if [ "$MODE" = "range" ]; then
        # Convert range to list of SHAs (oldest first)
        mapfile -t shas < <(git rev-list --reverse --no-merges "$RANGE" 2>/dev/null)
        if [ ${#shas[@]} -eq 0 ]; then
            echo "ERROR: No commits found in range $RANGE"
            exit 1
        fi
    elif [ "$MODE" = "file" ]; then
        if [ ! -f "$BATCH_FILE" ]; then
            echo "ERROR: Batch file not found: $BATCH_FILE"
            exit 1
        fi
        while IFS= read -r line; do
            # Skip comments and blank lines
            line=$(echo "$line" | sed 's/#.*//' | tr -d '[:space:]')
            [ -z "$line" ] && continue
            shas+=("$line")
        done < "$BATCH_FILE"
        if [ ${#shas[@]} -eq 0 ]; then
            echo "ERROR: No SHAs found in $BATCH_FILE"
            exit 1
        fi
    else
        echo "ERROR: Must specify --range or --file (or --resume)"
        usage
    fi

    printf '%s\n' "${shas[@]}"
}

# Save progress
save_progress() {
    local sha="$1"
    local status="$2"  # "done" or "conflict"
    local remaining="$3"
    echo "${sha} ${status} ${remaining}" > "$PROGRESS_FILE"
}

# Load progress for resume
load_resume_point() {
    if [ ! -f "$PROGRESS_FILE" ]; then
        echo "ERROR: No progress file found at $PROGRESS_FILE"
        echo "Nothing to resume. Start with --range or --file."
        exit 1
    fi
    local last_sha last_status
    read -r last_sha last_status _ < "$PROGRESS_FILE"
    echo "$last_sha $last_status"
}

run_tests() {
    echo ""
    echo "--- Running tests ---"
    if make test && make lint; then
        echo "--- Tests PASSED ---"
        return 0
    else
        echo "--- Tests FAILED ---"
        return 1
    fi
}

# Main cherry-pick loop
do_cherry_pick() {
    local shas
    mapfile -t shas < <(collect_shas)
    local total=${#shas[@]}
    local skip_until=""

    # Handle resume: find where we left off
    if [ "$RESUME" = true ]; then
        local resume_info
        resume_info=$(load_resume_point)
        local resume_sha resume_status
        read -r resume_sha resume_status <<< "$resume_info"

        if [ "$resume_status" = "conflict" ]; then
            echo "Last attempt had a conflict on $resume_sha."
            echo "Checking if conflict is resolved..."

            # Check for unmerged files
            if git diff --name-only --diff-filter=U 2>/dev/null | grep -q .; then
                echo ""
                echo "There are still unmerged files. Resolve them, then:"
                echo "  git add <resolved-files>"
                echo "  ./scripts/cherry-pick-upstream.sh --resume"
                exit 1
            fi

            # Conflict was resolved, commit it
            local orig_msg
            orig_msg=$(git log -1 --format="%s" "$resume_sha" 2>/dev/null || echo "cherry-pick $resume_sha")
            git commit --no-edit -m "${orig_msg}

(cherry-picked from ${resume_sha})" 2>/dev/null || true
            echo "Committed resolved cherry-pick for $resume_sha"
            skip_until="$resume_sha"
        else
            # Last SHA was successfully done, skip everything up to and including it
            skip_until="$resume_sha"
        fi
    fi

    local count=0
    local skipping=true
    [ -z "$skip_until" ] && skipping=false

    for sha in "${shas[@]}"; do
        # Skip already-processed commits when resuming
        if [ "$skipping" = true ]; then
            if [ "$sha" = "$skip_until" ]; then
                skipping=false
            fi
            continue
        fi

        count=$((count + 1))
        local remaining=$((total - count))
        local short_sha="${sha:0:9}"
        local msg
        msg=$(git log -1 --format="%s" "$sha" 2>/dev/null || echo "unknown")

        echo ""
        echo "[$count/$total] Cherry-picking $short_sha: $msg"

        if [ "$DRY_RUN" = true ]; then
            echo "  (dry-run) Would cherry-pick: $short_sha"
            continue
        fi

        # Attempt cherry-pick with --no-commit first to stage changes
        if git cherry-pick --no-commit "$sha" 2>/dev/null; then
            # No conflicts - commit with trailer
            git commit --no-edit -m "${msg}

(cherry-picked from ${sha})" 2>/dev/null
            echo "  OK"
            save_progress "$sha" "done" "$remaining"

            # Run tests if --test flag is set
            if [ "$TEST_EACH" = true ]; then
                if ! run_tests; then
                    echo ""
                    echo "Tests failed after cherry-picking $short_sha."
                    echo "Fix the issue, then run: ./scripts/cherry-pick-upstream.sh --resume"
                    save_progress "$sha" "done" "$remaining"
                    exit 1
                fi
            fi
        else
            # Conflict detected
            save_progress "$sha" "conflict" "$remaining"
            echo ""
            echo "=========================================="
            echo " CONFLICT on $short_sha"
            echo "=========================================="
            echo ""
            echo "Conflicted files:"
            git diff --name-only --diff-filter=U 2>/dev/null || true
            echo ""
            echo "To resolve:"
            echo "  1. Edit the conflicted files"
            echo "  2. git add <resolved-files>"
            echo "  3. ./scripts/cherry-pick-upstream.sh --resume"
            echo ""
            echo "To skip this commit:"
            echo "  git cherry-pick --abort (or git reset --hard HEAD)"
            echo "  Edit .cherry-pick-progress to mark as 'done'"
            echo "  ./scripts/cherry-pick-upstream.sh --resume"
            echo ""
            echo "Remaining: $remaining commits after this one"
            exit 1
        fi
    done

    if [ "$DRY_RUN" = true ]; then
        echo ""
        echo "Dry run complete. $total commits would be cherry-picked."
        exit 0
    fi

    echo ""
    echo "=========================================="
    echo " All $total commits cherry-picked successfully!"
    echo "=========================================="

    # Run final tests
    echo ""
    echo "Running final validation..."
    if run_tests; then
        echo ""
        echo "All tests pass. Batch complete."
        rm -f "$PROGRESS_FILE"
    else
        echo ""
        echo "Tests failed after completing all cherry-picks."
        echo "Review and fix before proceeding."
        exit 1
    fi
}

# Handle resume-only mode (no --range or --file, just --resume)
if [ "$RESUME" = true ] && [ -z "$MODE" ]; then
    # Try to read the batch file or range from progress
    if [ -f "$PROGRESS_FILE" ]; then
        echo "Resuming from progress file..."
        # We need the original SHA list. Check if there's a batch file reference.
        echo "ERROR: --resume requires --range or --file to know the full commit list."
        echo "Re-run with the original --range or --file plus --resume."
        exit 1
    fi
fi

if [ -z "$MODE" ] && [ "$RESUME" != true ]; then
    echo "ERROR: Must specify --range, --file, or --resume"
    usage
fi

do_cherry_pick
