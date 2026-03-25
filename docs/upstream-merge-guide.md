# Upstream Merge Guide — software-agent-sdk

Procedure for merging upstream changes from `OpenHands/software-agent-sdk` into our fork.

## Overview

| Item | Value |
|------|-------|
| **Upstream repo** | `https://github.com/OpenHands/software-agent-sdk` |
| **Our fork** | `https://github.com/zparnold/software-agent-sdk` |
| **Working branch** | `main` |
| **Custom commits** | ~7 (see list below) |

Unlike the OpenHands repo (which has a separate `self-hosted` branch), we work directly on `main` with custom commits on top of upstream.

## Custom Commits to Preserve

These customizations must survive every merge. Grouped by area:

### Docker/Entrypoint (CA certs for corporate TLS)
- `openhands-agent-server/openhands/agent_server/docker/entrypoint.sh`
- `openhands-agent-server/openhands/agent_server/docker/build.py` (generates entrypoint for all targets)
- `openhands-agent-server/openhands/agent_server/docker/Dockerfile` (root USER for CA cert merging)

### Webhook & Cost Tracking
- `openhands-agent-server/openhands/agent_server/event_service.py` — `model_dump(mode="json")` for kind field (upstream bug), stats emission on startup, asyncio thread-safety fix, WebSocket _closed flag
- `openhands-agent-server/openhands/agent_server/sockets.py` — WebSocket ping/pong heartbeat handler

### Org-Level Skill Registry
- `openhands-agent-server/openhands/agent_server/skills_service.py` — org skills loading with auth_header + branch
- `openhands-agent-server/openhands/agent_server/skills_router.py` — org skills routes
- `openhands-sdk/openhands/sdk/context/agent_context.py` — org skills config fields
- `openhands-sdk/openhands/sdk/context/skills/skill.py` — `load_org_skills()` function

### Performance
- `openhands-agent-server/openhands/agent_server/event_service.py` — count_events O(1) fast path

### Error Handling
- `openhands-sdk/openhands/sdk/workspace/remote/remote_workspace_mixin.py` — file download 4xx detail extraction

### Dropped (2026-03-25)
- ~~VSCode server-base-path~~ — absorbed by upstream
- ~~microagents/ directory compat~~ — removed, use skills/ only
- ~~Azure prompt_cache_retention fix~~ — absorbed by upstream
- ~~CI workflow reverts~~ — no longer needed

## Pre-Merge: Check Status

```bash
# See how far behind we are
./scripts/check-upstream-sync.sh

# Or manually:
git fetch upstream
git rev-list --count main..upstream/main    # commits behind
git rev-list --count upstream/main..main    # custom commits ahead
```

## Merge Procedure

### Step 1: Fetch upstream

```bash
cd /home/zach/development/claude_workspace/software-agent-sdk
git fetch upstream
```

### Step 2: Create a merge branch

Work on a disposable branch so `main` stays clean until the merge is verified.

```bash
git checkout main
git checkout -b merge/upstream-$(date +%Y-%m-%d)
```

### Step 3: Merge upstream/main

```bash
git merge upstream/main --no-ff -m "Merge upstream/main into main ($(date +%Y-%m-%d))"
```

### Step 4: Resolve conflicts

Conflicts will typically occur in files touched by our custom commits (listed above). For each conflict:

1. **Our custom files** (entrypoint.sh, Dockerfile, vscode_service.py, skills_service.py, etc.):
   Accept upstream changes but re-apply our customizations on top. Use `git diff upstream/main..main -- <file>` to see what we changed.

2. **Lock file** (`uv.lock`):
   Delete and regenerate:
   ```bash
   rm uv.lock
   uv lock
   ```

3. **CI/CD files** (`.github/workflows/`):
   Generally accept upstream unless we have specific CI customizations.

4. **Tests**:
   Accept upstream. If our custom code breaks upstream tests, fix the tests after merge.

### Step 5: Regenerate lock file

```bash
uv lock
```

### Step 6: Verify build

```bash
make build
```

### Step 7: Run tests

```bash
uv run pytest tests/ -x --timeout=30
```

### Step 8: Lint

```bash
make lint
```

### Step 9: Verify custom features

Check that our customizations still work:

- [ ] CA cert handling in entrypoint.sh
- [ ] VSCode server-base-path proxy support
- [ ] Webhook event serialization (kind field present)
- [ ] count_events optimization
- [ ] Org-level skill registry loads from GitHub
- [ ] Auth header passed through for skill loading
- [ ] microagents/ directory backwards compatibility

### Step 10: Complete the merge

```bash
git checkout main
git merge merge/upstream-$(date +%Y-%m-%d) --no-ff
```

### Step 11: Mark sync point

```bash
./scripts/check-upstream-sync.sh --mark
```

### Step 12: Push and deploy

```bash
git push origin main
```

Then rebuild and deploy the agent-server image as needed.

## Rollback

If something goes wrong after merging to `main`:

```bash
# Find the commit before the merge
git log --oneline -5

# Reset to pre-merge state
git reset --hard <pre-merge-sha>
git push origin main --force-with-lease
```

## Keeping This Guide Updated

After each merge, update the "Custom Commits to Preserve" section if new custom commits were added. Run `git log --oneline upstream/main..main` to get the current list.
