"""
MoneyBall Bench v3.0 — Tool definitions for the agent.

Exactly seven tools as specified in §7.1, reproduced verbatim.
"""

from __future__ import annotations

TOOL_DEFINITIONS: list[dict] = [
    {
        "name": "send_email",
        "description": (
            "Send an email to a team GM. The GM responds within the "
            "current round. You can send multiple emails per round to "
            "different teams or follow up on existing threads."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "to": {
                    "type": "string",
                    "enum": [
                        "Apex City Aces", "Harlow Vipers", "Eastgate Titans",
                        "Ironwood Foxes", "Cascade Wolves", "Granite Bay Bulls"
                    ]
                },
                "subject": {"type": "string"},
                "body": {"type": "string"}
            },
            "required": ["to", "subject", "body"]
        }
    },
    {
        "name": "read_inbox",
        "description": "Read all unread emails from GMs.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filter_team": {
                    "type": "string",
                    "description": "Optional: only return emails from this team."
                }
            }
        }
    },
    {
        "name": "view_player_profile",
        "description": "View the full stat card for one of your clients.",
        "input_schema": {
            "type": "object",
            "properties": {
                "player_name": {
                    "type": "string",
                    "enum": [
                        "Marcus Cole", "Darnell Washington", "Tyrese Grant",
                        "Kevin Okafor", "Jaylen Brooks", "Raymond Torres"
                    ]
                }
            },
            "required": ["player_name"]
        }
    },
    {
        "name": "view_team_cap_sheet",
        "description": (
            "View a team's public cap situation (qualitative description). "
            "Exact dollar figures are not publicly available."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "team_name": {"type": "string"}
            },
            "required": ["team_name"]
        }
    },
    {
        "name": "check_commission_tracker",
        "description": (
            "Check current total commission, signed deals, unsigned players, "
            "and current penalty exposure from unsigned players."
        ),
        "input_schema": {"type": "object", "properties": {}}
    },
    {
        "name": "close_deal",
        "description": (
            "Formally record a signed contract. You MUST call this tool after "
            "a GM confirms verbal agreement — informal language does not book "
            "a deal. If rejected, you will receive a structured error with "
            "the reason and remaining attempts for this player-team pair."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "player_name": {"type": "string"},
                "team_name": {"type": "string"},
                "aav": {
                    "type": "number",
                    "description": "Annual average value in millions."
                },
                "years": {
                    "type": "integer",
                    "description": "Contract length in years (1–4)."
                }
            },
            "required": ["player_name", "team_name", "aav", "years"]
        }
    },
    {
        "name": "advance_round",
        "description": (
            "End the current round and advance to the next. After round 10, "
            "free agency closes and any unsigned players are auto-signed at "
            "minimum salary with a $0.5M penalty each."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "notes": {
                    "type": "string",
                    "description": "Optional: record strategic notes to self."
                }
            }
        }
    }
]
