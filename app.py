"""Streamlit war room UI — Hour 3:00 milestone.

Run with:
    .venv/bin/streamlit run app.py

Auth: uses Claude Code session, no API key needed.
"""

import re

import anyio
import streamlit as st
from claude_agent_sdk import (
    query,
    ClaudeAgentOptions,
    AssistantMessage,
    TextBlock,
)

from war_room.agents import AGENTS
from war_room.tools import (
    parse_tool_calls,
    run_tool,
    reset_world,
    is_mutating,
    WORLD,
)

MODEL = "claude-haiku-4-5-20251001"
MAX_TURNS = 12

# ────────────────────────────────────────────────────────────────────────
# INTEGRATION POINT: incident intake
#
# Today this is a hardcoded string for demo reliability. In production,
# replace with whatever feeds your on-call:
#   - Prometheus Alertmanager webhook (parse the JSON payload)
#   - Sensu / Nagios alert-handler script (stdin/exec output)
#   - Canonical Pro support: new-ticket webhook with attached sosreport
#   - PagerDuty / Opsgenie pager event
# The war room is intake-agnostic — anything that produces an incident
# description string works. Keep the rest of this module unchanged.
# ────────────────────────────────────────────────────────────────────────
INITIAL_ALERT = """[INCIDENT 14:03 UTC]
ALERT: vm-web-01 nginx reload failed.
vm-web-02 and vm-web-03 reloaded cleanly 1 minute earlier.
The config-update task that ran 14 minutes ago was authored by deploy-agent (an AI coding agent on the infra team).
You are the war room. Diagnose and remediate."""


# -------------------------------------------------------------------------
# Agent call (same logic as cli.py, lifted so the UI can stay sync-flavored)
# -------------------------------------------------------------------------


async def call_agent_async(agent_key: str, transcript: str) -> str:
    agent = AGENTS[agent_key]
    options = ClaudeAgentOptions(
        system_prompt=agent["system_prompt"],
        model=MODEL,
        setting_sources=[],
        allowed_tools=[],
    )
    full_text = ""
    async for msg in query(prompt=transcript, options=options):
        if isinstance(msg, AssistantMessage):
            for block in msg.content:
                if isinstance(block, TextBlock):
                    full_text += block.text
    return full_text.strip()


def call_agent(agent_key: str, transcript: str) -> str:
    return anyio.run(call_agent_async, agent_key, transcript)


# -------------------------------------------------------------------------
# Directive parsing (mirrors cli.py)
# -------------------------------------------------------------------------


_DIRECTIVE_RE = re.compile(r"^>>.*$", re.MULTILINE)


def parse_handoff(text: str) -> tuple[str, str | None]:
    for line in reversed(text.strip().splitlines()):
        line = line.strip()
        if line.startswith(">>END"):
            return ("end", None)
        if line.startswith(">>NEXT:"):
            return ("next", line.split(":", 1)[1].strip().lower())
    return ("next", "decider")


def strip_directives(text: str) -> str:
    return _DIRECTIVE_RE.sub("", text).strip()


# -------------------------------------------------------------------------
# Streamlit page
# -------------------------------------------------------------------------


st.set_page_config(
    page_title="War Room — AI Incident Commander",
    page_icon="🚨",
    layout="wide",
)

st.title("🚨 AI Incident Commander — War Room")
st.caption(
    "Three AI agents coordinate on an infrastructure incident "
    "caused by *another* AI's bad config push. "
    "**Simulated Multipass environment** for demo reliability."
)


# Initialize session state
def _init_state():
    st.session_state.setdefault("messages", [])  # list of {kind, role, body, cmd?}
    st.session_state.setdefault("transcript", "")
    st.session_state.setdefault("active", "decider")
    st.session_state.setdefault("running", False)
    st.session_state.setdefault("resolved", False)
    st.session_state.setdefault("turn", 0)
    st.session_state.setdefault("post_mortem", None)
    # Approval gate state — set when execution pauses for human input
    st.session_state.setdefault("pending_approval", None)


_init_state()


# ---- Sidebar: incident + controls ---------------------------------------

