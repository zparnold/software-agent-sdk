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

These commits contain our self-hosted customizations and must survive every merge:

1. **`198e2a9`** — `feat(docker): add entrypoint script to handle CA certs and argv stripping`
2. **`88859a8`** — `feat: configure VSCode server-base-path for proxy support`
3. **`d1b8c6f`** — `fix: serialize webhook events with mode='json' to include kind field`
4. **`a2b4f23`** — `Optimize count_events to avoid full iteration when no filters applied`
5. **`a2140ea`** — `feat: add org-level shared skill registry support`
6. **`e1fd801`** — `Add auth_header and branch support to agent-server org skills loading`
7. **`96dd776`** — `Support microagents/ directory in load_org_skills for backwards compat`

Key files touched by custom commits (high conflict risk):
- `openhands-agent-server/openhands/agent_server/docker/entrypoint.sh`
- `openhands-agent-server/openhands/agent_server/docker/Dockerfile`
- `openhands-agent-server/openhands/agent_server/vscode_service.py`
- `openhands-agent-server/openhands/agent_server/event_service.py`
- `openhands-agent-server/openhands/agent_server/conversation_service.py`
- `openhands-agent-server/openhands/agent_server/skills_service.py`
- `openhands-agent-server/openhands/agent_server/skills_router.py`

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
