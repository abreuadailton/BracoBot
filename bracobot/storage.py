"""Livro do simulador em SQLite: saldos, crédito e lançamentos atômicos."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Callable

from .policy import ROOT, Rejected

DEFAULT_DB_PATH = ROOT / "dados" / "bracobot.sqlite3"
# Inteiros em centavos. Os valores iniciais são aplicados uma única vez.
INITIAL_ACCOUNTS = (("1001", 100000, 200000), ("1002", 50000, 150000), ("1003", 25000, 100000))


@dataclass(frozen=True)
class Entry:
    id: str
    date: datetime
    account: str
    operation: str
    amount: Decimal
    source: str


class Ledger:
    def __init__(self, path: Path | None = None):
        self.path = Path(path) if path is not None else DEFAULT_DB_PATH
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        except OSError:
            raise Rejected("Não foi possível abrir a pasta de dados do simulador.") from None
        self._initialize()

    @contextmanager
    def connection(self, timeout: float = 5):
        db = None
        try:
            db = sqlite3.connect(self.path, timeout=max(0.001, min(timeout, 5)), isolation_level=None)
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA foreign_keys = ON")
            db.execute("PRAGMA synchronous = FULL")
            yield db
        except sqlite3.Error:
            raise Rejected("Armazenamento local indisponível. Os dados não foram reiniciados. "
                           "Consulte o extrato antes de repetir uma confirmação.") from None
        finally:
            if db is not None:
                try:
                    if db.in_transaction:
                        db.rollback()
                finally:
                    db.close()

    def _initialize(self) -> None:
        schema = (
            """CREATE TABLE IF NOT EXISTS accounts (
                id TEXT PRIMARY KEY,
                balance_cents INTEGER NOT NULL CHECK(typeof(balance_cents) = 'integer' AND balance_cents >= 0),
                credit_limit_cents INTEGER NOT NULL CHECK(credit_limit_cents >= 0),
                credit_used_cents INTEGER NOT NULL DEFAULT 0
                    CHECK(typeof(credit_used_cents) = 'integer' AND credit_used_cents BETWEEN 0 AND credit_limit_cents)
            )""",
            """CREATE TABLE IF NOT EXISTS transactions (
                id TEXT PRIMARY KEY,
                request_id TEXT NOT NULL UNIQUE,
                owner TEXT NOT NULL REFERENCES accounts(id),
                operation TEXT NOT NULL CHECK(operation IN ('deposito', 'saque')),
                source TEXT NOT NULL CHECK(source IN ('saldo', 'cartao')),
                amount_cents INTEGER NOT NULL CHECK(typeof(amount_cents) = 'integer' AND amount_cents > 0),
                destination TEXT REFERENCES accounts(id),
                created TEXT NOT NULL,
                CHECK((operation = 'saque' AND destination IS NULL) OR
                      (operation = 'deposito' AND destination IS NOT NULL AND destination != owner))
            )""",
            """CREATE TABLE IF NOT EXISTS entries (
                seq INTEGER PRIMARY KEY,
                transaction_id TEXT NOT NULL REFERENCES transactions(id),
                account TEXT NOT NULL REFERENCES accounts(id),
                amount_cents INTEGER NOT NULL CHECK(typeof(amount_cents) = 'integer'),
                source TEXT NOT NULL CHECK(source IN ('saldo', 'cartao')),
                UNIQUE(transaction_id, account)
            )""",
            "CREATE INDEX IF NOT EXISTS entries_account ON entries(account, seq)",
        )
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            if db.execute("PRAGMA user_version").fetchone()[0] not in (0, 1):
                raise Rejected("Versão do banco local não suportada. Nenhum dado foi alterado.")
            for statement in schema:
                db.execute(statement)
            accounts = {row[0] for row in db.execute("SELECT id FROM accounts")}
            if not accounts:
                if db.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]:
                    raise Rejected("Banco local inconsistente; restaure uma cópia válida.")
                db.executemany("INSERT INTO accounts(id, balance_cents, credit_limit_cents) VALUES (?, ?, ?)",
                               INITIAL_ACCOUNTS)
            elif accounts != {row[0] for row in INITIAL_ACCOUNTS}:
                raise Rejected("Contas locais inconsistentes; nenhum saldo foi reiniciado.")
            db.execute("PRAGMA user_version = 1")
            db.commit()

    def account(self, owner: str, timeout: float = 5) -> dict:
        with self.connection(timeout) as db:
            row = db.execute("SELECT * FROM accounts WHERE id = ?", (owner,)).fetchone()
            if row is None:
                raise Rejected("Conta fictícia não encontrada.")
            return {
                "balance": Decimal(row["balance_cents"]) / 100,
                "limit": Decimal(row["credit_limit_cents"]) / 100,
                "used": Decimal(row["credit_used_cents"]) / 100,
                "available": Decimal(row["credit_limit_cents"] - row["credit_used_cents"]) / 100,
            }

    @property
    def balances(self) -> dict[str, Decimal]:
        with self.connection() as db:
            return {r["id"]: Decimal(r["balance_cents"]) / 100 for r in db.execute("SELECT * FROM accounts")}

    @staticmethod
    def _entry(row) -> Entry:
        return Entry(row["id"], datetime.fromisoformat(row["created"]), row["account"],
                     row["operation"], Decimal(row["amount_cents"]) / 100, row["source"])

    @property
    def entries(self) -> list[Entry]:
        with self.connection() as db:
            return [self._entry(r) for r in db.execute(
                """SELECT t.id, t.created, t.operation, e.account, e.amount_cents, e.source
                   FROM entries e JOIN transactions t ON t.id = e.transaction_id ORDER BY e.seq"""
            )]

    def statement(self, owner: str, since: datetime, page: int, deposits_only: bool,
                  timeout: float = 5) -> tuple[list[Entry], int]:
        # Count e página usam o mesmo snapshot, mesmo com outra janela escrevendo.
        with self.connection(timeout) as db:
            db.execute("BEGIN")
            condition = "e.account = ? AND t.created >= ?"
            parameters: tuple = (owner, since.isoformat())
            if deposits_only:
                condition += " AND t.operation = 'deposito'"
            count = db.execute(
                "SELECT COUNT(*) FROM entries e JOIN transactions t ON t.id = e.transaction_id WHERE " + condition,
                parameters,
            ).fetchone()[0]
            pages = max(1, (count + 9) // 10)
            if page > pages:
                raise Rejected(f"Página inexistente. Há {pages} página(s).")
            rows = db.execute(
                """SELECT t.id, t.created, t.operation, e.account, e.amount_cents, e.source
                   FROM entries e JOIN transactions t ON t.id = e.transaction_id WHERE """
                + condition + " ORDER BY e.seq DESC LIMIT 10 OFFSET ?",
                (*parameters, (page - 1) * 10),
            ).fetchall()
            return [self._entry(row) for row in rows], pages

    def execute(self, *, identifier: str, request_id: str, owner: str, operation: str,
                source: str, amount: Decimal, destination: str | None,
                guard: Callable[[], None], timeout: float = 5) -> None:
        if source not in ("saldo", "cartao") or operation not in ("deposito", "saque"):
            raise Rejected("Operação ou fonte de recursos não autorizada.")
        if not amount.is_finite() or amount <= 0 or amount * 100 != (amount * 100).to_integral_value():
            raise Rejected("Valor monetário inválido.")
        cents = int(amount * 100)
        expected = (identifier, request_id, owner, operation, source, cents, destination)
        with self.connection(timeout) as db:
            db.execute("BEGIN IMMEDIATE")
            guard()  # Revalidar depois da espera pelo lock.
            previous = db.execute(
                """SELECT id, request_id, owner, operation, source, amount_cents, destination
                   FROM transactions WHERE id = ? OR request_id = ?""", (identifier, request_id)
            ).fetchone()
            if previous:
                if tuple(previous) != expected:
                    raise Rejected("Identificador já utilizado por outra operação.")
                return  # Mesmo efeito já confirmado; jamais aplicar duas vezes.
            account = db.execute("SELECT * FROM accounts WHERE id = ?", (owner,)).fetchone()
            if account is None:
                raise Rejected("Conta fictícia não encontrada.")
            if operation == "deposito":
                if destination == owner or not db.execute(
                    "SELECT 1 FROM accounts WHERE id = ?", (destination,)
                ).fetchone():
                    raise Rejected("Destinatário fictício inválido.")
            elif destination is not None:
                raise Rejected("Saque não aceita destinatário.")
            if source == "saldo":
                if cents > account["balance_cents"]:
                    raise Rejected("ALERTA: saldo simulado insuficiente na validação final.")
                db.execute("UPDATE accounts SET balance_cents = balance_cents - ? WHERE id = ?", (cents, owner))
            else:
                if cents > account["credit_limit_cents"] - account["credit_used_cents"]:
                    raise Rejected("ALERTA: limite disponível do cartão insuficiente na validação final.")
                db.execute("UPDATE accounts SET credit_used_cents = credit_used_cents + ? WHERE id = ?", (cents, owner))
            now = datetime.now(timezone.utc).isoformat()
            db.execute("INSERT INTO transactions VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (*expected, now))
            db.execute("INSERT INTO entries(transaction_id, account, amount_cents, source) VALUES (?, ?, ?, ?)",
                       (identifier, owner, -cents, source))
            if destination:
                db.execute("UPDATE accounts SET balance_cents = balance_cents + ? WHERE id = ?", (cents, destination))
                db.execute("INSERT INTO entries(transaction_id, account, amount_cents, source) VALUES (?, ?, ?, 'saldo')",
                           (identifier, destination, cents))
            guard()  # Timeout/expiração aqui reverte débito, crédito e lançamentos juntos.
            db.commit()
