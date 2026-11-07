# BracoBot

Chat bancário fictício em português, no CMD do Windows, escrito em Python.
O modo normal usa **Strands Agents SDK + OpenAI**. Contas, saldos, cartões,
transferências e saques são simulados. **Saldos, crédito utilizado e lançamentos
permanecem salvos entre sessões**, no banco SQLite local `dados/bracobot.sqlite3`.

## Executar

O ambiente `.venv` já foi preparado nesta máquina com Python 3.14.

1. Abra **`iniciar.cmd`**.
2. A chave `OPENAI_API_KEY` é lida primeiro do ambiente e depois do arquivo `.env`
   na raiz do projeto. Se não estiver configurada, informe-a na entrada oculta de
   inicialização. O programa não grava nem exibe a chave. Não a cole na conversa.
3. Digite `/entrar` e use um dos CPFs/PINs fictícios abaixo, também em entrada oculta.
4. Converse normalmente: `qual meu saldo?`, `transfira 25,50 para Bruno`,
   `transfira 50 para Bruno usando o cartão`, `saque de 10 no cartão`,
   `qual meu limite?` ou `extrato dos últimos 30 dias`.

Para testar sem chave e sem custo, execute **`demonstracao.cmd`**. Esse modo é
explicitamente identificado como demonstração **sem OpenAI** e usa interpretação
limitada por regras. O modo normal não troca silenciosamente para demonstração.
Ambos os modos usam o mesmo banco fictício persistido neste computador.

Em outra máquina, instale Python 3.12 ou superior e execute `instalar.cmd`.
As versões foram validadas em **Windows com Python 3.14**. A instalação usa
`requirements-lock.txt`, incluindo dependências transitivas e pytest, e prepara
o tokenizer. Ela precisa de rede; o modo demonstração não chama APIs após isso.

Também é possível executar no CMD:

```bat
.venv\Scripts\python.exe -m bracobot
.venv\Scripts\python.exe -m bracobot --demo
```

Não é necessário configurar conta AWS, Amazon Bedrock ou credencial bancária.

O `.env` aceita `OPENAI_API_KEY=sua_chave` e está excluído do Git. Apenas essa chave
é lida; outras variáveis do arquivo não alteram endpoints, telemetria ou políticas.

## Contas de demonstração

| Cliente | Conta | CPF de teste | PIN público de teste | Saldo inicial | Limite do cartão |
| --- | --- | --- | --- | --- | --- |
| Ana | 1001 | 00000000191 | 2468 | R$ 1.000,00 | R$ 2.000,00 |
| Bruno | 1002 | 00000000272 | 1357 | R$ 500,00 | R$ 1.500,00 |
| Carla | 1003 | 00000000353 | 8642 | R$ 250,00 | R$ 1.000,00 |

Essas credenciais pertencem somente ao cenário fictício. Não consulte cadastros
reais nem use CPF, senha ou cartão reais. CPF válido, sozinho, não autentica.
Os saldos e limites iniciais são aplicados somente na primeira criação do banco,
não a cada login. O cartão fictício é vinculado à conta: não há número de cartão
ou CVC para informar.

Depois de `transfira 25,50 para Bruno`, o programa apresenta origem, destinatário,
valor, fonte dos recursos e tarifa zero. Para executar a operação pendente, sem copiar identificador:

```text
/confirmar
```

Você também pode dizer `confirmar`. Informe novamente o PIN na entrada oculta.
Um `sim` após o resumo inicia essa mesma confirmação com PIN; sozinho não executa
a movimentação. Durante a oferta de crédito, `sim` apenas aceita a fonte e abre o resumo.
O modelo não recebe o PIN e não pode executar `/confirmar` por você.
O programa vincula a confirmação à única operação pendente; o identificador continua
sendo usado internamente e aparece no comprovante após a conclusão.
Partindo do saldo inicial, após essa confirmação o saldo de Ana será R$ 974,50.
Sair, reiniciar ou trocar de conta preserva o resultado e os lançamentos.

Você também pode informar os dados em etapas: `faça uma transferência para Bruno`
e, quando o agente perguntar o valor, responder apenas `25`. O destinatário e a
fonte de recursos já informados são preservados. Nomes conhecidos são vinculados
às contas correspondentes; nomes desconhecidos não são corrigidos ou adivinhados.

## Usar cartão e trocar de conta

Peça explicitamente a fonte de recursos:

```text
transfira 50 para Bruno usando o cartão
saque 20 no cartão de crédito
qual meu limite?
```

