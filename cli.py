"""Terminal entry point — Hour 0:30 milestone.

Runs the war room loop in stdout so we can verify agents have distinct
voices before building the Streamlit UI.

Usage:
    .venv/bin/python cli.py
"""

import os
import re
import sys

from dotenv import load_dotenv
from anthropic import Anthropic

from war_room.agents import AGENTS

load_dotenv()

if not os.getenv("ANTHROPIC_API_KEY"):
    sys.exit("ANTHROPIC_API_KEY not set. Add it to .env and try again.")

client = Anthropic()
MODEL = "claude-sonnet-4-6"
MAX_TURNS = 12

INITIAL_ALERT = """ALERT: vm-web-01 nginx reload failed at 14:03 UTC.
Two other VMs in the fleet (vm-web-02, vm-web-03) reloaded successfully.
The config-update task that ran 14 minutes ago was authored by deploy-agent (an AI coding agent).
You are the war room. Diagnose and remediate."""


def call_agent(agent_key: str, history: list[dict]) -> str:
    """Call the named agent with the shared conversation history."""
    agent = AGENTS[agent_key]
    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=agent["system_prompt"],
        messages=history,
    )
    return response.content[0].text


def parse_directive(text: str) -> tuple[str, str | None]:
    """Pull the >>NEXT or >>END directive from the agent's last line.

    Returns (kind, payload) where kind is 'next' or 'end' and payload is
    the next agent key (or None for end).
    """
    for line in reversed(text.strip().splitlines()):
        line = line.strip()
        if line.startswith(">>END"):
            return ("end", None)
        if line.startswith(">>NEXT:"):
            return ("next", line.split(":", 1)[1].strip().lower())
    return ("next", "decider")  # fallback: hand back to Decider


def format_turn(agent_key: str, text: str) -> str:
    """Pretty-print an agent turn for the terminal."""
    agent = AGENTS[agent_key]
    header = f"\n{agent['avatar']}  {agent['name'].upper()}"
    body = re.sub(r"^>>.*$", "", text, flags=re.MULTILINE).strip()
    return f"{header}\n{'-' * 40}\n{body}\n"


def main():
    print("=" * 60)
    print("AI INCIDENT COMMANDER — WAR ROOM (simulated environment)")
    print("=" * 60)
    print(INITIAL_ALERT)
    print("=" * 60)

    history = [{"role": "user", "content": INITIAL_ALERT}]
    active = "decider"

    for turn in range(MAX_TURNS):
        text = call_agent(active, history)
        print(format_turn(active, text))
        history.append({"role": "assistant", "content": text})
        # Anthropic API wants alternating user/assistant. We append a user
        # echo so the next agent sees the running transcript as the user side.
        history.append(
            {"role": "user", "content": f"[War room transcript continues. Next speaker:]"}
        )

        kind, payload = parse_directive(text)
        if kind == "end":
            print("\n" + "=" * 60)
            print("INCIDENT RESOLVED.")
            print("=" * 60)
            return
        if payload not in AGENTS:
            print(f"\n[orchestrator] Unknown handoff target '{payload}', ending.")
            return
        active = payload

    print(f"\n[orchestrator] Max turns ({MAX_TURNS}) reached without resolution.")


if __name__ == "__main__":
    main()
