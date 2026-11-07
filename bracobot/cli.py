"""Interface CMD. Confirmação, autenticação e resultados não passam pelo LLM."""

from __future__ import annotations

import argparse
import asyncio
import getpass
import os
import re
import sys
import time
import unicodedata
from collections import deque
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from dotenv import dotenv_values

from .bank import Auth, Bank, InsufficientBalance, brl, money
from .policy import ROOT, Audit, LimitReached, Rejected, RequestBudget, Settings, protect_input, safe_terminal
from .router import DemoRouter, OpenAIRouter, Solicitacao

HELP = """Posso consultar saldo, limite do cartão e extrato, transferir/depositar e simular saque.
Exemplos: "qual meu saldo?", "extrato dos últimos 30 dias", "transfira 25,50 para Bruno",
"saque de 10", "transfira 50 para Bruno usando o cartão", "qual meu limite?".
Contas de destino: Ana 1001, Bruno 1002, Carla 1003.
Comandos: /entrar, /trocar, /limite, /ajuda, /confirmar, /cancelar, /auditoria, /sair.
Você também pode dizer "quero entrar", "trocar de conta", "me ajuda",
"confirmar", "cancelar", "mostrar auditoria" ou "quero sair".
Se faltar saldo para transferir, posso oferecer crédito, somente com seu consentimento.
Use /novo para abandonar uma conversa incompleta e iniciar outra intenção.
Saldos, crédito utilizado e lançamentos ficam salvos localmente. Não informe dados reais."""


def normalized_intent(text: str) -> str:
    text = "".join(c for c in unicodedata.normalize("NFKD", text.casefold()) if not unicodedata.combining(c))
    text = re.sub(r"\s+", " ", text).strip().rstrip(".!?")
    text = re.sub(r"^por favor,?\s+|\s*,?\s*por favor$", "", text).strip()
    return text


def local_command(text: str, pending: bool = False) -> str:
    """Reconhece intenções completas; texto citado, negado ou composto não confirma."""
    intent = normalized_intent(text)
    if intent.startswith("/"):
        return intent.split(maxsplit=1)[0]
    if pending and intent in ("sim", "sim, pode confirmar", "sim pode confirmar",
                              "pode prosseguir", "sim, pode prosseguir", "sim pode prosseguir"):
        return "/confirmar"
    prefix = r"(?:(?:eu )?(?:quero|gostaria de|preciso|preciso de|pode|voce pode|poderia|voce poderia) )?"
    patterns = {
        "/entrar": r"(?:entrar|acessar (?:a )?minha conta|(?:fazer )?login|me autenticar|iniciar (?:a )?sessao)",
        "/trocar": r"(?:(?:trocar|troque|mudar|mude) (?:de )?conta|entrar (?:em |na )?outra conta)",
        "/ajuda": r"(?:ajuda|me ajude|me ajuda|me ajudar|ajude-me|(?:ver|mostrar|mostre) (?:os )?comandos|(?:ver|mostrar|mostre) (?:a )?ajuda)",
        "/confirmar": r"(?:(?:confirmar|confirme|confirma)(?: (?:a |essa |esta |o )?(?:operacao|transferencia|saque))?|confirmo)",
        "/cancelar": r"(?:(?:cancelar|cancele|cancela)(?: (?:a |essa |esta |o )?(?:operacao|transferencia|saque))?|desistir|desisto)",
        "/novo": r"(?:nova (?:solicitacao|operacao)|comecar de novo|recomecar)",
        "/auditoria": r"(?:(?:ver|mostrar|mostre|consultar) (?:a )?)?auditoria",
        "/limite": r"(?:(?:ver|mostrar|mostre|consultar) (?:o |meu )?|qual (?:e )?(?:o )?(?:meu )?)?limite(?: do (?:meu )?cartao)?",
        "/sair": r"(?:sair|encerrar(?: (?:a )?(?:sessao|aplicacao|conversa))?|fechar (?:o )?(?:chat|aplicativo))",
    }
    for command, pattern in patterns.items():
        if re.fullmatch(prefix + pattern, intent):
            return command
    return ""


@dataclass(frozen=True)
class CreditOffer:
    plan: Solicitacao
    owner: str
    generation: int
    expires: float


