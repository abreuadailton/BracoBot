# RF01 — BracoBot: chat bancário local via CMD

| Campo | Definição |
| --- | --- |
| Versão | 1.1 — persistência local, cartão fictício e troca de conta |
| Autorização | Usuário: “resolva tudo e ja crie o agente” |
| Ambiente | Windows, Python local; Strands Agents SDK e OpenAI |
| Escopo bancário | Simulação com dados fictícios; saldos, crédito e lançamentos persistidos em SQLite |
| Identidade | BracoBot, assistente de IA de banco fictício |
| Documento anterior | [Histórico v0.3](RF01-historico-v0.3.md) |
| System prompt | [bracobot/system_prompt.md](../bracobot/system_prompt.md) |

## 1. Requisito principal

O sistema deve oferecer um chat em português brasileiro no CMD, executado localmente
em Python. O BracoBot deve usar o Strands Agents SDK com OpenAI para interpretar
solicitações e encaminhá-las a ferramentas bancárias locais, sujeitas a validação
determinística de identidade, autorização, parâmetros, orçamento e confirmação humana.

Somente resultados do simulador podem representar saldo, extrato ou conclusão de
uma movimentação. A saída livre do modelo não deve ser apresentada como resultado
bancário. O modelo propõe uma intenção estruturada; o programa executa ferramentas
e apresenta respostas, esclarecimentos e confirmações verificáveis.

O usuário confirmou: depósito significa transferência entre contas; o próprio
cliente autenticado confirma saque e depósito; o limite de sete refere-se a erros.
Posteriormente, solicitou persistência entre sessões, uso de cartão com limite
fictício por usuário e troca de conta sem fechar a aplicação. Essas solicitações
substituem a decisão anterior de não persistir operações e de desabilitar crédito.

## 2. Fontes e cobertura do Canvas

