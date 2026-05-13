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

# Add your Anthropic API key
cp .env.example .env
# Edit .env and paste your key (sk-ant-...)

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

- **Anthropic Claude API** — for agent reasoning and persona voicing
- **Streamlit** — `st.chat_message` per agent, color-coded
- **Python** — orchestration via a small handoff loop (~80 lines, no framework)
- **Mocked Multipass** — fake `multipass exec` tool outputs for demo reliability

No dependency on Swarm or other multi-agent frameworks. The orchestration is a transparent text protocol (`>>NEXT: <agent>` / `>>END`) you can read in 30 seconds.

## Why this matters

Teams at this hackathon are already running AI coding agents inside Multipass VMs. When one of those agents ships a bad change, the human on-call inherits the problem. This is a near-future scenario for a user population that exists today.

If your AI agent is running in Multipass right now, this is your next outage.

## Design

Full design doc: [`concepts/ubuntu-main-design-20260513-112551.md`](concepts/ubuntu-main-design-20260513-112551.md)

Includes problem statement, premises, approaches considered, 60-second demo arc, and the 5-hour build timeline.
