"""Ferramentas do banco fictício com armazenamento local transacional."""

from __future__ import annotations

import hmac
import re
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from .policy import Audit, Rejected, RequestBudget, Settings
from .storage import Entry, Ledger

# Identidades exclusivas do cenário de demonstração; não consultar cadastros reais.
DEMO_USERS = (
    ("Ana", "1001", "00000000191", "2468"),
    ("Bruno", "1002", "00000000272", "1357"),
    ("Carla", "1003", "00000000353", "8642"),
)


def resolve_recipient(value: str) -> str:
    """Mapeia apenas nomes/contas exatos do cadastro, sem corrigir identificadores."""
    normalized = value.strip().casefold()
    for name, account, _, _ in DEMO_USERS:
        if normalized in (name.casefold(), account):
            return account
    return value


def money(value: str) -> Decimal:
    if not isinstance(value, str) or not re.fullmatch(r"\d{1,8}(?:[,.]\d{1,2})?", value):
        raise Rejected("Informe um valor positivo, sem separador de milhar, como 25,50.")
    result = Decimal(value.replace(",", ".")).quantize(Decimal("0.01"))
    if result <= 0 or result > Decimal("100000.00"):
        raise Rejected("Valor deve estar entre R$ 0,01 e R$ 100.000,00.")
    return result


def brl(value: Decimal) -> str:
    return f"R$ {value:.2f}".replace(".", ",")


class InsufficientBalance(Rejected):
    def __init__(self, balance: Decimal, credit_available: Decimal):
        super().__init__("ALERTA: saldo simulado insuficiente. Nenhuma operação foi realizada.")
        self.balance = balance
        self.credit_available = credit_available


def valid_cpf(value: str) -> bool:
    if not re.fullmatch(r"\d{3}\.?\d{3}\.?\d{3}-?\d{2}", value):
        return False
    digits = re.sub(r"\D", "", value)
    if len(set(digits)) == 1:
        return False
    for length in (9, 10):
        digit = (sum(int(digits[i]) * (length + 1 - i) for i in range(length)) * 10) % 11
        if int(digits[length]) != (0 if digit == 10 else digit):
            return False
    return True


class Auth:
    def __init__(self, settings: Settings, clock=time.monotonic):
        self.settings, self.clock = settings, clock
        self.account: str | None = None
        self.expires = 0.0
        self.failures = 0
        self.locked_until = 0.0
        self.generation = 0

    def logout(self) -> None:
        self.account = None
        self.expires = 0
        self.generation += 1

    def _attempt(self, ok: bool) -> None:
        if self.clock() < self.locked_until:
            raise Rejected("Autenticação bloqueada temporariamente por 60 segundos.")
        if not ok:
            self.failures += 1
            if self.failures >= 3:
                self.locked_until = self.clock() + 60
                self.failures = 0
                self.logout()
            raise Rejected("Credenciais de demonstração inválidas.")
        self.failures = 0

    def login(self, cpf: str, pin: str, budget: RequestBudget) -> str:
        self.logout()
        budget.call("ValidarCPF")
        digits = re.sub(r"\D", "", cpf)
        user = next((u for u in DEMO_USERS if u[2] == digits), None)
        self._attempt(bool(valid_cpf(cpf) and user and
                           hmac.compare_digest(pin.encode(), user[3].encode())))
        self.account = user[1]
        self.expires = self.clock() + self.settings.session_seconds
        budget.audit.record(request=budget.id, action="ValidarCPF", decision="SUCCESS")
        return user[0]

    def require(self) -> str:
        if not self.account or self.clock() >= self.expires:
            self.logout()
            raise Rejected("Sessão ausente ou expirada. Use /entrar.")
        return self.account

    def verify_pin(self, pin: str) -> None:
        account = self.require()
        expected = next(u[3] for u in DEMO_USERS if u[1] == account)
        self._attempt(hmac.compare_digest(pin.encode(), expected.encode()))


@dataclass(frozen=True)
class Pending:
    id: str
    request_id: str
    owner: str
    generation: int
    operation: str
    amount: Decimal
    destination: str | None
    source: str
    expires: float


