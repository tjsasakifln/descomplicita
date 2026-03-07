# Descomplicita Proactive Squad Activation Guide

**Status:** Auto-activation system ready
**Version:** 1.0
**Framework:** Synkra AIOS + Smart Context Detection

---

## Overview

Never worry about which squad to activate. Descomplicita's intelligent context detection automatically:

✅ **Detects your context** - Analyzes what you're doing
✅ **Suggests squad proactively** - Offers the right squad automatically
✅ **Guides next steps** - Shows exactly what to do next
✅ **Tracks progress** - Monitors story status and test coverage

---

## How It Works

### 1️⃣ Automatic Detection (Session Start)

When you start work, the system automatically:

```
┌─────────────────────────────────────────┐
│ Analyzing Descomplicita Project Context...      │
└─────────────────────────────────────────┘
          ↓
  ┌─────────────────────────┐
  │ Context Signals:        │
  │ • Directory: backend/   │
  │ • Branch: feature/fix   │
  │ • Files: 5 modified     │
  │ • Story: In progress    │
  └─────────────────────────┘
          ↓
  ┌─────────────────────────┐
  │ Confidence: 95%         │
  │ Squad: Backend ✅       │
  └─────────────────────────┘
```

### 2️⃣ Adaptive Greeting

You see a personalized greeting:

```
🐍 Descomplicita Development Assistant

📍 Detected: 🐍 Backend Development
   Modified: 5 backend files, 2 frontend files
   Branch: feature/issue-31-production-deployment

💡 Recommended Squad:
   🐍 Team Descomplicita Backend
   FastAPI development, PNCP client, database work
   Agents: architect, dev, data-engineer, qa
   Confidence: 95%

🚀 Next Steps:
   1. Type: /bidiq backend
   2. Use: *help (for command reference)
   3. Start: *develop (to begin implementation)

📖 Need help? See: docs/guides/bidiq-development-guide.md
─────────────────────────────────────────────────
```

### 3️⃣ Intelligent Suggestions

Throughout your session, system proactively suggests:

- **Coverage alerts** - "Backend coverage 65% (target: 70%)"
- **Story progress** - "5 of 8 tasks complete"
- **Test failures** - "2 tests failing in pncp_client.py"
- **Uncommitted changes** - "3 files with uncommitted changes"

### 4️⃣ Exit Guidance (When Leaving Squad)

When you exit a squad, you see:

```
═══════════════════════════════════════════════
🔄 Exiting team-bidiq-backend
═══════════════════════════════════════════════

📊 SESSION SUMMARY

✅ Accomplishments:
   • Implemented PNCP pagination logic
   • Added 4 new test cases
   • Updated documentation

📖 Active Story: story-2-1-pncp-pagination
   Progress: [█████████░░░░░░░░░░] 50% (4/8 tasks)

📝 Uncommitted Changes: 3 file(s)

🧪 Test Coverage: ✅ [██████████████████░░] 96% (target: 70%)

═══════════════════════════════════════════════

🎯 NEXT STEPS

1. 🟠 Commit your changes
   Reason: 3 file(s) with uncommitted changes
   Run: git add . && git commit -m "message"

2. 🟠 Continue story-2-1-pncp-pagination
   Reason: 4 task(s) remaining in active story
   Run: /bidiq backend (or appropriate squad)

═══════════════════════════════════════════════
```

---

## Usage Scenarios

### Scenario 1: Start Your Day

**What Happens:**
```bash
# You cd into backend/ directory
cd ~/projects/bidiq/backend

# System automatically detects
🐍 Descomplicita Development Assistant
📍 Detected: 🐍 Backend Development
💡 Recommended: team-bidiq-backend
🚀 Type: /bidiq backend
```

**What You Do:**
```bash
/bidiq backend
# Squad activates with all agents ready
```

---

### Scenario 2: Working on Story

