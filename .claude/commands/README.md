# Claude Code Commands - AIOS Agent System

**Project:** Descomplicita (PNCP POC v0.2)
**Framework:** Synkra AIOS v2.0
**Setup Status:** ✅ Complete & Validated

## What is This?

This directory contains **command files** that activate specialized AI agents to help you with different aspects of development.

Think of it as a **team of experts** that you can call upon:
- **Developer** for writing code
- **QA Engineer** for testing
- **Architect** for design decisions
- **Product Owner** for backlog management
- ... and 8 more specialized roles

## Quick Start

### 1. Type a Command
```
/dev
```

### 2. Agent Activates
You see a greeting from the Full Stack Developer agent (James), ready to help you code.

### 3. Use Agent Commands
```
*develop              → Implement a story
*run-tests           → Run tests
*help                → See all commands
```

### 4. Switch Agents
```
/qa                  → Switch to QA agent
/AIOS               → Return to master selector
```

## Available Agents

### 👨‍💻 Development
- **`/dev`** - Full Stack Developer (write code, fix bugs, refactor)
- **`/qa`** - QA Engineer (test code, validate quality)
- **`/architect`** - System Architect (design decisions, technical guidance)
- **`/analyst`** - Business Analyst (requirements, research)

### 📊 Product & Project
- **`/pm`** - Engineering Manager (project planning, resource allocation)
- **`/po`** - Product Owner (backlog, story refinement)
- **`/sm`** - Scrum Master (ceremonies, team facilitation)

### 🔧 Specialized
- **`/data-engineer`** - Database Architect (schemas, migrations, optimization)
- **`/devops`** - GitHub DevOps Manager (push code, create PRs, CI/CD)
- **`/squad-creator`** - Multi-Agent Team Creator (assemble agent squads)
- **`/ux-design-expert`** - UX Designer (wireframes, user research)

### 👑 Master
- **`/AIOS`** - Master Orchestrator (access all agents, full framework)
- **`/aios-master`** - Same as `/AIOS` (alternative command)

## File Structure

```
.claude/commands/
├── README.md                     ← You are here
├── INDEX.md                      ← Complete reference
├── SETUP-VALIDATION.md           ← Setup confirmation
│
├── AIOS.md                       ← Master hub command
├── aios-master.md               ← Master orchestrator command
│
├── dev.md                       ← Developer command
├── qa.md                        ← QA command
├── architect.md                 ← Architect command
├── analyst.md                   ← Analyst command
├── pm.md                        ← Project Manager command
├── po.md                        ← Product Owner command
├── sm.md                        ← Scrum Master command
├── data-engineer.md             ← Data Engineer command
├── devops.md                    ← DevOps command
├── squad-creator.md             ← Squad Creator command
├── ux-design-expert.md          ← UX Designer command
│
├── review-pr.md                 ← Governance: PR automation
├── audit-roadmap.md             ← Governance: Roadmap audit
├── pick-next-issue.md           ← Governance: Issue selection
│
└── AIOS/
    └── agents/                  ← Complete agent definitions
        ├── _README.md
        ├── dev.md               ← Full Dev agent config
        ├── qa.md                ← Full QA agent config
        ├── architect.md         ← Full Architect config
        ├── ... (8 more agents)
        └── aios-master.md       ← Full Master config
```

## How It Works

```
┌─────────────────┐
│  User Types     │
│   /dev          │
└────────┬────────┘
         │
         ▼
┌──────────────────────────┐
│  .claude/commands/dev.md │  ← Quick reference file
│  (explanation & help)    │     Shows what /dev does
└────────┬─────────────────┘
         │
         ▼
┌──────────────────────────────────────┐
│ .claude/commands/AIOS/agents/dev.md  │  ← Full agent definition
│ (complete YAML configuration)        │     Complete persona & commands
└────────┬──────────────────────────────┘
         │
         ▼
┌──────────────────────────┐
│ Dev Agent Activates      │
│                          │
│ Name: Dex (Builder)      │
│ Commands: *develop       │
│           *run-tests     │
│           etc...         │
│                          │
│ Awaits your commands...  │
└──────────────────────────┘
```

## Command Types

### Activation Commands (Start an Agent)
```
/dev              → Activate Developer
/qa               → Activate QA
/architect        → Activate Architect
... etc ...
/AIOS             → Activate Master
```

### Agent Commands (Use Within Agent)
Once an agent is active, use commands with `*` prefix:
```
*help             → Show all available commands
*develop          → (Dev agent) Implement story
*run-tests        → (QA agent) Execute tests
*analyze-impact   → (Architect) Assess design impact
*exit             → Leave current agent
```

## When to Use Each Agent