class Chat:
    def __init__(self, settings: Settings, router, clock=time.monotonic, db_path: Path | None = None):
        self.settings, self.router, self.clock = settings, router, clock
        self.audit = Audit()
        self.auth = Auth(settings, clock)
        self.bank = Bank(self.auth, self.audit, clock, db_path)
        self.budget: RequestBudget | None = None
        self.history: list[str] = []
        self.awaiting_value: Solicitacao | None = None
        self.credit_offer: CreditOffer | None = None
        self.requests = 0
        self.timestamps: deque[float] = deque()

    def clear_request(self) -> None:
        try:
            self.bank.cancel()
        except (OSError, LimitReached, ValueError):
            # A aprovação já foi revogada. Nova movimentação continuará exigindo
            # auditoria funcional; falha de registro não pode impedir a parada.
            pass
        if self.budget:
            self.budget.closed = True
        self.budget = None
        self.history.clear()
        self.awaiting_value = None
        self.credit_offer = None

    def login(self, cpf: str, pin: str) -> str:
        self.clear_request()
        # O login muda a identidade e invalida aprovações, não o livro persistido.
        budget = RequestBudget(self.settings, self.audit, self.clock)
        with budget.processing():
            name = self.auth.login(cpf, pin, budget)
        self.requests = 0
        return f"Olá, {name}! Sessão fictícia autenticada por 15 minutos. {HELP}"

    def new_budget(self) -> RequestBudget:
        now = self.clock()
        while self.timestamps and now - self.timestamps[0] >= 60:
            self.timestamps.popleft()
        if len(self.timestamps) >= self.settings.max_requests_per_minute:
            raise LimitReached("Limite de dez solicitações por minuto. Aguarde um pouco.")
        if self.requests >= self.settings.max_requests_per_session:
            raise LimitReached("Limite de sessenta solicitações da sessão. Use /entrar.")
        self.timestamps.append(now)
        self.requests += 1
        return RequestBudget(self.settings, self.audit, self.clock)

    async def message(self, text: str) -> str:
        self.auth.require()
        if self.bank.pending:
            return "Há uma operação pendente. Use /confirmar ou /cancelar antes de continuar."
        text = protect_input(text, self.router.api_key)
        if self.router.count(text) > self.settings.max_input_tokens:
            raise LimitReached("Mensagem acima do limite de 1024 tokens. Por favor, tente novamente mais tarde!")
        if self.credit_offer is not None:
            return self.answer_credit_offer(text)
        if self.budget is None:
            self.budget = self.new_budget()
        if len(self.history) >= 6:
            self.clear_request()
            raise LimitReached("Limite de seis mensagens para esclarecer a mesma intenção. Comece novamente.")
        self.history.append(text)
        budget = self.budget
        with budget.processing():
            if self.awaiting_value is not None and re.fullmatch(r"\d{1,8}(?:[,.]\d{1,2})?", text):
                # Resposta somente com valor completa o rascunho já validado,
                # sem reinterpretar destinatário, origem ou fonte de recursos.
                plan = self.awaiting_value.model_copy(update={"valor": text})
            else:
                plan = await self.router.interpret(self.history, budget)
            self.awaiting_value = None
            budget.check()
            result, done = self.dispatch(plan, budget)
        if done:
            budget.closed = True
            self.budget = None
            self.history.clear()
            self.awaiting_value = None
            self.credit_offer = None
        return result

    def dispatch(self, plan: Solicitacao, budget: RequestBudget) -> tuple[str, bool]:
        # A origem nunca vem de contexto do modelo sem validar a identidade real.
        self.bank.authorize(plan.conta)
        if plan.acao == "saldo":
            return self.bank.balance(budget, plan.conta), True
        if plan.acao == "limite":
            return self.bank.credit(budget, plan.conta), True
        if plan.acao == "trocar_conta":
            return "Diga 'trocar de conta' ou use /trocar para autenticar outra conta sem fechar o aplicativo.", True
        if plan.acao == "extrato":
            return self.bank.statement(budget, plan.dias, plan.pagina,
                                       plan.somente_depositos, plan.conta), True
        if plan.acao in ("deposito", "saque"):
            if plan.fonte == "cartao" and not re.search(
                r"\b(cart[aã]o|cr[eé]dito)\b", " ".join(self.history), re.I
            ):
                return "Para usar crédito, peça explicitamente o cartão fictício; caso contrário use saldo.", False
            if plan.valor is None:
                self.awaiting_value = plan.model_copy(deep=True)
                return "Qual valor deseja simular? Use, por exemplo, 25,50.", False
            amount = money(plan.valor)
            # Evita que o modelo invente/corrija silenciosamente um número.
            candidates = re.findall(r"(?<![\d.,])\d+(?:[,.]\d{1,2})?(?![\d.,])", " ".join(self.history))
            if not any(Decimal(n.replace(",", ".")) == amount for n in candidates):
                return "Digite o valor em números, com até duas casas, sem separador de milhar.", False
            if plan.acao == "deposito" and plan.destinatario is None:
                return "Qual destinatário? Ana (1001), Bruno (1002) ou Carla (1003)?", False
            try:
                self.bank.prepare(budget, plan.acao, plan.valor, plan.destinatario, plan.conta, plan.fonte)
            except InsufficientBalance as exc:
                if plan.acao != "deposito":
                    raise
                if exc.credit_available < amount:
                    return (f"Saldo insuficiente ({brl(exc.balance)}) e limite disponível do cartão "
                            f"insuficiente ({brl(exc.credit_available)}) para transferir {brl(amount)}. "
                            "Nenhuma operação foi realizada."), True
                self.credit_offer = CreditOffer(
                    plan.model_copy(update={"fonte": "cartao"}, deep=True), self.auth.require(),
                    self.auth.generation, self.clock() + self.settings.confirmation_seconds,
                )
                return (f"Seu saldo de {brl(exc.balance)} é insuficiente para transferir "
                        f"{brl(amount)} à conta {plan.destinatario}."
                        f"\nSeu cartão fictício tem {brl(exc.credit_available)} de limite disponível."
                        f"\nDeseja usar crédito? O valor integral de {brl(amount)} será lançado no cartão, "
                        "sem debitar o saldo. Tarifas e juros simulados: R$ 0,00."
                        "\nResponda 'usar crédito' ou 'sim' para revisar a operação; "
                        "'não' ou 'cancelar' para desistir. Oferta válida por 120 segundos."), False
            return self.bank.summary(), False
        if plan.acao == "esclarecer":
            return ("Informe uma operação por vez." if plan.motivo == "uma_operacao"
                    else "Pode esclarecer a operação, o valor ou o destinatário?"), False
        if plan.acao == "fora_escopo":
            self.audit.record(request=budget.id, decision="DENY", code="outside_scope")
            return "Essa solicitação está fora das capacidades autorizadas.\n" + HELP, True
        return HELP, True

    def answer_credit_offer(self, text: str) -> str:
        offer = self.credit_offer
        owner = self.auth.require()
        if (offer is None or self.budget is None or offer.owner != owner
                or offer.generation != self.auth.generation or self.clock() >= offer.expires):
            self.clear_request()
            raise Rejected("Oferta de crédito expirada ou inválida. Faça uma nova solicitação.")
        answer = normalized_intent(text)
        if answer in ("nao", "nao quero", "nao quero usar credito", "nao quero usar o cartao",
                      "cancelar", "desistir", "prefiro cancelar"):
            self.clear_request()
            return "Transferência cancelada. Nenhum saldo ou limite foi utilizado."
        accepted = re.fullmatch(
            r"(?:sim[, ]+)?(?:(?:quero|pode|desejo|vamos) )?"
            r"(?:usar (?:o )?(?:credito|cartao)|prosseguir(?: com (?:o )?(?:credito|cartao))?)",
            answer,
        ) or answer == "sim"
        if not accepted:
            return ("Deseja usar crédito para a transferência apresentada? Responda 'usar crédito' ou 'não'. "
                    "Para mudar o valor ou destinatário, cancele e faça um novo pedido.")
        with self.budget.processing():
            self.budget.check()
            plan = offer.plan
            # Consentimento local vinculado à oferta; o modelo não pode aceitá-la.
            self.bank.prepare(self.budget, plan.acao, plan.valor, plan.destinatario, plan.conta, "cartao")
        self.credit_offer = None
        return self.bank.summary()

    def credit_limit(self) -> str:
        self.auth.require()
        if self.bank.pending:
            return "Há uma operação pendente. Use /confirmar ou /cancelar antes de continuar."
        self.clear_request()
        budget = self.new_budget()
        with budget.processing():
            result = self.bank.credit(budget)
        budget.closed = True
        return result

    def confirm(self, identifier: str, pin: str) -> str:
        if self.budget is None:
            raise Rejected("Não há operação pendente.")
        with self.budget.processing():
            result = self.bank.confirm(self.budget, identifier, pin)
        self.budget = None
        self.history.clear()
        self.awaiting_value = None
        self.credit_offer = None
        return result

    def audit_summary(self) -> str:
        # Não expõe CPF, saldos, valores ou prompts, nem permite reconstituir livro.
        events = self.audit.events[-12:]
        lines = ["Auditoria técnica somente em memória (últimos 12 eventos):"]
        for event in events:
            lines.append(f"{event['sequence']}: {event.get('action', '-')} "
                         f"{event.get('decision', '-')} {event.get('code', '')}")
        return "\n".join(lines)