**What Happens:**
```bash
# You're editing backend code for a story
vim backend/pncp_client.py

# System detects:
# • File: pncp_client.py (backend)
# • Branch: feature/issue-31
# • Story: story-2-1 (in progress)
# • Context: Backend development

💡 Recommended: team-bidiq-backend
📖 Active Story: story-2-1 (50% complete)
```

**What You Do:**
```bash
# Continue with your squad
@dev: *develop
# Implementation continues

# Or switch squads if needed
/bidiq feature
# Switches to feature squad for architecture review
```

---

### Scenario 3: Before Committing

**What Happens:**
```bash
# System detects you're about to commit
git status

# Analysis shows:
# • 3 modified files
# • Tests: 96% coverage ✅
# • Coverage threshold: 70% ✅
# • All tests passing ✅

✅ Ready to commit!
```

**What You Do:**
```bash
git add .
git commit -m "feat(pncp): implement pagination"
# Commit succeeds, squad suggests next step
```

---

## Configuration

### Enable Auto-Activation

The system is configured in `.aios-core/development/configs/bidiq-activation-config.yaml`:

```yaml
activation:
  enabled: true              # Global enable/disable
  greeting_on_start: true    # Show greeting on session start
  context_detection: true    # Detect context automatically
  auto_suggest: true         # Suggest squads proactively

greeting:
  confidence_threshold: 40   # Only suggest if >= 40% confident
  show_context: true         # Show detected context
  show_recommendations: true # Show action recommendations
```

### Customize Detection Rules

Add your own context detection rules in the config:

```yaml
context_rules:
  backend:
    directories:
      - backend/
      - backend/**/*.py
    branches:
      - feature/backend-*
    squad: team-bidiq-backend
    confidence_boost: 20
```

---

## Manual Activation (When Auto Doesn't Work)

If auto-detection doesn't trigger, manually activate:

```bash
# See your context
node .aios-core/development/scripts/bidiq-greeting-system.js

# Get full project analysis
node .aios-core/development/scripts/bidiq-context-detector.js

# Or manually activate
/bidiq backend
/bidiq frontend
/bidiq feature
```

---

## What Gets Detected

### Context Signals

The system analyzes multiple signals:

| Signal | Examples | Weight |
|--------|----------|--------|
| **Directory** | `backend/`, `frontend/`, `docs/stories/` | 30% |
| **Git Branch** | `feature/*`, `fix/*`, main | 25% |
| **Modified Files** | Which files you changed | 25% |
| **Story Status** | In progress, pending, blocked | 15% |
| **Test Status** | Coverage, failures | 5% |

### Confidence Calculation

```
Base Confidence: 50%

+ Directory match: +30%
+ Branch match: +25%
+ File match: +20%
+ Story activity: +10%
+ Test status: +5%

= Total Confidence (0-100%)
```

Only suggestions with ≥40% confidence are shown.

---

## Proactive Alerts

System proactively notifies you about:

### 🔴 Critical Issues
- Test failures preventing merge
- Blocked stories
- Missing required commits

### 🟠 High Priority
- Coverage below threshold (70%/60%)
- Uncommitted changes
- Incomplete stories

### 🟡 Medium Priority
- Outdated branches
- Large pending changelist
- Multiple pending stories

---

## Integration Points

### With Your Workflow

The auto-activation integrates at these points:

```
Session Start
    ↓
detect context → show greeting → suggest squad
    ↓
User activates squad
    ↓
Work in squad
    ↓
Exit squad
    ↓
show summary → suggest next steps → ask for commit
    ↓
Continue or switch squads
```

### With Git

Detects:
- Branch name and type
- Uncommitted changes
- Commits ahead of main
- File modifications

### With Stories

Monitors:
- Active stories
- Task completion %
- Blockers
- Story status

### With Tests

Checks:
- Coverage %
- Test pass/fail
- Coverage trends
- Performance

---

## Example Workflows