| Need | Use Agent |
|------|-----------|
| "Write this feature" | `/dev` |
| "Test this code" | `/qa` |
| "How should this be designed?" | `/architect` |
| "What are the requirements?" | `/analyst` |
| "Plan the sprint" | `/pm` |
| "Manage the backlog" | `/po` |
| "Run a retrospective" | `/sm` |
| "Design the database" | `/data-engineer` |
| "Push this to GitHub" | `/devops` |
| "Create UX wireframes" | `/ux-design-expert` |
| "Assemble a team" | `/squad-creator` |
| "Do everything" | `/AIOS` |

## Example Workflows

### Implement a Feature (Multi-Agent)

1. Create the story:
   ```
   /pm
   *create-story
   ```

2. Implement:
   ```
   /dev
   *develop story-1.2.3
   ```

3. Test:
   ```
   /qa
   *run-tests
   ```

4. Push to GitHub:
   ```
   /devops
   *push-changes
   ```

### Database Migration

1. Design schema:
   ```
   /data-engineer
   *db-domain-modeling
   ```

2. Apply migration:
   ```
   /data-engineer
   *db-apply-migration
   ```

3. Test it:
   ```
   /qa
   *run-tests
   ```

### UX Design to Implementation

1. Research users:
   ```
   /ux-design-expert
   *user-research
   ```

2. Create wireframes:
   ```
   /ux-design-expert
   *create-wireframe
   ```

3. Build component:
   ```
   /dev
   *build-component
   ```

## Configuration & Documentation

| File | Purpose |
|------|---------|
| `README.md` | This file - overview |
| `INDEX.md` | Complete command-agent reference |
| `SETUP-VALIDATION.md` | Setup completion verification |
| `AIOS/agents/_README.md` | Agent system documentation |
| `.claude/CLAUDE.md` | Development rules & guidelines |
| `.aios-core/user-guide.md` | Full AIOS framework guide |

## Common Questions

### Q: How do I see all available commands for an agent?
**A:** Activate the agent, then type `*help`

Example:
```
/dev
*help
```

### Q: How do I switch agents?
**A:** Type `/AIOS` to go to master, then type the agent you want.
Or type a command directly: `/qa`

### Q: What if I don't know which agent to use?
**A:** Type `/AIOS` to see the master hub with descriptions of all agents.

### Q: Can I use multiple agents for one task?
**A:** Yes! That's the point. Different experts collaborate. Example: `/dev` writes code, then `/qa` tests it, then `/devops` pushes it.

### Q: Where are the actual agent definitions?
**A:** In `.claude/commands/AIOS/agents/` directory. These contain the complete YAML configuration for each agent.

### Q: What if an agent command doesn't work?
**A:**
1. Make sure agent is activated (you see their greeting)
2. Use `*` prefix for agent commands: `*help` not `help`
3. Type `*help` to see available commands for that agent
4. Check `.claude/commands/AIOS/agents/{agent-id}.md` for details

### Q: Can I customize an agent?
**A:** Yes! Edit `.claude/commands/AIOS/agents/{agent-id}.md` to customize persona, commands, or behavior.

## Setup Verification

All commands are properly configured and tested:

```
✅ 12 Agent Commands ........... Fully linked
✅ 3 Governance Commands ....... Available
✅ Complete Documentation ...... Present
✅ Framework Integration ....... Verified
✅ Setup Validation ............ Complete
```

See `SETUP-VALIDATION.md` for detailed verification.

## Next Steps

1. **Try it out:**
   ```
   /dev
   *help
   ```

2. **Read the framework guide:**
   See `.aios-core/user-guide.md` for complete AIOS documentation

3. **Work on a story:**
   ```
   /sm
   *create-next-story
   ```

4. **Reference:**
   - `INDEX.md` for complete command reference
   - `.aios-core/development/tasks/` for available tasks (115+)
   - `.aios-core/development/workflows/` for workflows (7)

## Structure at a Glance

```
Commands: /dev, /qa, /architect, ...
    ↓ (Links to)
Agent Definitions: .claude/commands/AIOS/agents/dev.md, etc.
    ↓ (Contains)
YAML Config: Persona, Commands, Tools, Dependencies
    ↓ (Access to)
Framework Resources: Tasks, Templates, Checklists, Workflows
    ↓ (Enable)
Agent Actions: *develop, *run-tests, *create-story, etc.
```

---

**Ready?** Type `/dev` to get started!

For complete documentation, see:
- `INDEX.md` - Command reference
- `SETUP-VALIDATION.md` - Setup status
- `.aios-core/user-guide.md` - Full framework guide
- `CLAUDE.md` - Development rules

**Questions?** See `.claude/commands/AIOS/agents/_README.md` for agent system details.