- [Canvas do agente, slide 1](../anexos/Canvas-do-Agente-Individual-editavel%20%281%29.pptx).
- [OWASP Agentic Skills Top 10 fornecido](../anexos/ast10-top10-whitepaper-2.pdf), 66 páginas.
- [OWASP Top 10 for Agentic Applications 2026, publicação oficial](https://genai.owasp.org/2025/12/09/owasp-top-10-for-agentic-applications-the-benchmark-for-agentic-security-in-the-age-of-autonomous-ai/).
- [Provedor OpenAI do Strands](https://strandsagents.com/docs/user-guide/sdk/model-providers/openai/).
- [Modelo e preços de referência](https://developers.openai.com/api/docs/models/gpt-5.4-nano).

O anexo OWASP é **Agentic Skills Top 10 (AST)**; a referência complementar de aplicações
usa **ASI**. São classificações distintas. O mapeamento não constitui certificação.

| Box do Canvas | Aplicação na versão inicial |
| --- | --- |
| Identificação | BracoBot. “Equipe Bradesco” é referência do Canvas; a aplicação identifica explicitamente o banco como fictício. |
| 01 — Objetivo | Saldo, limite do cartão, extrato, consulta de depósitos, transferência/depósito e saque simulados, usando saldo ou crédito fictício. |
| 02 — Quem usa | Cliente fictício autenticado; acesso apenas à própria conta. |
| 03 — Entradas | Chat em português. CPF/PIN em fluxo local separado, sem envio ao modelo. Erros linguísticos podem ser interpretados; identificadores e valores não podem ser corrigidos silenciosamente. |
| 04 — Tools e permissões | ValidarCPF, Saldo/limite e Extrato somente leitura; Depósito e Saque alteram o livro fictício local por transação atômica. Lista fechada e parâmetros validados. |
| 05 — Dados sensíveis | Somente identidades de teste. PIN e chave OpenAI não entram no contexto ou auditoria. Sem cartão real, CVC ou credenciais bancárias reais. |
| 06 — Nunca faz | Não movimenta sem autenticação, autorização e confirmação válida. Não acessa contas reais ou dinheiro real. |
| 07 — Humano no loop | Cliente revisa resumo estruturado, usa `/confirmar` ou pedido direto `confirmar` e revalida seu PIN fora do modelo. O programa vincula o identificador da operação pendente automaticamente. |
| 08 — Orçamento | 60 segundos de processamento acumulado, sete erros técnicos, tokens limitados e teto local de custo calculado de R$ 0,05 por intenção. |
| Governança — Papéis | Bradesco, CEO/CFO e Suporte permanecem referências do exercício. No protótipo, o operador local administra, monitora e interrompe o programa. |
| Governança — Impacto | Consultas autônomas após login; transferência e saque requerem confirmação. Saque sem saldo emite alerta. |
| Governança — Limites | Sete erros não são sete chamadas. Limites de ferramentas, tempo, tokens e custo são independentes. |

## 3. Registro das decisões — D01 a D13

| ID | Decisão final |
| --- | --- |
| D01 | Simulação local com OpenAI real. Modo adicional `--demo` somente para diagnóstico, sem OpenAI, identificado explicitamente. |
| D02 | Saldos, crédito utilizado e lançamentos são persistidos em `dados/bracobot.sqlite3`. Reinício, saída e login preservam o livro fictício. Valores iniciais são aplicados somente na primeira criação. Consulta de depósitos filtra o extrato persistido. |
| D03 | Depósito e transferência são a mesma operação, entre contas fictícias 1001, 1002 e 1003. Destinatário informado por nome ou conta; sem PIX real ou modalidade externa. |
| D04 | Transferência e saque podem usar saldo ou cartão fictício. Limites: Ana R$ 2.000, Bruno R$ 1.500, Carla R$ 1.000. Crédito usado reduz o limite disponível e não debita saldo da origem; transferência credita saldo ao destinatário. Fonte padrão é saldo; crédito precisa ser solicitado e mostrado no resumo. Tarifas/juros fictícios zero; sem pagamento de fatura ou recomposição automática de limite. |
| D05 | Confirmação explícita por `/confirmar` ou intenção local equivalente, sem ID digitado, e PIN do cliente após o resumo. Um `sim` durante oferta de crédito apenas aceita a fonte; após resumo, inicia a confirmação com PIN. O identificador da única operação pendente é vinculado pelo programa. Aprovação única, válida por 120 segundos; alteração exige cancelar e preparar novamente. |
| D06 | Sete erros técnicos acumulados por intenção. Inclui falhas de rede/API e saída inválida do modelo. Saldo insuficiente, cancelamento e esclarecimento não incrementam esse contador. Falhas não recuperáveis encerram antes; não há obrigação de repetir sete vezes. |
| D07 | Modelo `gpt-5.4-nano-2026-03-17`, reasoning `none`, resposta até 512 tokens. Entrada até 1.024 tokens por mensagem e contexto enviado até 8.192 tokens. Preços/câmbio em `config.toml`; teto calculado de R$ 0,05. Sem troca automática de modelo. |
| D08 | 60 segundos acumulados de processamento por intenção, incluindo rede, retries e operações locais; espera por esclarecimento e confirmação fica excluída. |
| D09 | CPF fictício + PIN de teste em entrada oculta; validação de CPF não substitui autenticação. Sessão de 15 minutos, três falhas de credencial geram bloqueio de 60 segundos. PIN revalidado na confirmação. `/trocar` exige novo CPF/PIN e invalida contexto e pendências anteriores, sem encerrar o aplicativo ou apagar o livro. |
| D10 | Auditoria técnica e contexto somente em memória; nenhum log/transcrição é gravado em arquivo pelo aplicativo. Ao modelo vão somente instruções e mensagens de solicitação já filtradas, nunca credenciais, extratos ou saldos retornados pelas ferramentas. |
| D11 | Operador da máquina administra o protótipo. Alertas no CMD, `/auditoria` para eventos técnicos, `/sair` ou Ctrl+C para parada. Não há escalonamento corporativo externo. |
| D12 | Extrato persistido padrão de 30 dias, máximo 90; dez lançamentos por página, com fonte saldo/cartão. Máximo de dez intenções por minuto e sessenta por sessão. Até seis mensagens para esclarecer uma intenção. Saque: três invocações por intenção. Consulta `/limite` usa a quota de Saldo, sem inferência. |
| D13 | Operações concluídas e seus identificadores são persistidos; um mesmo identificador/intenção não pode reaplicar débitos. Aprovações pendentes, autenticação e contexto permanecem efêmeros e não são restaurados. SQLite serializa escritas e revalida saldo/limite antes do commit, inclusive entre janelas. |

O modelo selecionado consta como *deprecated* na documentação consultada, embora
a página documente Chat Completions e o snapshot. Sua disponibilidade para a chave
do usuário depende do provedor. A aplicação informa indisponibilidade sem trocar
de modelo. Uma migração exige revisar preço, parâmetros e os testes de integração.

## 4. Requisitos funcionais

| ID | Comportamento |
| --- | --- |
| RF01.01 | Abrir no CMD com nome BracoBot, aviso de IA, simulação e identificação do modo OpenAI ou demonstração. |
| RF01.02 | Manter conversa em português e reconhecer pedidos diretos equivalentes aos comandos locais, como `quero entrar`, `trocar de conta`, `me ajuda`, `confirmar`, `cancelar`, `mostrar auditoria` e `quero sair`. Preservar os comandos com barra. Intenções de confirmação negadas, citadas ou compostas não autorizam movimentações. |
| RF01.03 | Interpretar erros linguísticos, pedir esclarecimento de valores/destinatários e aceitar uma intenção por vez. Mapear nomes exatos conhecidos para as contas correspondentes, sem adivinhar nomes desconhecidos. Ao pedir um valor faltante, preservar destinatário, origem e fonte; uma resposta somente numérica completa o rascunho local sem reinterpretar esses campos. Valores monetários são decimais, sem separador de milhar, até duas casas. |
| RF01.04 | Autenticar fora do chat por CPF/PIN fictícios; restringir coleta de segredos a terminal interativo. |
| RF01.05 | Validar identidade e conta antes de toda consulta, preparação e execução; origem informada pelo modelo não concede acesso. |
| RF01.06 | Manter contexto somente enquanto uma intenção está em andamento. Logout/novo login/troca de conta invalida contexto e aprovações, preservando saldos e lançamentos persistidos. |
| RF01.07 | Consultar saldo disponível e limite fictício da própria conta. Consulta de cartão apresenta limite total, utilizado e disponível, sem revelar crédito de terceiros. |
| RF01.08 | Consultar extrato persistido por dias e página, incluindo fonte dos recursos; distinguir extrato vazio de erro. |
| RF01.09 | Consultar depósitos pelo filtro do extrato; mostrar lançamentos da própria conta, incluindo débitos de transferência e créditos recebidos. |
| RF01.10 | Preparar transferência ou saque validando valor positivo, fonte, saldo ou limite disponível, conta e destinatário. Se faltar saldo na transferência, oferecer crédito somente quando o limite cobrir o valor integral; nunca trocar automaticamente. O aceite mantém valor/destino e prepara resumo com cartão, sem executar. Recusa, cancelamento, expiração de 120 segundos ou troca de conta invalidam a oferta. Limite é revalidado ao aceitar e ao gravar. |
| RF01.11 | Exibir resumo local estruturado e exigir confirmação única pelo cliente, com PIN, em até 120 segundos. Texto gerado pelo modelo não aprova. Pedidos diretos do cliente são reconhecidos pelo terminal, sem delegar confirmação ao LLM. |
| RF01.12 | Revalidar sessão, PIN, orçamento, prazo, conta e saldo/limite antes de gravar. Aplicar débito ou consumo de crédito, crédito ao destinatário e lançamentos numa transação SQLite indivisível; erro antes do commit reverte todos os efeitos. |
| RF01.12a | Saque com fonte saldo debita a conta e exibe `Dinheiro sacado com sucesso! (Saldo)` somente após persistência bem-sucedida. No cartão explícito, identificar a fonte como Crédito. |
| RF01.13 | Exibir comprovante fictício derivado da operação local concluída; nunca inventar sucesso a partir da fala do modelo. |
| RF01.14 | Cancelar invalida aprovação pendente. Sair, EOF e Ctrl+C impedem novas ações e descartam contexto/autenticação, preservando operações já concluídas. |
| RF01.15 | Exibir falha compreensível sem resposta bruta, credencial ou stack trace do provedor. Falhas de autenticação OpenAI e modelo indisponível não são repetidas automaticamente. |
| RF01.16 | Aplicar limites no executor e na porta de saída HTTP, incluindo chamadas internas do SDK. Esclarecimentos preservam orçamento e contadores da intenção. |
| RF01.17 | Recusar ferramentas/capacidades não habilitadas. Não carregar skills ou executar shell, código, arquivos ou URLs sugeridos na conversa. |
| RF01.18 | Registrar decisões e resultados técnicos em memória; permitir visualização resumida e parada local independente do modelo. |

## 5. Ferramentas e contratos de execução

O Strands usa a saída estruturada `Solicitacao`, definida com Pydantic. Ela permite
somente ações enumeradas e campos conhecidos. Não possui campo para autorizar,
confirmar, alterar política ou executar código. O executor chama as ferramentas
locais abaixo; o modelo não recebe uma ferramenta que efetive movimentação.

| Ferramenta | Contrato e permissão | Limite por intenção |
| --- | --- | --- |
| ValidarCPF | Validar CPF de teste no login. PIN é verificado separadamente pelo autenticador. Não é exposta ao modelo. | 1 |
| Saldo | Ler saldo ou limite total/utilizado/disponível da conta autenticada; conta diferente é negada. | 3 |
| Extrato | Ler conta autenticada, dias 1–90, página positiva e filtro de depósitos. | 3 |
| Depósito | Preparar transferência entre contas fictícias distintas, financiada por saldo ou cartão da origem. Efetivar somente pelo comando local de confirmação. | 10 |
| Saque | Preparar saque fictício por saldo ou cartão da própria conta, sem destinatário. Confirmar localmente. | 3 |

Preparação e confirmação consomem, cada uma, uma invocação da respectiva ferramenta.
O limite de chamadas não autoriza repetir o efeito financeiro da mesma intenção.
Valores aceitos: de R$ 0,01 a R$ 100.000,00, sujeitos ao saldo ou limite disponível.
O resumo deve distinguir a conta de origem da fonte dos recursos e mostrar se o
valor será debitado da conta ou lançado no cartão. Não coletar número de cartão/CVC.

As identidades e saldos iniciais são fixos para testes: Ana/1001/R$ 1.000,00,
Bruno/1002/R$ 500,00 e Carla/1003/R$ 250,00. Os dados de acesso estão no README e
não representam autenticação bancária real. Não há comando no chat para listar
CPFs e PINs. Limites iniciais de cartão:
Ana R$ 2.000, Bruno R$ 1.500 e Carla R$ 1.000. Os valores iniciais não são reaplicados
a cada abertura. Ambos os modos, OpenAI e demonstração, compartilham o livro local.

### 5.1 Persistência local

O arquivo SQLite contém contas fictícias, saldos em centavos inteiros, limites,
crédito usado, operações concluídas e lançamentos. Não armazena CPF, PIN, chave
OpenAI, conversas ou aprovações pendentes. A pasta `dados/` é excluída do Git.

Escritas usam `BEGIN IMMEDIATE`, validação do saldo/limite atual e commit atômico.
Contadores de orçamento e a validade da aprovação são revalidados após adquirir
o lock e antes do commit. Consultas leem o estado salvo, sem cache de saldos entre
janelas. Idempotência é assegurada por identificadores únicos no banco.

Banco indisponível, corrompido ou com versão incompatível não deve provocar reset
ou substituição silenciosa. O arquivo não é criptografado; contém apenas dados
fictícios e depende das permissões do sistema operacional. Operações da versão
anterior, mantidas apenas em memória, não são migradas automaticamente.

## 6. Orçamento, erros e encerramento

Cada intenção recebe um identificador, contador de erros, contadores por ferramenta,
tempo ativo acumulado e reserva cumulativa de custo. Uma nova intenção começa quando
a anterior termina ou é cancelada; não há reset por tentativa interna do SDK.

Antes de cada chamada OpenAI, a aplicação:

1. Verifica prazo, erros e contexto.
2. Reserva custo de entrada usando o tamanho do payload em bytes UTF-8 mais margem
   de 2.048 tokens de enquadramento, e saída máxima de 512 tokens.
3. Calcula USD pela tabela configurada, converte por R$ 7,00/USD e aplica margem de 20%.
4. Bloqueia a chamada quando a reserva acumulada ultrapassaria R$ 0,05.
5. Impõe timeout pelo tempo restante e desabilita retries ocultos do SDK/cliente.
6. Registra uso retornado quando disponível; não devolve reserva após falha ou sucesso.

Esse é um **teto local calculado pelos preços e câmbio configurados**, não uma garantia
de valor da fatura: preço, câmbio efetivo, tributos e tokenização do provedor podem
variar. Não há consulta cambial externa nem promessa de retenção zero pela OpenAI.
O custo local do simulador é zero; o modo `--demo` não faz chamadas pagas.

Falhas transitórias podem ser repetidas sob os mesmos limites. Ao sétimo erro,
o processamento termina. Chamadas bem-sucedidas não contam como erros. Erro
irrecuperável, tempo/custo/rota excedido ou autorização inválida pode encerrar antes.
Uma confirmação ou mudança de saldo nunca ocorre após retorno de modelo vencido.

Para esgotamento, manter a mensagem do Canvas: “Por favor, tente novamente mais tarde!”,
acompanhada do motivo útil. Falha de resultado da simulação não permite inventar
comprovante ou repetir uma aprovação já consumida.

## 7. Segurança, governança e OWASP

- Autenticação, autorização, confirmação, orçamento e idempotência são código
  independente do prompt. A origem efetiva vem da sessão local.
- Segredos são capturados sem eco e sem envio ao LLM. A chave é lida de
  `OPENAI_API_KEY` no ambiente ou no `.env` da raiz, nessa ordem, ou pode ser digitada
  no início. O programa não grava nem exibe a chave; outras variáveis do `.env` não
  são importadas para o processo.
- Entrada é limitada e rejeita caracteres de controle/invisíveis, CPF, cartão,
  chaves e padrões de credenciais. Essa detecção é proteção adicional e não
  reconhece todo segredo possível; a interface orienta uso exclusivo de dados fictícios.
- Respostas bancárias são locais; nem saldo nem extrato são enviados ao modelo.
- OpenAI usa endpoint fixo, TLS, sem proxy do ambiente ou redirecionamento.
  `store=false` não equivale a garantia contratual de retenção zero.
- Não há shell, navegador, acesso genérico a arquivos, skills, plugins dinâmicos,
  outros agentes ou ferramentas de instalação disponíveis ao modelo.
- Telemetria de conteúdo do SDK é desabilitada. Auditoria própria usa campos
  permitidos, sem payloads bancários, prompts ou segredos.
- Eventos técnicos são encadeados com hash em memória. Isso ajuda a detectar
  alteração acidental, mas não resiste a um operador que controla o processo e
  não oferece comprovação independente ou retenção corporativa.
- Configuração e prompt são arquivos administrativos. O agente não os modifica.
  Dependências diretas e transitivas possuem versões fixadas no lock.
- Não há sandbox de código de terceiros. Skills executáveis continuam desabilitadas.
  A adoção futura requer revisão de procedência, isolamento e permissões.

| OWASP Agentic Skills (anexo) | Aplicação |
| --- | --- |
| AST01 — Malicious Skills | Carregamento dinâmico desabilitado; saída do modelo não executa código. |
| AST02 — Supply Chain Compromise | Versões fixadas e sem instalação pelo agente. Assinatura de pacote/skills e revisão de supply chain completa não são afirmadas. |
| AST03 — Over-Privileged Skills | Executor com lista fechada, conta vinculada à sessão e sem shell. |
| AST04 — Insecure Metadata | Contrato Pydantic rejeita campos desconhecidos; configurações TOML validadas. |
| AST05 — Untrusted External Instructions | Texto de usuário é dado não confiável; sem busca de instruções remotas. |
| AST06 — Weak Isolation | Contexto e aprovações por sessão; livro compartilhado com autorização por conta. Sem execução de skills de terceiros. |
| AST07 — Update Drift | Modelo snapshot e versões fixadas; mudança exige revisão e testes. |
| AST08 — Poor Scanning | Testes negativos de autorização, saída inválida, segredos, limites e falhas. Não se afirma avaliação completa de resistência do modelo a injeção. |
| AST09 — No Governance | Responsável local, auditoria em memória e parada independente do LLM. |
| AST10 — Cross-Platform Reuse | Versão validada no Windows; portabilidade de skills não habilitada. |

| OWASP Agentic Applications | Controle |
| --- | --- |
| ASI01 — Agent Goal Hijack | Prompt delimita papel; validação de ações fora do modelo. |
| ASI02 — Tool Misuse and Exploitation | Contratos restritos e confirmação local. |
| ASI03 — Identity and Privilege Abuse | CPF/PIN de teste, expiração, bloqueio e autorização por conta. |
| ASI04 — Agentic Supply Chain Vulnerabilities | Lock de dependências e ausência de instalação dinâmica. |
| ASI05 — Unexpected Code Execution | Sem ferramentas de execução de código/shell. |
| ASI06 — Memory & Context Poisoning | Contexto limitado à intenção, sem memória persistente; reset ao entrar novamente. |
| ASI07 — Insecure Inter-Agent Communication | Não aplicável: agente único, sem delegação. |
| ASI08 — Cascading Failures | Sete erros, timeout, orçamento, retries observáveis e confirmação de uso único. |
| ASI09 — Human-Agent Trust Exploitation | Resumo e comprovante determinísticos; confirmação não interpretada pelo LLM. |
| ASI10 — Rogue Agents | Sem acesso a configurações, parada local e bloqueio por política. |

## 8. Aceite e validação

| Grupo | Evidência esperada |
| --- | --- |
| Conversa | Inicialização pelo CMD, modo identificado, português e ajuda. |
| Autenticação | CPF válido sem PIN correto não concede acesso; três falhas bloqueiam; sessão expira. |
| Isolamento | Tentativa de consultar/debitar outra conta falha; destinatário não tem seu saldo exposto. |
| Confirmação | Preparar não altera saldo; PIN/ID inválido, aprovação expirada ou antiga não executam. |
| Movimentação | Transferir debita/credita exatamente uma vez; saque reduz apenas saldo fictício; saldo insuficiente bloqueia. |
| Contexto | Esclarecimentos mantêm orçamento e os campos já coletados. Pedir transferência para Ana e responder somente `25` preserva Ana como destino. Cancelamento/troca de conta descarta rascunhos e aprovações, sem apagar o livro persistido. |
| Persistência | Novo processo preserva saldos, crédito usado e lançamentos; replay não reaplica operação; arquivo inválido não é sobrescrito. |
| Crédito | Fonte explícita no resumo; valor usado reduz limite, sem debitar saldo; exceder limite é negado; crédito de outra conta é inacessível. |
| Oferta de crédito | Transferência sem saldo oferece crédito disponível; aceite não executa antes de resumo/PIN; recusa, expiração e troca de conta invalidam oferta; consumo concorrente de limite impede a conclusão. |
| Comandos naturais | Pedidos diretos funcionam sem barra; negação não confirma; `sim` na oferta apenas aceita a fonte; confirmação após resumo ainda exige PIN. |
| Concorrência | Duas janelas não gastam o mesmo saldo ou limite; falha antes de commit reverte todos os efeitos. |
| Limites | Oitava chamada bem-sucedida não é bloqueada por sete erros; sétimo erro encerra; quotas por rota continuam independentes. |
| Tempo | Espera humana excluída; resultado de modelo que chega após 60 segundos não é executado. |
| Custo | Próxima chamada acima da reserva é bloqueada antes do HTTP. |
| Proteção de dados | Segredos e controles invisíveis rejeitados; PIN e CPF do login ausentes do payload OpenAI. |
| Integração | Strands real com provedor OpenAI, HTTP simulado nos testes, contrato e parâmetros verificados. |
| Falhas | HTTP 401 sem retry, HTTP 500 contabilizado, saída estruturada inválida limitada a sete erros. |
| Auditoria | Falha de auditoria antes da movimentação bloqueia alteração; campos sensíveis não são aceitos. |

Os testes automatizados estão em [tests/test_bracobot.py](../tests/test_bracobot.py).
A suíte atual tem 68 testes aprovados, com HTTP simulado nos cenários automatizados
e bancos SQLite temporários que não alteram os dados do usuário.
Uma consulta de saldo fictício também foi concluída com Strands e OpenAI reais,
usando a chave do `.env` sem exibi-la. Isso valida o caminho básico de integração;
os demais cenários de falha continuam cobertos por testes com transporte simulado.
Também foi validada uma transferência com cartão interpretada pela OpenAI real,
confirmada em banco temporário e consultada após trocar de conta, sem alterar
os saldos persistidos do usuário.

## 9. Limites desta entrega

Este é um protótipo local. PINs públicos de teste, auditoria efêmera e ausência de
integração bancária não servem como autenticação ou governança de produção.
Há persistência de um livro inteiramente fictício, sem aprovação institucional presumida. O operador da
máquina pode alterar arquivos; o programa não é uma barreira contra seu administrador.

Não restam decisões de produto bloqueando a primeira versão. Alterações futuras
em regras de crédito, armazenamento, modelo, dados reais ou integrações bancárias exigem revisão
do escopo, dos controles e dos critérios de aceite.