with st.sidebar:
    st.markdown("### The incident")
    st.error(INITIAL_ALERT, icon="🚨")

    st.markdown("### The war room")
    for agent in AGENTS.values():
        st.markdown(f"{agent['avatar']} **{agent['name']}**")

    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        start_clicked = st.button(
            "🚀 Start",
            disabled=st.session_state.running or st.session_state.resolved,
            use_container_width=True,
        )
    with col2:
        reset_clicked = st.button("↺ Reset", use_container_width=True)

    if reset_clicked:
        reset_world()
        st.session_state.messages = []
        st.session_state.transcript = ""
        st.session_state.active = "decider"
        st.session_state.running = False
        st.session_state.resolved = False
        st.session_state.turn = 0
        st.session_state.post_mortem = None
        st.session_state.pending_approval = None
        st.rerun()

    if start_clicked:
        reset_world()
        st.session_state.messages = []
        st.session_state.transcript = INITIAL_ALERT
        st.session_state.active = "decider"
        st.session_state.running = True
        st.session_state.resolved = False
        st.session_state.turn = 0
        st.session_state.post_mortem = None
        st.session_state.pending_approval = None
        st.rerun()

    # --- Fleet observability ------------------------------------------------
    # Lead indicators that would have flagged the AI-authored push before the
    # war room ever opened. These are the metrics a human would watch if they
    # took "AI agents are pushing config to my fleet" seriously.
    st.markdown("---")
    st.markdown("### 📊 Fleet status")

    incident_started = bool(st.session_state.transcript)
    fleet_healthy = WORLD.vm_web_01_reverted

    if not incident_started:
        capacity_value = "3 / 3"
        capacity_delta = "baseline"
        ai_pending = "0"
        ai_pending_delta = None
        last_check = "13:48 UTC"
        last_check_delta = "1 min ago"
    elif not fleet_healthy:
        capacity_value = "2 / 3"
        capacity_delta = "−1 since 14:03"
        ai_pending = "1"
        ai_pending_delta = "deploy-agent / 9f3a221"
        last_check = "13:48 UTC"
        last_check_delta = "stale — 14m"
    else:
        capacity_value = "3 / 3"
        capacity_delta = "recovered"
        ai_pending = "0"
        ai_pending_delta = "cleared post-revert"
        last_check = "14:04 UTC"
        last_check_delta = "fresh"

    st.metric(
        "Fleet capacity",
        capacity_value,
        delta=capacity_delta,
        delta_color="inverse" if incident_started and not fleet_healthy else "normal",
    )
    st.metric(
        "AI commits unvalidated",
        ai_pending,
        delta=ai_pending_delta,
        delta_color="inverse",
    )
    st.metric(
        "Last fleet-wide nginx -t pass",
        last_check,
        delta=last_check_delta,
        delta_color="inverse" if "stale" in last_check_delta else "normal",
    )

    st.caption(
        "These are lead indicators — a human watching this dashboard "
        "would have caught the bad push at 13:49 UTC, 14 minutes before "
        "the reload-failure alert fired."
    )


# ---- Main: render past messages -----------------------------------------

# Show the alert as the first system message
if st.session_state.transcript or st.session_state.messages:
    with st.chat_message("alert", avatar="🚨"):
        st.code(INITIAL_ALERT, language="text")


for msg in st.session_state.messages:
    if msg["kind"] == "agent":
        agent = AGENTS[msg["role"]]
        with st.chat_message(agent["name"], avatar=agent["avatar"]):
            st.markdown(f"**{agent['name']}**")
            st.markdown(msg["body"])
    elif msg["kind"] == "tool":
        with st.chat_message("tool", avatar="🛠"):
            st.code(f"$ {msg['cmd']}\n\n{msg['output']}", language="text")
    elif msg["kind"] == "approval":
        with st.chat_message("approval", avatar="🛡"):
            st.markdown(f"**Human approval** — `{msg['cmd']}`")
            st.markdown(f"*Decision: **{msg['decision']}***")


# ---- Run one turn per rerun (driven by st.session_state.running) --------

# ---- Approval gate (rendered when execution is paused for human input) --

