"""Políticas determinísticas. Nenhuma decisão de segurança é delegada ao LLM."""

from __future__ import annotations

import hashlib
import json
import re
import time
import tomllib
import unicodedata
import uuid
from collections import Counter
from contextlib import contextmanager
from dataclasses import dataclass, field, fields
from decimal import Decimal
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parent.parent
RETRY_MESSAGE = "Por favor, tente novamente mais tarde!"
TOOL_LIMITS = {"ValidarCPF": 1, "Saldo": 3, "Extrato": 3, "Deposito": 10, "Saque": 3}


class Rejected(Exception):
    """Recusa esperada: texto seguro para apresentar ao cliente."""


class LimitReached(Rejected):
    pass


@dataclass(frozen=True)
class Settings:
    model: str
    input_usd_per_million: Decimal
    output_usd_per_million: Decimal
    brl_per_usd: Decimal
    price_margin: Decimal
    max_cost_brl: Decimal
    max_input_tokens: int
    max_context_tokens: int
    max_output_tokens: int
    timeout_seconds: int
    max_errors: int
    session_seconds: int
    confirmation_seconds: int
    max_requests_per_session: int
    max_requests_per_minute: int

    @classmethod
    def load(cls, path: Path = ROOT / "config.toml") -> Settings:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        if set(data) != {f.name for f in fields(cls)}:
            raise ValueError("Campos inválidos em config.toml.")
        for key in (
            "input_usd_per_million", "output_usd_per_million", "brl_per_usd",
            "price_margin", "max_cost_brl",
        ):
            data[key] = Decimal(str(data[key]))
            if not data[key].is_finite() or data[key] <= 0:
                raise ValueError("Preços e orçamento precisam ser positivos.")
        for f in fields(cls):
            if f.name not in {"model"} and not isinstance(data[f.name], Decimal):
                if type(data[f.name]) is not int or data[f.name] <= 0:
                    raise ValueError("Limites precisam ser inteiros positivos.")
        if data["model"] != "gpt-5.4-nano-2026-03-17":
            raise ValueError("Modelo não homologado. Revise provedor, preço e testes antes de mudar.")
        if data["max_errors"] != 7 or data["max_cost_brl"] > Decimal("0.05"):
            raise ValueError("A configuração deve respeitar sete erros e o teto de R$ 0,05.")
        if data["timeout_seconds"] > 60 or data["max_output_tokens"] > 512:
            raise ValueError("Prazo ou saída excedem a política homologada.")
        return cls(**data)


class Audit:
    """Trilha limitada à memória, encadeada para detectar alteração acidental.

    Não é um registro durável ou evidência independente contra o dono da máquina.
    Somente campos explicitamente permitidos são aceitos.
    """

    allowed = {"request", "action", "decision", "code", "errors", "calls",
               "cost_reserved", "cost_measured", "model"}

    def __init__(self) -> None:
        self.events: list[dict] = []
        self.chain = "0" * 64

    def record(self, **metadata: object) -> None:
        if not set(metadata) <= self.allowed:
            raise ValueError("Campo não permitido na auditoria.")
        if len(self.events) >= 10000:
            raise LimitReached("Auditoria da sessão cheia. Encerre e inicie nova sessão.")
        event = {"sequence": len(self.events), "time": round(time.time(), 3), **metadata}
        digest = hashlib.sha256((self.chain + json.dumps(event, sort_keys=True)).encode()).hexdigest()
        self.events.append({**event, "previous": self.chain, "hash": digest})
        self.chain = digest


@dataclass
class RequestBudget:
    settings: Settings
    audit: Audit
    clock: Callable[[], float] = time.monotonic
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    elapsed: float = 0
    errors: int = 0
    calls: Counter = field(default_factory=Counter)
    reserved: Decimal = Decimal("0")
    measured: Decimal = Decimal("0")
    closed: bool = False
    _started: float | None = None

    @property
    def remaining(self) -> float:
        current = self.clock() - self._started if self._started is not None else 0
        return self.settings.timeout_seconds - self.elapsed - current

    @contextmanager
    def processing(self):
        if self._started is not None:
            raise RuntimeError("Processamento já iniciado.")
        self.check()
        self._started = self.clock()
        try:
            yield
        finally:
            self.elapsed += self.clock() - self._started
            self._started = None

    def check(self) -> None:
        if self.errors >= self.settings.max_errors:
            self.closed = True
            raise LimitReached(f"Limite de sete erros atingido. {RETRY_MESSAGE}")
        if self.remaining <= 0:
            self.closed = True
            raise LimitReached(f"Tempo excedido. {RETRY_MESSAGE}")
        if self.closed:
            raise LimitReached("Solicitação encerrada.")

    def call(self, name: str) -> None:
        self.check()
        if name not in TOOL_LIMITS:
            raise Rejected("Ferramenta não autorizada.")
        if self.calls[name] >= TOOL_LIMITS[name]:
            raise LimitReached(f"Limite de chamadas atingido. {RETRY_MESSAGE}")
        self.calls[name] += 1
        self.audit.record(request=self.id, action=name, decision="ADMIT", calls=self.calls[name])

    def error(self, code: str) -> None:
        self.errors += 1
        self.audit.record(request=self.id, decision="ERROR", code=code, errors=self.errors)
        self.check()

    def estimate(self, input_tokens: int, output_tokens: int) -> Decimal:
        s = self.settings
        usd = (input_tokens * s.input_usd_per_million +
               output_tokens * s.output_usd_per_million) / Decimal(1_000_000)
        return usd * s.brl_per_usd * s.price_margin

    def reserve_model(self, input_upper_bound: int) -> None:
        self.check()
        cost = self.estimate(input_upper_bound, self.settings.max_output_tokens)
        if self.reserved + cost > self.settings.max_cost_brl:
            raise LimitReached(f"Orçamento de R$ 0,05 insuficiente para a próxima chamada. {RETRY_MESSAGE}")
        self.reserved += cost
        self.calls["OpenAI"] += 1
        self.audit.record(request=self.id, action="OpenAI", decision="ADMIT",
                          cost_reserved=str(self.reserved), model=self.settings.model)


def safe_terminal(text: object) -> str:
    """Remove sequências ANSI/OSC, caracteres de controle e formatação invisível."""
    value = re.sub(r"\x1b\][^\x07]*(?:\x07|\x1b\\)", "", str(text))
    value = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", value)
    return "".join(c for c in value if c in "\n\t" or unicodedata.category(c)[0] != "C")


def protect_input(text: str, api_key: str = "") -> str:
    if len(text) > 8000:
        raise LimitReached(f"Mensagem acima do limite permitido. {RETRY_MESSAGE}")
    clean = safe_terminal(text).strip()
    if clean != text.strip():
        raise Rejected("Remova caracteres de controle ou invisíveis da mensagem.")
    # Não tentamos descobrir todo segredo possível em linguagem natural. Credenciais
    # possuem fluxo separado; esta é uma barreira adicional para cópias acidentais.
    patterns = (
        r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b",  # CPF
        r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)",   # cartão
        r"\bsk-[A-Za-z0-9_-]+",
        r"\b(?:senha|pin|cvc|cvv|token|api[_ -]?key)\s*[:=]?\s*\S+",
        r"\b(?:2468|1357|8642)\b",  # PINs públicos do cenário de teste
    )
    if (api_key and api_key in clean) or any(re.search(p, clean, re.I) for p in patterns):
        raise Rejected("Não envie CPF, PIN, cartão ou credenciais no chat. Use /entrar para autenticar.")
    if not clean:
        raise Rejected("Digite uma solicitação ou /ajuda.")
    return clean