Sem pedir cartão, a operação usa saldo em conta. Saldo insuficiente não causa troca
automática para crédito. Se faltar saldo numa transferência e o limite do cartão
cobrir o valor inteiro, o agente oferece usar crédito. Responda `usar crédito` ou
`sim` para revisar a operação; `não` ou `cancelar` para desistir. A oferta expira
em 120 segundos. O limite é revalidado ao aceitar e ao concluir, e não há débito
parcial em saldo: o valor inteiro é lançado no cartão.
O resumo mostra a fonte escolhida antes de `confirmar` ou `/confirmar`, sempre com PIN.
Operações no cartão aumentam o crédito utilizado e reduzem o limite disponível,
sem debitar o saldo da conta de origem. Em uma transferência, o destinatário recebe
saldo em conta. Tarifas e juros fictícios são zero; pagamento de fatura e recomposição
do limite ainda não fazem parte do simulador. O crédito utilizado não zera ao sair.

Use **`/limite`** para consultar total, utilizado e disponível sem chamar a OpenAI.
Use **`/trocar`** e informe o CPF/PIN da outra conta para continuar na mesma janela.
A troca cancela operações pendentes e apaga o contexto da conversa anterior, mas
preserva todas as operações já concluídas. Outra conta não pode aprovar a pendência
do cliente anterior.

Para um saque com saldo, diga `quero sacar 25`. Após conferir o resumo e confirmar
com seu PIN, R$ 25,00 são debitados da conta e o agente exibe
**“Dinheiro sacado com sucesso! (Saldo)”**. A mensagem só aparece depois da gravação
da operação. Saque com saldo insuficiente continua bloqueado; a oferta de crédito
automática é exclusiva de transferências.

## Comandos

A barra é opcional para os pedidos diretos reconhecidos. Exemplos: `quero entrar`,
`trocar de conta`, `me ajuda`, `confirmar`, `quero cancelar essa operação`,
`mostrar auditoria`, `qual é o meu limite?`, `começar de novo` e `quero sair`.
Negações, perguntas sobre como confirmar e comandos citados não confirmam uma
movimentação. Autenticação e PIN continuam sendo solicitados pelo terminal.
Também são aceitos atalhos financeiros como `/saldo`, `/extrato`, `/saque 25`
e `/transferir 50 para Bruno`.

| Comando | Efeito |
| --- | --- |
| `/entrar` | Autenticar; renova a sessão e o contexto, preservando saldos e crédito. |
| `/trocar` | Entrar em outra conta com CPF/PIN, sem fechar o aplicativo; cancela pendências. |
| `/limite` | Consultar limite total, utilizado e disponível do cartão da conta autenticada. |
| `/ajuda` | Listar capacidades e exemplos. |
| `/confirmar` ou `confirmar` | Confirmar a única operação pendente com PIN, sem informar ID; prazo de 120 segundos. |
| `/cancelar` | Invalidar intenção e confirmação pendentes. |
| `/novo` | Abandonar esclarecimentos e iniciar uma nova intenção. |
| `/auditoria` | Mostrar os últimos eventos técnicos da sessão, sem dados bancários. |
| `/sair` ou Ctrl+C | Encerrar e invalidar pendências; operações concluídas continuam salvas. |

## Limites definidos

- Autenticação por 15 minutos. Três falhas de credencial bloqueiam por 60 segundos.
- Sete **erros técnicos** acumulados por intenção; chamadas bem-sucedidas não contam.
- Até 60 segundos acumulados de processamento, sem contar espera humana.
- Entrada de até 1.024 tokens; contexto de até 8.192; saída do modelo de até 512.
- Até seis mensagens para esclarecer uma intenção, dez intenções/minuto e sessenta/sessão.
- Saldo e Extrato: três chamadas; Depósito: dez; Saque: três por intenção.
  Preparação e confirmação são contadas separadamente.
- Extrato persistido: padrão 30 dias, máximo 90, dez lançamentos por página.
- Transferência/saque com saldo ou cartão fictício; nunca com dinheiro ou cartão real.

O teto local calculado é **R$ 0,05 por intenção**. O programa reserva um custo
conservador antes de cada chamada, usando preços de `config.toml`, R$ 7,00/USD e
margem de 20%. Reservas não são devolvidas após falhas, pois a API pode ter cobrado.
O valor não é garantia de fatura: preços, câmbio e impostos efetivos podem variar.
Chamadas são bloqueadas quando não cabem no saldo do orçamento.