def say(text: object) -> None:
    print(f"\nBracoBot> {safe_terminal(text)}\n")


def secret(prompt: str) -> str:
    # getpass pode fazer fallback com eco quando stdin é pipe: não permitir.
    if not sys.stdin.isatty():
        raise Rejected("Credenciais exigem um terminal interativo. Abra iniciar.cmd no CMD.")
    return getpass.getpass(prompt)


def load_api_key(env_file: Path = ROOT / ".env") -> str:
    """Lê somente a chave; não importa outras configurações do .env para o processo."""
    configured = os.environ.get("OPENAI_API_KEY", "").strip()
    if configured:
        return configured
    if env_file.is_file():
        values = dotenv_values(env_file, encoding="utf-8-sig", interpolate=False)
        return (values.get("OPENAI_API_KEY") or "").strip()
    return ""


async def run(demo: bool) -> int:
    settings = Settings.load()
    print("BracoBot | Assistente de IA | SIMULAÇÃO BANCÁRIA LOCAL")
    print("Sem dinheiro real. Saldos, crédito e extratos são salvos neste computador.")
    if demo:
        print("MODO DEMONSTRAÇÃO: interpretador limitado, SEM OpenAI e SEM chamadas pagas.")
        router = DemoRouter(settings)
    else:
        key = load_api_key()
        if not key:
            print("A chave será usada somente em memória. Não a digite na conversa.")
            key = secret("Chave OpenAI (entrada oculta): ").strip()
        if not key:
            raise Rejected("Chave ausente. Configure OPENAI_API_KEY ou use demonstracao.cmd.")
        router = OpenAIRouter(settings, key)
        print(f"OpenAI real via Strands | modelo: {settings.model}")
        print("Controle local de custo baseado nos preços e câmbio de config.toml.")
    chat = Chat(settings, router)
    say("Diga 'quero entrar' para autenticar ou 'me ajuda' para ver as opções. Comandos com / também funcionam.")
    while True:
        try:
            text = input("Você> ").strip()
            command = local_command(text, pending=chat.bank.pending is not None)
            if command in ("/sair", "sair"):
                chat.clear_request()
                chat.auth.logout()
                say("Sessão encerrada. Saldos, crédito e extratos continuam salvos.")
                return 0
            if command in ("/entrar", "/trocar"):
                chat.clear_request()
                chat.auth.logout()
                cpf = secret("CPF de teste (oculto): ")
                pin = secret("PIN de teste (oculto): ")
                try:
                    say(chat.login(cpf, pin))
                finally:
                    cpf = pin = ""
            elif command in ("/ajuda", "/help"):
                say(HELP)
            elif command == "/limite":
                say(chat.credit_limit())
            elif command in ("/cancelar", "/novo"):
                chat.clear_request()
                say("Solicitação cancelada. Nenhuma aprovação pendente será reutilizada.")
            elif command == "/confirmar":
                if text.startswith("/") and len(text.split()) != 1:
                    raise Rejected("Use apenas /confirmar, sem identificador.")
                chat.auth.require()
                if not chat.bank.pending:
                    raise Rejected("Não há operação pendente.")
                identifier = chat.bank.pending.id
                pin = secret("Confirme seu PIN de teste (oculto): ")
                try:
                    say(chat.confirm(identifier, pin))
                finally:
                    pin = ""
            elif command == "/auditoria":
                chat.auth.require()
                say(chat.audit_summary())
            elif command in ("/saldo", "/extrato", "/saque", "/sacar",
                             "/transferir", "/transferencia", "/depositar"):
                say(await chat.message(text[1:]))
            elif command.startswith("/"):
                say("Comando desconhecido. Use /ajuda.")
            elif text:
                say(await chat.message(text))
        except (EOFError, KeyboardInterrupt, asyncio.CancelledError):
            chat.clear_request()
            chat.auth.logout()
            say("Interrompido. Aprovações pendentes canceladas; operações concluídas continuam salvas.")
            return 0
        except Rejected as exc:
            chat.clear_request()
            say(exc)
        except Exception:
            # Nunca imprimir repr/traceback de APIs: podem conter payloads ou chaves.
            chat.clear_request()
            say("Falha técnica. A solicitação foi interrompida. "
                "Se acabou de confirmar uma simulação, confira o extrato antes de repetir. "
                "Use /ajuda ou reinicie o agente.")


def main() -> int:
    parser = argparse.ArgumentParser(description="BracoBot: chat bancário fictício local.")
    parser.add_argument("--demo", action="store_true", help="Diagnóstico local sem OpenAI; interpretação limitada.")
    args = parser.parse_args()
    try:
        return asyncio.run(run(args.demo))
    except (Rejected, ValueError, OSError) as exc:
        # Mensagens de Settings e do fluxo local são seguras; OSError não inclui segredos.
        print(safe_terminal(exc), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
