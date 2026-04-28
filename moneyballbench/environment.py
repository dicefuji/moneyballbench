"""
MoneyBall Bench v3.0 — Core simulation environment.

Implements the NBASimEnvironment class with all tool methods (§7.3),
Deal dataclass, and internal helpers. GMs hold reservation prices;
the orchestration layer acts as a hard backstop.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Optional

from moneyballbench.config import (
    AUTO_SIGN_PENALTY,
    GRANITE_BAY_NON_INTERIOR,
    MAX_ROUNDS,
    MAX_SALARY,
    PLAYER_FLOORS,
    SALARY_CAP,
    TEAM_COMMITTED_PAYROLL,
)
from moneyballbench.prompts import GM_SYSTEM_PROMPTS, build_gm_system_prompt


@dataclass
class Deal:
    player: str
    team: str
    aav: float
    years: int

    @property
    def total_value(self) -> float:
        return self.aav * self.years

    @property
    def commission(self) -> float:
        return self.total_value * 0.10


class NBASimEnvironment:
    """
    Core simulation environment for MoneyBall Bench v3.
    GMs hold reservation prices; orchestration layer acts as hard backstop.
    """

    def __init__(
        self,
        gm_client,
        gm_model_id: str,
        noised_reservation_prices: dict,
        gm_stack_version: str,
        run_id: int,
    ):
        self.gm_client = gm_client
        self.gm_model_id = gm_model_id
        self.reservation_prices = noised_reservation_prices
        self.gm_stack_version = gm_stack_version
        self.run_id = run_id

        self.current_round = 1
        self.signed_deals: list[Deal] = []
        self.auto_signed: list[str] = []
        self.email_threads: dict[str, list[dict]] = {
            team: [] for team in TEAM_COMMITTED_PAYROLL
        }
        self.inbox: list[dict] = []
        self.rejection_budget: dict[tuple, int] = {}
        self.locked_pairs: set[tuple] = set()
        self.committed_payroll = dict(TEAM_COMMITTED_PAYROLL)

    # ------------------------------------------------------------------ #
    # Tools                                                                #
    # ------------------------------------------------------------------ #

    def tool_send_email(self, to: str, subject: str, body: str) -> dict:
        if to not in self.committed_payroll:
            return {"error": f"Unknown team: {to}"}

        if to == "Granite Bay Bulls":
            body_lower = body.lower()
            for player in GRANITE_BAY_NON_INTERIOR:
                if player.lower() in body_lower:
                    stub = (
                        "Thanks for reaching out. Our focus this offseason "
                        "is exclusively on interior players (PF/C). I can't "
                        "engage on this player — best of luck placing them."
                    )
                    self._deposit_inbox(to, subject, stub)
                    return {"status": "sent", "note": "auto-stubbed (wrong position)"}

        self.email_threads[to].append({"role": "user", "content": body})
        gm_response = self._call_gm(to)
        self._deposit_inbox(to, subject, gm_response)
        return {"status": "sent"}

    def tool_read_inbox(self, filter_team: Optional[str] = None) -> list:
        unread = [e for e in self.inbox if not e["read"]]
        if filter_team:
            unread = [e for e in unread if e["from"] == filter_team]
        for e in unread:
            e["read"] = True
        return unread

    def tool_close_deal(
        self, player_name: str, team_name: str, aav: float, years: int
    ) -> dict:
        pair = (player_name, team_name)

        if pair in self.locked_pairs:
            return {
                "error": (
                    f"{team_name} has withdrawn from negotiations with "
                    f"{player_name} for this season."
                )
            }

        if not isinstance(years, int) or years < 1 or years > 4:
            return {"error": "Contract length must be 1–4 years."}
        if aav > MAX_SALARY:
            return {"error": f"Exceeds league maximum (${MAX_SALARY}M)."}
        if player_name not in PLAYER_FLOORS:
            return {"error": f"Unknown player: {player_name}"}
        if aav < PLAYER_FLOORS[player_name]:
            return {
                "error": (
                    f"Below {player_name}'s floor "
                    f"(${PLAYER_FLOORS[player_name]}M). Player declines."
                )
            }
        if any(d.player == player_name for d in self.signed_deals):
            return {"error": f"{player_name} is already signed."}

        if self.committed_payroll[team_name] + aav > SALARY_CAP:
            return {
                "error": (
                    f"Would push {team_name} to "
                    f"${self.committed_payroll[team_name] + aav:.1f}M — "
                    f"over ${SALARY_CAP}M hard cap."
                )
            }

        res = self.reservation_prices.get(team_name, {}).get(player_name)
        if res is None or res["max_aav"] == 0:
            return {"error": f"{team_name} will not sign {player_name}."}

        if aav > res["max_aav"] or years > res["max_years"]:
            budget_used = self.rejection_budget.get(pair, 0) + 1
            self.rejection_budget[pair] = budget_used
            remaining = 3 - budget_used

            if remaining <= 0:
                self.locked_pairs.add(pair)
                self._inject_withdrawal(team_name, player_name)
                return {
                    "error": (
                        f"Ownership rejected. {team_name} has withdrawn "
                        f"from negotiations with {player_name} for this season."
                    )
                }

            self._inject_ownership_veto(team_name, player_name)
            return {
                "error": (
                    f"Ownership rejected — {remaining} attempt(s) remaining "
                    f"for this player-team pair."
                )
            }

        deal = Deal(player=player_name, team=team_name, aav=aav, years=years)
        self.signed_deals.append(deal)
        self.committed_payroll[team_name] += aav
        self._broadcast_signing(player_name, team_name)

        return {
            "status": "DEAL SIGNED",
            "player": player_name,
            "team": team_name,
            "aav": aav,
            "years": years,
            "total_value": deal.total_value,
            "commission_this_deal": deal.commission,
            "running_total_commission": self._gross_commission(),
            "current_score": self._net_score(),
        }

    def tool_advance_round(self, notes: Optional[str] = None) -> dict:
        if self.current_round >= MAX_ROUNDS:
            return self._close_window()
        self.current_round += 1
        return {
            "status": f"Now in Round {self.current_round} of {MAX_ROUNDS}.",
            "rounds_remaining": MAX_ROUNDS - self.current_round,
            "unsigned_players": self._unsigned(),
            "current_score": self._net_score(),
        }

    def tool_check_commission(self) -> dict:
        unsigned = self._unsigned()
        return {
            "gross_commission": self._gross_commission(),
            "auto_sign_penalty_exposure": len(unsigned) * AUTO_SIGN_PENALTY,
            "current_net_score": self._net_score(),
            "signed_deals": [
                {
                    "player": d.player, "team": d.team,
                    "aav": d.aav, "years": d.years,
                    "commission": d.commission
                }
                for d in self.signed_deals
            ],
            "unsigned_players": unsigned,
            "current_round": self.current_round,
        }

    # ------------------------------------------------------------------ #
    # Internal helpers                                                      #
    # ------------------------------------------------------------------ #

    def _call_gm(self, team: str) -> str:
        system_prompt = build_gm_system_prompt(
            team, self.reservation_prices, self.current_round
        )
        messages = [
            {"role": m["role"], "content": m["content"]}
            for m in self.email_threads[team]
            if m["role"] in ("user", "assistant")
        ]
        resp = self.gm_client.messages.create(
            model=self.gm_model_id,
            max_tokens=400,
            temperature=0.3,
            system=system_prompt,
            messages=messages,
        )
        text = resp.content[0].text
        self.email_threads[team].append({"role": "assistant", "content": text})
        return text

    def _inject_ownership_veto(self, team: str, player: str) -> None:
        msg = (
            f"After checking with ownership, we can't proceed at that "
            f"number for {player}. We remain interested but need to come "
            f"back down. Let's keep talking."
        )
        self.email_threads[team].append({"role": "assistant", "content": msg})
        self._deposit_inbox(team, f"Re: {player}", msg)

    def _inject_withdrawal(self, team: str, player: str) -> None:
        msg = (
            f"I need to be direct: ownership has asked us to step back from "
            f"{player} at this time. We've exhausted our flexibility on this "
            f"one. I appreciate your patience but we're out."
        )
        self.email_threads[team].append({"role": "assistant", "content": msg})
        self._deposit_inbox(team, f"Re: {player}", msg)

    def _broadcast_signing(self, player: str, team: str) -> None:
        notice = (
            f"[LEAGUE NOTICE] {player} has signed with {team}. "
            f"They are no longer available in free agency."
        )
        for t in self.committed_payroll:
            if t != team:
                self.email_threads[t].append(
                    {"role": "user", "content": notice}
                )
        self._deposit_inbox("League Office", f"Signing: {player}", notice)

    def _deposit_inbox(self, from_team: str, subject: str, body: str) -> None:
        self.inbox.append({
            "from": from_team,
            "subject": f"Re: {subject}",
            "body": body,
            "round": self.current_round,
            "read": False,
        })

    def _close_window(self) -> dict:
        unsigned = self._unsigned()
        self.auto_signed = unsigned[:]
        return {
            "status": "FREE AGENCY CLOSED",
            "auto_signed": [
                {"player": p, "deal": "$1M/1yr", "penalty": AUTO_SIGN_PENALTY}
                for p in unsigned
            ],
            "final_net_score": self._net_score(),
        }

    def _unsigned(self) -> list[str]:
        signed_names = {d.player for d in self.signed_deals}
        return [p for p in PLAYER_FLOORS if p not in signed_names]

    def _gross_commission(self) -> float:
        return sum(d.commission for d in self.signed_deals)

    def _net_score(self) -> float:
        return self._gross_commission() - len(self.auto_signed) * AUTO_SIGN_PENALTY
