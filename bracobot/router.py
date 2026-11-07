"""Strands interpreta a intenção; somente o executor local pode operar o banco."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from pathlib import Path
from types import SimpleNamespace
from typing import Literal

# Nenhum conteúdo, prompt ou credencial é exportado via tracing do SDK.
os.environ["OTEL_SDK_DISABLED"] = "true"
os.environ["OTEL_TRACES_EXPORTER"] = "none"
os.environ["OTEL_METRICS_EXPORTER"] = "none"
os.environ["OTEL_LOGS_EXPORTER"] = "none"

import httpx
import openai
import tiktoken
from pydantic import BaseModel, ConfigDict, Field, field_validator
from strands import Agent
from strands.hooks import AfterToolCallEvent, HookProvider, HookRegistry
from strands.models.openai import OpenAIModel
from strands.types.exceptions import EventLoopException, MaxTokensReachedException, StructuredOutputException

from .policy import LimitReached, Rejected, RequestBudget, Settings, RETRY_MESSAGE
from .bank import resolve_recipient

# Bibliotecas não escrevem payloads nem exceções do provedor no terminal.
for logger in list(logging.Logger.manager.loggerDict) + ["strands", "openai", "httpx", "httpcore", "opentelemetry"]:
    if not logger.startswith(("strands", "openai", "httpx", "httpcore", "opentelemetry")):
        continue
    logging.getLogger(logger).disabled = True
    logging.getLogger(logger).addHandler(logging.NullHandler())
    logging.getLogger(logger).propagate = False


class Solicitacao(BaseModel):
    """Intenção bancária proposta; não constitui autorização de execução."""

    model_config = ConfigDict(extra="forbid", strict=True)
    acao: Literal["saldo", "limite", "extrato", "deposito", "saque", "trocar_conta",
                  "ajuda", "esclarecer", "fora_escopo"]
    fonte: Literal["saldo", "cartao"] = "saldo"
    valor: str | None = Field(default=None, max_length=16)
    destinatario: Literal["1001", "1002", "1003"] | None = Field(
        default=None, description="Conta de destino: Ana=1001, Bruno=1002, Carla=1003. null se não informada."
    )
    conta: str | None = Field(default=None, max_length=4)
    dias: int = Field(default=30, ge=1, le=90)
    pagina: int = Field(default=1, ge=1, le=100)
    somente_depositos: bool = False
    motivo: Literal["ambiguidade", "uma_operacao"] = "ambiguidade"

    @field_validator("destinatario", mode="before")
    @classmethod
    def normalize_recipient(cls, value):
        # Aceita os nomes exatos mesmo se o modelo não seguir a enumeração do schema.
        return resolve_recipient(value) if isinstance(value, str) else value


class TemporaryFailure(Exception):
    pass


class MeteredCompletions:
    """Única porta de saída para cada chamada HTTP, inclusive chamadas internas."""

    def __init__(self, client: openai.AsyncOpenAI, budget: RequestBudget, encoder):
        self.client, self.budget, self.encoder = client, budget, encoder

    async def create(self, **kwargs):
        b = self.budget
        b.check()
        payload = json.dumps(
            {k: kwargs[k] for k in ("messages", "tools", "response_format") if k in kwargs},
            ensure_ascii=False, separators=(",", ":"),
        )
        tokens = len(self.encoder.encode(payload, disallowed_special=()))
        if tokens > b.settings.max_context_tokens:
            raise LimitReached(f"Contexto acima do limite permitido. {RETRY_MESSAGE}")
        if kwargs.get("model") != b.settings.model or kwargs.get("stream") is not False:
            raise Rejected("Configuração de inferência não autorizada.")
        # Limite conservador: bytes UTF-8 (>= tokens de texto) + margem de framing.
        # Preço/câmbio são referências configuradas; não equivalem a teto de fatura.
        b.reserve_model(len(payload.encode("utf-8")) + 2048)
        kwargs["max_completion_tokens"] = b.settings.max_output_tokens
        kwargs["timeout"] = max(0.001, b.remaining)
        kwargs["store"] = False
        try:
            response = await self.client.chat.completions.create(**kwargs)
        except (openai.APIConnectionError, openai.RateLimitError) as exc:
            b.error(type(exc).__name__)
            raise TemporaryFailure() from None
        except openai.APIStatusError as exc:
            b.error(f"http_{exc.status_code}")
            if exc.status_code >= 500:
                raise TemporaryFailure() from None
            if exc.status_code in (401, 403):
                raise Rejected("OpenAI recusou a credencial ou o acesso ao modelo. Verifique sua configuração.") from None
            if exc.status_code == 404:
                raise Rejected("Modelo indisponível para esta chave. Revise o modelo e seus preços antes de alterar a configuração.") from None
            raise Rejected("A OpenAI recusou a requisição. Consulte a configuração do provedor.") from None
        if response.usage:
            b.measured += b.estimate(response.usage.prompt_tokens, response.usage.completion_tokens)
        b.audit.record(request=b.id, action="OpenAI", decision="SUCCESS",
                       cost_reserved=str(b.reserved), cost_measured=str(b.measured))
        b.check()
        if b.measured > b.settings.max_cost_brl:
            b.closed = True
            raise LimitReached("Uso reportado excedeu a estimativa. Inferência interrompida; revise preços e limites.")
        # Reserva não é devolvida nem após erro de rede: cobrança pode ter ocorrido.
        return response


class ValidationErrors(HookProvider):
    def __init__(self, budget: RequestBudget):
        self.budget = budget

    def register_hooks(self, registry: HookRegistry) -> None:
        registry.add_callback(AfterToolCallEvent, self.after)

    def after(self, event: AfterToolCallEvent) -> None:
        if event.result.get("status") == "error":
            # O SDK pode capturar exceções do hook e chamá-lo novamente.
            # Conte aqui, mas interrompa na porta de saída ANTES do próximo HTTP.
            self.budget.errors += 1
            self.budget.audit.record(request=self.budget.id, decision="ERROR",
                                     code="invalid_structured_output", errors=self.budget.errors)


class OpenAIRouter:
    def __init__(self, settings: Settings, api_key: str, transport=None):
        self.settings, self.api_key, self.transport = settings, api_key, transport
        self.encoder = tiktoken.get_encoding("o200k_base")
        self.prompt = Path(__file__).with_name("system_prompt.md").read_text(encoding="utf-8")

    def count(self, text: str) -> int:
        return len(self.encoder.encode(text, disallowed_special=()))

    async def interpret(self, history: list[str], budget: RequestBudget) -> Solicitacao:
        if any(self.count(text) > self.settings.max_input_tokens for text in history):
            raise LimitReached(f"Mensagem acima do limite permitido. {RETRY_MESSAGE}")
        prompt = json.dumps({"mensagens_do_cliente": history}, ensure_ascii=False)
        # Base URL fixa, sem proxies do ambiente, redirecionamento ou retries ocultos.
        async with openai.AsyncOpenAI(
            api_key=self.api_key, base_url="https://api.openai.com/v1",
            max_retries=0, timeout=60,
            http_client=httpx.AsyncClient(trust_env=False, follow_redirects=False,
                                          transport=self.transport),
        ) as client:
            metered = MeteredCompletions(client, budget, self.encoder)
            model = OpenAIModel(
                client=SimpleNamespace(chat=SimpleNamespace(completions=metered)),
                model_id=self.settings.model, stream=False,
                params={"max_completion_tokens": self.settings.max_output_tokens,
                        "reasoning_effort": "none", "parallel_tool_calls": False},
            )
            while True:
                budget.check()
                agent = Agent(model=model, name="BracoBot", system_prompt=self.prompt,
                              structured_output_model=Solicitacao, callback_handler=None,
                              retry_strategy=None, hooks=[ValidationErrors(budget)],
                              load_tools_from_directory=False)
                try:
                    async with asyncio.timeout(budget.remaining):
                        result = await agent.invoke_async(prompt)
                    budget.check()
                    if not isinstance(result.structured_output, Solicitacao):
                        budget.error("missing_structured_output")
                        raise TemporaryFailure()
                    return result.structured_output
                except TemporaryFailure:
                    budget.check()
                    await asyncio.sleep(min(0.25 * budget.errors, max(0, budget.remaining)))
                except (StructuredOutputException, MaxTokensReachedException):
                    budget.error("invalid_model_response")
                except EventLoopException:
                    budget.check()
                    raise Rejected("Falha na interpretação estruturada. Nenhuma operação foi executada.") from None
                except TimeoutError:
                    budget.closed = True
                    raise LimitReached(f"Tempo excedido. {RETRY_MESSAGE}") from None


class DemoRouter:
    """Modo opcional de diagnóstico SEM LLM; nunca se apresenta como OpenAI."""

    api_key = ""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.encoder = tiktoken.get_encoding("o200k_base")

    def count(self, text: str) -> int:
        return len(self.encoder.encode(text, disallowed_special=()))

    async def interpret(self, history: list[str], budget: RequestBudget) -> Solicitacao:
        text = " ".join(history).lower()
        if any(word in text for word in ("ignore", "shell", "pix", "pagar fatura", "pagamento de fatura")):
            return Solicitacao(acao="fora_escopo")
        if re.search(r"trocar (?:de )?conta", text):
            return Solicitacao(acao="trocar_conta")
        source = "cartao" if re.search(r"\b(cart[aã]o|cr[eé]dito)\b", text) else "saldo"
        if sum(("extrato" in text,
                any(w in text for w in ("transf", "deposit", "depósit")),
                any(w in text for w in ("saque", "sacar")))) > 1:
            return Solicitacao(acao="esclarecer", motivo="uma_operacao")
        if any(word in text for word in ("extrato", "histórico", "historico", "consultar depósitos")):
            days = re.search(r"(\d+)\s*dias", text)
            page = re.search(r"p[aá]gina\s*(\d+)", text)
            return Solicitacao(acao="extrato", dias=int(days[1]) if days else 30,
                              pagina=int(page[1]) if page else 1,
                              somente_depositos="depósitos" in text)
        if any(word in text for word in ("transf", "deposit", "depósit", "saqu", "sac")):
            action = "saque" if any(w in text for w in ("saqu", "sac")) else "deposito"
            nums = re.findall(r"(?<!\d)\d+(?:[,.]\d{1,2})?(?!\d)", text)
            accounts = [n for n in nums if n in ("1001", "1002", "1003")]
            amounts = [n for n in nums if n not in accounts]
            dest = accounts[-1] if accounts else None
            for name, account in (("ana", "1001"), ("bruno", "1002"), ("carla", "1003")):
                if re.search(rf"\b{name}\b", text):
                    dest = account
            return Solicitacao(acao=action, valor=amounts[-1] if amounts else None,
                              destinatario=dest if action == "deposito" else None, fonte=source)
        if "limite" in text or source == "cartao":
            account = re.search(r"conta\s*(\d+)", text)
            return Solicitacao(acao="limite", conta=account[1] if account else None)
        if "saldo" in text or "saudo" in text:
            account = re.search(r"conta\s*(\d+)", text)
            return Solicitacao(acao="saldo", conta=account[1] if account else None)
        return Solicitacao(acao="ajuda")