### Complete Day Workflow

**Morning Start:**
```bash
# 8:00 AM - Start day
cd bidiq
# System shows: Backend development, story in progress

# Activate squad
/bidiq backend

# Continue work
@dev: *develop
# ... coding ...

# Check progress
/bidiq status  # (coming Week 2)
# Shows: 3 uncommitted, coverage 96%, 5 tests passing
```

**Before Lunch:**
```bash
# Need to run tests
/bidiq backend
@qa: *run-tests
# Coverage: 96% ✅ All tests passing ✅

# Commit work
git add .
git commit -m "feat(pncp): pagination support"

# System shows:
# ✅ Ready for PR
# /bidiq feature  (to create PR)
```

**After Lunch:**
```bash
# Switch to frontend work
cd frontend
# System detects: Frontend development

/bidiq frontend
@dev: *develop
# ... UI work ...

# Work on new story
/bidiq feature
@pm: *create-story
# ... story creation ...
```

---

## Tips & Tricks

### Fast Squad Activation

If detection doesn't trigger:
```bash
# Quick manual activation
/bidiq backend
/bidiq frontend
/bidiq feature
```

### See Your Context

```bash
# Understand why squad was suggested
node .aios-core/development/scripts/bidiq-greeting-system.js

# Get full project analysis
node .aios-core/development/scripts/bidiq-context-detector.js
```

### Monitor Progress

```bash
# Check real-time status (coming Week 2)
/bidiq status

# See test coverage
pytest --cov              # Backend
npm test --coverage       # Frontend
```

### Custom Suggestions

Edit `.aios-core/development/configs/bidiq-activation-config.yaml` to customize detection rules for your workflow.

---

## Troubleshooting

### Squad Not Activating Automatically?

**Check:**
1. Are you in a Descomplicita project? (CLAUDE.md should exist)
2. Is `activation.enabled: true` in bidiq-activation-config.yaml?
3. Is confidence ≥ 40%?

**Fix:**
```bash
# See what's detected
node .aios-core/development/scripts/bidiq-greeting-system.js

# Manually activate if needed
/bidiq [backend|frontend|feature]
```

### Suggestions Not Appearing?

**Check:**
1. Is `greeting.show_recommendations: true`?
2. Is context detection enabled?

**Fix:**
```bash
# See analysis
node .aios-core/development/scripts/bidiq-context-detector.js

# Re-run greeting
node .aios-core/development/scripts/bidiq-greeting-system.js
```

### Wrong Squad Suggested?

The system uses multiple signals. To improve accuracy:

1. **Use descriptive branch names:** `feature/pncp-pagination`
2. **Work in correct directory:** `backend/` for Python code
3. **Keep one story active:** Prevents confusion
4. **Commit frequently:** Makes file status clearer

---

## What's Coming

### Phase 2 (Week 2)
- `bidiq-context-aware-hints.js` - Real-time tips based on context
- `bidiq-progress-monitor.js` - Track story velocity
- Integration with `/bidiq status` command

### Phase 3 (Week 3)
- Slack/email notifications for blockers
- Weekly progress reports
- Squad recommendation improvements

### Phase 4 (Week 4)
- ML-based context prediction
- Personalized workflow optimization
- Integration with GitHub Actions

---

## Summary

You never need to remember which command to type. The system:

✅ **Automatically detects** your context
✅ **Proactively suggests** the right squad
✅ **Guides every step** with clear next actions
✅ **Monitors progress** continuously
✅ **Alerts on issues** before they block work

**Result:** Focus on coding, not on managing commands.

---

**For Questions:**
- Check detection: `node .aios-core/development/scripts/bidiq-greeting-system.js`
- See full analysis: `node .aios-core/development/scripts/bidiq-context-detector.js`
- Manual activation: `/bidiq [backend|frontend|feature]`

**Status:** ✅ Ready to use
**Date:** 2026-01-26
