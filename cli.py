"""Terminal entry point for the war room.

Uses the Claude Agent SDK (Claude Code auth, no API key). Orchestrates
three agents via a text protocol parsed from each agent's response:

    >>TOOL: multipass exec vm-web-01 -- journalctl -u nginx -n 20
    >>NEXT: paranoid
    >>END

Usage:
    .venv/bin/python cli.py
"""

import re

import anyio
from claude_agent_sdk import (
    query,
    ClaudeAgentOptions,
    AssistantMessage,
    TextBlock,
)

from war_room.agents import AGENTS
from war_room.tools import parse_tool_calls, run_tool, reset_world

MODEL = "claude-haiku-4-5-20251001"
MAX_TURNS = 15

INITIAL_ALERT = """[INCIDENT 14:03 UTC]
ALERT: vm-web-01 nginx reload failed.
vm-web-02 and vm-web-03 reloaded cleanly 1 minute earlier.
The config-update task that ran 14 minutes ago was authored by deploy-agent (an AI coding agent on the infra team).
You are the war room. Diagnose and remediate."""


async def call_agent(agent_key: str, transcript: str) -> str:
    """Run one agent turn. Returns the agent's response text."""
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


def parse_handoff(text: str) -> tuple[str, str | None]:
    """Pull the >>NEXT or >>END directive from the LAST line."""
    for line in reversed(text.strip().splitlines()):
        line = line.strip()
        if line.startswith(">>END"):
            return ("end", None)
        if line.startswith(">>NEXT:"):
            return ("next", line.split(":", 1)[1].strip().lower())
    return ("next", "decider")


_DIRECTIVE_RE = re.compile(r"^>>.*$", re.MULTILINE)


def format_turn(agent_key: str, text: str) -> str:
    """Strip directives, pretty-print the agent's prose."""
    agent = AGENTS[agent_key]
    body = _DIRECTIVE_RE.sub("", text).strip()
    header = f"\n{agent['avatar']}  {agent['name'].upper()}"
    return f"{header}\n{'-' * 50}\n{body}\n"


def format_tool(cmd: str, output: str) -> str:
    return f"\n   🛠  $ {cmd}\n" + "\n".join(
        "      " + line for line in output.splitlines()
    ) + "\n"


async def main():
    reset_world()
    print("=" * 60)
    print("AI INCIDENT COMMANDER — WAR ROOM (simulated environment)")
    print("=" * 60)
    print(INITIAL_ALERT)
    print("=" * 60)

    transcript = INITIAL_ALERT
    active = "decider"

    for turn in range(MAX_TURNS):
        text = await call_agent(active, transcript)
        print(format_turn(active, text))

        # Append agent's turn to transcript
        transcript += f"\n\n[{AGENTS[active]['name']}]: {text}"

        # If the agent invoked tools, run them and inject results
        tool_calls = parse_tool_calls(text)
        for tool_line in tool_calls:
            output = run_tool(tool_line)
            print(format_tool(tool_line, output))
            transcript += f"\n\n[TOOL OUTPUT for `{tool_line}`]\n{output}"

        kind, payload = parse_handoff(text)
        if kind == "end":
            print("\n" + "=" * 60)
            print("INCIDENT RESOLVED.")
            print("=" * 60)
            return
        if payload not in AGENTS:
            print(f"\n[orchestrator] Unknown handoff target {payload!r}, ending.")
            return
        active = payload

    print(f"\n[orchestrator] Max turns ({MAX_TURNS}) reached without resolution.")


if __name__ == "__main__":
    anyio.run(main)