class Bank:
    def __init__(self, auth: Auth, audit: Audit, clock=time.monotonic, db_path: Path | None = None):
        self.auth, self.audit, self.clock = auth, audit, clock
        self.ledger = Ledger(db_path)
        self.pending: Pending | None = None

    @property
    def balances(self) -> dict[str, Decimal]:
        return self.ledger.balances

    @property
    def entries(self) -> list[Entry]:
        return self.ledger.entries

    def authorize(self, account: str | None = None) -> str:
        owner = self.auth.require()
        if account and account != owner:
            raise Rejected("Acesso negado: consultas e débitos são restritos à sua conta.")
        return owner

    def balance(self, budget: RequestBudget, account: str | None = None) -> str:
        owner = self.authorize(account)
        budget.call("Saldo")
        data = self.ledger.account(owner, budget.remaining)
        budget.check()
        self.audit.record(request=budget.id, action="Saldo", decision="SUCCESS")
        return (f"Saldo disponível simulado da conta {owner}: {brl(data['balance'])}."
                f"\nCartão fictício: limite disponível {brl(data['available'])}. "
                "Para detalhes, use /limite.")

    def credit(self, budget: RequestBudget, account: str | None = None) -> str:
        owner = self.authorize(account)
        budget.call("Saldo")  # Consulta de crédito compartilha a quota de consulta de saldo.
        data = self.ledger.account(owner, budget.remaining)
        budget.check()
        self.audit.record(request=budget.id, action="Saldo", decision="SUCCESS")
        return (f"Cartão fictício da conta {owner}:"
                f"\nLimite total: {brl(data['limit'])}."
                f"\nCrédito utilizado: {brl(data['used'])}."
                f"\nLimite disponível: {brl(data['available'])}."
                "\nTarifas e juros simulados: R$ 0,00. Pagamento de fatura não implementado.")

    def statement(self, budget: RequestBudget, days: int = 30, page: int = 1,
                  deposits_only: bool = False, account: str | None = None) -> str:
        owner = self.authorize(account)
        if type(days) is not int or not 1 <= days <= 90 or type(page) is not int or page < 1:
            raise Rejected("Extrato: período de 1 a 90 dias e página positiva.")
        budget.call("Extrato")
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        rows, pages = self.ledger.statement(owner, cutoff, page, deposits_only, budget.remaining)
        budget.check()
        lines = [f"Extrato simulado: últimos {days} dias, página {page}/{pages} (histórico salvo)."]
        for entry in rows:
            source = "cartão" if entry.source == "cartao" else "conta"
            lines.append(f"{entry.date:%d/%m %H:%M} UTC | {entry.operation} | {source} | {brl(entry.amount)} | {entry.id}")
        if not rows:
            lines.append("Nenhum lançamento encontrado.")
        self.audit.record(request=budget.id, action="Extrato", decision="SUCCESS")
        return "\n".join(lines)

    def prepare(self, budget: RequestBudget, operation: str, value: str,
                destination: str | None = None, account: str | None = None, source: str = "saldo") -> Pending:
        owner = self.authorize(account)
        if self.pending:
            raise Rejected("Confirme ou cancele a operação pendente antes de preparar outra.")
        if operation not in {"deposito", "saque"}:
            raise Rejected("Operação não habilitada.")
        if source not in {"saldo", "cartao"}:
            raise Rejected("Fonte de recursos não habilitada.")
        amount = money(value)
        if operation == "deposito":
            if isinstance(destination, str):
                destination = resolve_recipient(destination)
            if destination not in {u[1] for u in DEMO_USERS} or destination == owner:
                raise Rejected("Selecione outra conta fictícia válida como destinatária: 1001, 1002 ou 1003.")
        elif destination is not None:
            raise Rejected("Saque não aceita destinatário.")
        budget.call("Deposito" if operation == "deposito" else "Saque")
        data = self.ledger.account(owner, budget.remaining)
        budget.check()
        available = data["available"] if source == "cartao" else data["balance"]
        if amount > available:
            self.audit.record(request=budget.id, action=operation, decision="DENY", code="insufficient_balance")
            if source == "saldo":
                raise InsufficientBalance(data["balance"], data["available"])
            label = "limite disponível do cartão" if source == "cartao" else "saldo simulado"
            raise Rejected(f"ALERTA: {label} insuficiente. Nenhuma operação foi realizada.")
        self.pending = Pending(uuid.uuid4().hex, budget.id, owner, self.auth.generation,
                               operation, amount, destination, source,
                               self.clock() + self.auth.settings.confirmation_seconds)
        self.audit.record(request=budget.id, action=operation, decision="AWAITING_CONFIRMATION")
        return self.pending

    def summary(self) -> str:
        p = self.pending
        if p is None:
            raise Rejected("Não há operação pendente.")
        target = next((u[0] for u in DEMO_USERS if u[1] == p.destination), "")
        destination = f"\nDestino: {target}, conta {p.destination}." if p.destination else ""
        source = "cartão de crédito fictício" if p.source == "cartao" else "saldo da conta"
        charge = "lançar no cartão" if p.source == "cartao" else "debitar da conta"
        return (f"SIMULAÇÃO — {'Depósito/transferência' if p.operation == 'deposito' else 'Saque'}"
                f"\nOrigem: conta {p.owner}. Valor: {brl(p.amount)}.{destination}"
                f"\nFonte: {source}."
                f"\nTarifa e juros simulados: R$ 0,00. Total a {charge}: {brl(p.amount)}."
                "\nPara aprovar esta operação, diga 'confirmar' ou digite /confirmar e informe seu PIN fora do chat."
                "\nConfirmação válida por 120 segundos. Para desistir: 'cancelar' ou /cancelar.")

    def cancel(self) -> None:
        pending = self.pending
        # Revogar não pode depender da disponibilidade da trilha de auditoria.
        self.pending = None
        if pending:
            self.audit.record(request=pending.request_id, action=pending.operation,
                              decision="CANCELLED")

    def confirm(self, budget: RequestBudget, confirmation_id: str, pin: str) -> str:
        owner = self.authorize()
        p = self.pending
        if p is None or confirmation_id != p.id:
            raise Rejected("Confirmação inválida ou já utilizada.")
        if p.owner != owner or p.generation != self.auth.generation or p.request_id != budget.id:
            self.cancel()
            raise Rejected("A confirmação não pertence à sessão e solicitação atuais.")
        if self.clock() >= p.expires:
            self.cancel()
            raise Rejected("Confirmação expirada. Prepare uma nova operação.")
        self.auth.verify_pin(pin)
        budget.call("Deposito" if p.operation == "deposito" else "Saque")
        # Reserve espaço para admissão e resultado antes de modificar o cenário.
        if len(self.audit.events) > 9998:
            raise Rejected("Auditoria indisponível. A operação não foi realizada.")
        self.audit.record(request=budget.id, action=p.operation, decision="ALLOW")

        def guard() -> None:
            budget.check()
            if self.authorize() != owner or self.auth.generation != p.generation:
                raise Rejected("Sessão alterada durante a confirmação.")
            if self.clock() >= p.expires:
                raise Rejected("Confirmação expirada.")

        self.ledger.execute(identifier=p.id, request_id=p.request_id, owner=owner,
                            operation=p.operation, source=p.source, amount=p.amount,
                            destination=p.destination, guard=guard, timeout=budget.remaining)
        source = "cartão fictício" if p.source == "cartao" else "saldo da conta"
        receipt = (f"SIMULAÇÃO concluída. Comprovante: {p.id}.\n"
                   f"{'Transferência' if p.operation == 'deposito' else 'Saque'} de {brl(p.amount)}."
                   f"\nFonte: {source}. Operação salva localmente."
                   "\nNenhum dinheiro real foi movimentado.")
        if p.operation == "saque":
            label = "Saldo" if p.source == "saldo" else "Crédito"
            receipt = f"Dinheiro sacado com sucesso! ({label})\n" + receipt
        self.pending = None
        self.audit.record(request=budget.id, action=p.operation, decision="SUCCESS")
        budget.closed = True
        return receipt