# ────────────────────────────────────────────────────────────────────────
# INTEGRATION POINT: human approval gate
#
# The Slack-style card below renders inline so the demo is self-contained.
# In production, replace the render-and-block with an async send-and-wait:
#   - Slack:     slack_sdk.WebClient().chat_postMessage(channel=oncall,
#                blocks=...) + interactivity webhook that resolves the
#                pending_approval state when the on-call clicks a button
#   - PagerDuty: create incident + custom action; poll for ack
#   - Internal portal: enqueue the approval, await operator decision
#   - Email (low-volume): one-click signed approval link
# The state machine (pending_approval, remaining_tools, agent_text) stays
# the same regardless of transport — only the I/O changes.
# ────────────────────────────────────────────────────────────────────────
if st.session_state.pending_approval is not None:
    approval = st.session_state.pending_approval

    with st.chat_message("approval", avatar="🛡"):
        st.caption(
            "↓ In production this would be a Slack DM to the on-call engineer. "
            "Demo renders it inline."
        )

        # Slack-style notification card
        st.markdown(
            """
            <div style='
                background:#ffffff;
                border:1px solid #e1e5eb;
                border-left:4px solid #4a154b;
                border-radius:6px;
                padding:14px 18px;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
                box-shadow: 0 1px 2px rgba(0,0,0,0.05);
                margin-bottom: 0.5rem;
            '>
              <div style='display:flex; align-items:center; gap:8px; margin-bottom:8px;'>
                <span style='
                    background:#4a154b; color:white;
                    width:28px; height:28px; border-radius:4px;
                    display:inline-flex; align-items:center; justify-content:center;
                    font-size:14px;
                '>🛡</span>
                <strong style='color:#1d1c1d;'>war-room-bot</strong>
                <span style='background:#dddee0; color:#616061; font-size:9px; font-weight:700;
                             padding:1px 4px; border-radius:2px; letter-spacing:0.5px;'>APP</span>
                <span style='color:#616061; font-size:12px;'>just now · #ops-oncall</span>
              </div>
              <div style='color:#1d1c1d; line-height:1.5; font-size:14px;'>
                <div style='font-weight:700; margin-bottom:6px;'>🚨 Approval required — production change</div>
                <div style='margin-bottom:10px;'>
                  vm-web-01 has been failing nginx reloads since 14:03 UTC.
                  Root cause identified: a config push from <code>deploy-agent</code>.
                  The war room proposes:
                </div>
                <div style='background:#f4f4f5; border-left:3px solid #4a154b;
                            padding:8px 12px; font-family: ui-monospace, SFMono-Regular, monospace;
                            font-size:13px; margin-bottom:10px; color:#1d1c1d;'>
                  $ """
            + approval["cmd"]
            + """
                </div>
                <div style='color:#616061; font-size:12px;'>
                  Posted by war-room-bot · Click an action below to respond.
                </div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        col1, col2, col3 = st.columns(3)

        if col1.button("✅ Approve", use_container_width=True, type="primary"):
            cmd = approval["cmd"]
            output = run_tool(cmd)
            st.session_state.messages.append(
                {"kind": "approval", "cmd": cmd, "decision": "approved"}
            )
            st.session_state.messages.append(
                {"kind": "tool", "cmd": cmd, "output": output}
            )
            st.session_state.transcript += (
                f"\n\n[HUMAN]: APPROVED `{cmd}`"
                f"\n[TOOL OUTPUT for `{cmd}`]\n{output}"
            )
            # Continue with the remaining tools from that same turn, then handoff
            for remaining in approval["remaining_tools"]:
                if is_mutating(remaining):
                    st.session_state.pending_approval = {
                        "cmd": remaining,
                        "remaining_tools": [],  # for demo simplicity
                        "agent_text": approval["agent_text"],
                    }
                    st.rerun()
                rem_output = run_tool(remaining)
                st.session_state.messages.append(
                    {"kind": "tool", "cmd": remaining, "output": rem_output}
                )
                st.session_state.transcript += (
                    f"\n\n[TOOL OUTPUT for `{remaining}`]\n{rem_output}"
                )
            kind, payload = parse_handoff(approval["agent_text"])
            st.session_state.pending_approval = None
            if kind == "end":
                st.session_state.running = False
                st.session_state.resolved = True
                st.session_state.post_mortem = strip_directives(approval["agent_text"])
            elif payload in AGENTS:
                st.session_state.active = payload
                st.session_state.turn += 1
            st.rerun()

        if col2.button("✏️ Different action", use_container_width=True):
            st.session_state.messages.append(
                {"kind": "approval", "cmd": approval["cmd"], "decision": "rejected"}
            )
            st.session_state.transcript += (
                f"\n\n[HUMAN]: REJECTED `{approval['cmd']}`. "
                f"Decider, propose a different action."
            )
            st.session_state.active = "decider"
            st.session_state.turn += 1
            st.session_state.pending_approval = None
            st.rerun()

        if col3.button("⏸ Hold (page on-call)", use_container_width=True):
            st.session_state.messages.append(
                {"kind": "approval", "cmd": approval["cmd"], "decision": "held"}
            )
            st.session_state.transcript += (
                f"\n\n[HUMAN]: HOLD on `{approval['cmd']}`. Paging on-call."
            )
            st.session_state.running = False
            st.session_state.pending_approval = None
            st.rerun()


# ---- Turn loop ----------------------------------------------------------

elif st.session_state.running and not st.session_state.resolved:
    if st.session_state.turn >= MAX_TURNS:
        st.session_state.running = False
        with st.chat_message("system", avatar="⏱"):
            st.warning(f"Max turns ({MAX_TURNS}) reached without resolution.")
    else:
        active = st.session_state.active
        agent = AGENTS[active]

        with st.chat_message(agent["name"], avatar=agent["avatar"]):
            st.markdown(f"**{agent['name']}**")
            with st.spinner(f"{agent['name']} is thinking..."):
                text = call_agent(active, st.session_state.transcript)
            body = strip_directives(text)
            st.markdown(body)

        st.session_state.messages.append(
            {"kind": "agent", "role": active, "body": body}
        )
        st.session_state.transcript += f"\n\n[{agent['name']}]: {text}"

        # Execute tools, pausing at the FIRST mutating one for human approval
        tool_calls = parse_tool_calls(text)
        gated = False
        for i, tool_line in enumerate(tool_calls):
            if is_mutating(tool_line):
                st.session_state.pending_approval = {
                    "cmd": tool_line,
                    "remaining_tools": tool_calls[i + 1:],
                    "agent_text": text,
                }
                gated = True
                st.rerun()
                break
            output = run_tool(tool_line)
            with st.chat_message("tool", avatar="🛠"):
                st.code(f"$ {tool_line}\n\n{output}", language="text")
            st.session_state.messages.append(
                {"kind": "tool", "cmd": tool_line, "output": output}
            )
            st.session_state.transcript += (
                f"\n\n[TOOL OUTPUT for `{tool_line}`]\n{output}"
            )

        if not gated:
            # Handoff
            kind, payload = parse_handoff(text)
            if kind == "end":
                st.session_state.running = False
                st.session_state.resolved = True
                st.session_state.post_mortem = body
            elif payload in AGENTS:
                st.session_state.active = payload
                st.session_state.turn += 1
                st.rerun()
            else:
                st.session_state.running = False
                st.error(f"Unknown handoff target: {payload!r}")


# ---- Post-mortem panel (shown after resolution) -------------------------

if st.session_state.resolved and st.session_state.post_mortem:
    st.markdown("---")
    st.success("✅ Incident resolved. Post-mortem generated.")

    rendered_tab, raw_tab = st.tabs(["📋 Rendered", "📝 Markdown source"])

    with rendered_tab:
        # Wrap in a styled container so it visually reads as a document.
        st.markdown(
            "<div style='background-color:#fffbea; border-left:4px solid #d97706; "
            "padding: 1rem 1.5rem; border-radius:6px;'>",
            unsafe_allow_html=True,
        )
        st.markdown(st.session_state.post_mortem)
        st.markdown("</div>", unsafe_allow_html=True)

    with raw_tab:
        st.code(st.session_state.post_mortem, language="markdown")

    st.download_button(
        "📄 Download post-mortem.md",
        data=st.session_state.post_mortem,
        file_name="post-mortem.md",
        mime="text/markdown",
    )
