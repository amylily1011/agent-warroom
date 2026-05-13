# AI Incident Commander — The War Room

> AI cleans up after AI.

A three-agent war room that diagnoses and remediates an infrastructure incident caused by *another* AI's bad config push. Built for the Canonical AI Ubuntu Hackathon.

## The story

A coding agent updates nginx config across three Multipass VMs. One reload fails because the agent generated an invalid directive. Today, a human on-call scrambles to figure out what the AI did. With this war room, three named agents take it from there:

| Agent | Role | Voice |
|-------|------|-------|
| **Optimist** ⚡ | Fast recovery, common fixes | "Try X first, it's a 5-second test." |
| **Paranoid** 🔍 | Evidence gathering, risk assessment | "Before we touch it, what does the data say?" |
| **Decider** 🎯 | Incident commander, writes the post-mortem | "Optimist: propose a revert. Paranoid: pull the diff." |

The personas are operational roles. Each has a defined function in the response loop.

> The incident is simulated for demo reliability. The behavior is real.

## Quick start

```bash
# Clone and enter
git clone https://github.com/amylily1011/agent-warroom.git
cd agent-warroom

# Set up Python env
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# Auth happens through your existing Claude Code session — no API key needed.
# Just make sure `claude` is installed and you've run it at least once.

# Run the war room in your terminal
.venv/bin/python cli.py

# Later: run the Streamlit UI
.venv/bin/streamlit run app.py
```

## The demo scenario

A `deploy-agent` (AI coding agent) pushed a config update across:

- `vm-web-01` — failed reload (invalid `http2_max_concurrent_streams` directive)
- `vm-web-02` — clean reload
- `vm-web-03` — clean reload

The war room agents:

1. Decider opens the room with the alert
2. Optimist proposes the cheapest action (restart)
3. Paranoid pulls the journal and the config diff
4. They identify the AI-authored bad directive on line 23
5. Decider commits to a revert
6. Decider writes a three-line post-mortem closing with:
   > *"Filed under: AI-authored change, needs review gate."*

## Tech stack

- **Claude Agent SDK** — for agent reasoning and persona voicing (uses your Claude Code auth, no API key)
- **Streamlit** — `st.chat_message` per agent, color-coded
- **Python** — orchestration via a small handoff loop (~80 lines, no framework)
- **Mocked Multipass** — fake `multipass exec` tool outputs for demo reliability

No dependency on Swarm or other multi-agent frameworks. The orchestration is a transparent text protocol (`>>NEXT: <agent>` / `>>END`) you can read in 30 seconds.

## Why this matters

Teams at this hackathon are already running AI coding agents inside Multipass VMs. When one of those agents ships a bad change, the human on-call inherits the problem. This is a near-future scenario for a user population that exists today.

If your AI agent is running in Multipass right now, this is your next outage.

## Design principles

### 1. Human approval gates fire on *irreversibility*, not on every write

A human who rubber-stamps every approval prompt is a bottleneck, not a safety net. The principled gate fires when (a) an action is irreversible (truncating data, dropping tables, severing network reachability), or (b) the agents *disagree*. In this demo, `config-revert` and `systemctl reload` are reversible — we still gate them to keep the audit trail and mirror how on-call should hear about production changes, but the deeper version of this system would not interrupt the war room for reversible actions.

What the human is actually providing: **accountability, context the agents lack, and a kill switch**. Not correctness review.

### 2. Lead indicators belong in the war room

The sidebar shows fleet status — how many VMs are healthy, how many AI-authored commits haven't been validated across the fleet, and when the fleet last passed a config syntax check. A human watching this would have caught the bad push at `13:49 UTC`, 14 minutes before the alert fired. Building these dashboards *around* AI behaviour is the unglamorous half of AI-in-production; the glamorous half is the agents, but the unglamorous half is what prevents the next incident.

### 3. Today: AI cleans up after AI. Tomorrow: AI prevents AI.

The war room currently writes a post-mortem with action items: *"add an `nginx -t` pre-deploy gate", "audit deploy-agent's directive generation", "require human review for AI infra commits."* Those items sit in the post-mortem and rot.

The obvious next loop: the Decider doesn't just *write* action items — it **files the tickets and opens the PR**. A future `>>TOOL: file-ticket` and `>>TOOL: open-pr` would close the response loop into a prevention loop. Same demo, bigger arc.

## Integration points

The war room has three swappable boundaries. The demo mocks all three; a production install replaces each with real infrastructure. Every boundary is named inline in the code — grep for `INTEGRATION POINT` to find them. **A reader should not have to ask where their existing tools plug in.**

### 1. Incident intake — *where does the alert come from?*
- Code: `app.py` near `INITIAL_ALERT`
- Today: hardcoded string for demo reliability
- Swap in:
  - Prometheus Alertmanager webhook
  - Sensu / Nagios alert handler
  - Canonical Pro support: new-ticket webhook with attached sosreport
  - PagerDuty / Opsgenie pager event

### 2. Tool execution — *what actually runs the commands?*
- Code: `war_room/tools.py` near `run_tool()`
- Today: every `multipass exec …` returns a canned mock output
- Swap in:
  - Real `multipass exec …` via `subprocess`
  - Juju: `juju run --unit … …`
  - Ansible ad-hoc: `ansible_runner.run(host=…, module="shell", args=…)`
  - SSH with audit log via `paramiko` / `fabric`

### 3. Human approval gate — *where does on-call get pinged?*
- Code: `app.py` near the Slack-style approval card
- Today: inline Streamlit buttons (Approve / Different action / Hold)
- Swap in:
  - Slack interactive message + interactivity webhook
  - PagerDuty custom action on the incident
  - Internal operator portal with a queue
  - Email with a one-click signed approval link

The agent loop, the `>>TOOL:` / `>>NEXT:` protocol, and the `is_mutating()` gate contract stay identical regardless of which integrations you choose.

## Design doc

Full design doc: [`concepts/ubuntu-main-design-20260513-112551.md`](concepts/ubuntu-main-design-20260513-112551.md)

Includes problem statement, premises, approaches considered, 60-second demo arc, and the 5-hour build timeline.