O modelo fixado é `gpt-5.4-nano-2026-03-17`, com preços de referência de
US$ 0,20/1M tokens de entrada e US$ 1,25/1M de saída. A
[documentação consultada](https://developers.openai.com/api/docs/models/gpt-5.4-nano)
marca esse modelo como deprecated; disponibilidade depende da conta/provedor.
O aplicativo não faz fallback automático. Trocar de modelo requer rever os preços,
parâmetros e a validação em `Settings.load`, além de executar os testes.

## Organização e segurança

- `bracobot/system_prompt.md`: instruções do agente.
- `bracobot/router.py`: Strands, provedor OpenAI, contrato estruturado e porta HTTP com orçamento.
- `bracobot/bank.py`: autenticação de teste, regras bancárias e confirmação.
- `bracobot/storage.py`: SQLite, saldos, limites, crédito utilizado e lançamentos atômicos.
- `bracobot/policy.py`: limites, filtragem e auditoria técnica em memória.
- `bracobot/cli.py`: conversa, comandos locais e apresentação determinística.
- `config.toml`: configuração administrativa, sem segredos.
- `requisitos/RF01-chat-bancario-bracobot.md`: requisito final e decisões D01–D13.

O modelo interpreta a intenção; o código autoriza a operação. Não existem ferramentas
de shell, acesso genérico a arquivos, navegação, instalação de skills ou confirmação
expostas ao modelo. Saldos, extratos e comprovantes são apresentados diretamente pelo
simulador, sem passar pela geração de texto da OpenAI.

A chave OpenAI sai somente no cabeçalho de autenticação para `api.openai.com`.
O aplicativo desabilita exportação de telemetria do SDK, proxies do ambiente,
redirecionamentos e retries ocultos. `store=false` não garante retenção zero
contratual pela OpenAI. Mensagens válidas do chat são enviadas para inferência.

Saldos, crédito e movimentações são gravados em `dados/bracobot.sqlite3`, sem PIN,
CPF, chave OpenAI ou histórico de conversa. A pasta `dados/` está excluída do Git.
Transferências salvam débito/crédito e lançamentos em uma única transação SQLite.
O saldo/limite é revalidado durante a gravação, inclusive com mais de uma janela aberta.
Se o arquivo estiver indisponível ou corrompido, o programa informa a falha sem
reiniciar silenciosamente os valores. Não há criptografia do arquivo; ele contém
somente dados do simulador e fica sujeito às permissões da máquina.

Não há gravação de auditoria técnica ou conversa em arquivo. Auditoria em memória
encadeada por hash não é evidência independente contra o dono da máquina.
PINs são públicos e a finalidade é demonstração; não é um banco de produção.

Esta persistência vale para as operações feitas na nova versão. Movimentações
da versão anterior que existiam apenas em memória não são importadas automaticamente.
Reabra `iniciar.cmd` para usar a versão atualizada; janelas antigas continuam com
o código anterior.

## Validação

```bat
.venv\Scripts\python.exe -m pytest tests\test_bracobot.py -q
.venv\Scripts\python.exe -m pip check
```

Os testes exercitam autorização, confirmação única, expiração, bloqueios,
persistência após reinício, cartão, troca de conta, concorrência, rollback,
valores inválidos, segredos, quotas, timeout, custo e falhas de API.
Usam o **Strands e o cliente OpenAI reais com transporte HTTP simulado**, sem
consumo de tokens pagos. Cada teste usa um banco temporário e não altera
`dados/bracobot.sqlite3`.

Na validação atual: 68 testes aprovados. As dependências foram verificadas (`pip check`)
e inicialização/ajuda/saída verificadas através de `cmd.exe` e `demonstracao.cmd`.
Há também testes de leitura do `.env`, precedência do ambiente e ausência de efeitos
colaterais sobre outras variáveis do processo.

Uma consulta de saldo fictício também foi validada com a OpenAI real, usando a chave
local sem exibi-la: o modelo interpretou o pedido e o executor retornou o saldo de
R$ 1.000,00 da conta de teste. O controle local reservou R$ 0,01677816; o custo
calculado a partir do uso retornado foi R$ 0,00204414, incluindo câmbio e margem
configurados. Esses valores são estimativas locais, não valores de fatura.

A opção de cartão também foi validada com OpenAI real, em um banco temporário:
transferir R$ 12,50 para Bruno preservou o saldo de Ana, consumiu R$ 12,50 do
crédito e creditou Bruno. A troca de conta permitiu consultar o resultado. Esse
teste não alterou o arquivo de dados do usuário.
