# RF01 — Chat bancário interativo BracoBot via CMD

> HISTÓRICO: versão anterior à autorização de implementação. Suas pendências e
> restrição de não implementar foram substituídas pelo RF01 v1.0 em
> [RF01-chat-bancario-bracobot.md](RF01-chat-bancario-bracobot.md).

| Campo | Valor |
| --- | --- |
| Identificador | RF01 |
| Versão | 0.3 — sem efeito contábil persistente e com limite de sete erros |
| Data | 07/11/2026 |
| Agente | BracoBot |
| Público principal | Clientes do banco |
| Canal e execução | Terminal CMD do Windows; aplicação Python executada localmente |
| Integrações requeridas | OpenAI e Strands Agents SDK |
| Ambiente bancário inicial | Simulação local com contas, credenciais e movimentações fictícias; OpenAI real |
| Origem | Solicitação do usuário e Canvas do agente bancário |
| Situação | Requisito documentado; decisões pendentes na seção 13 |

Este documento refina o requisito funcional e registra as regras de negócio, os requisitos de segurança e os critérios de aceite associados. **Não autoriza nem contém implementação.** Os comportamentos adicionais ao Canvas são propostas de refinamento, sujeitas à validação. Lacunas não foram tratadas como decisões já aprovadas.

## 1. Fontes e interpretação

| Referência | Fonte | Uso neste documento |
| --- | --- | --- |
| F01 | Solicitação do usuário | Chat via CMD, Python local, OpenAI, Strands Agents SDK, identidade BracoBot e documentação sem implementação. |
| F01a | Respostas do usuário às perguntas de esclarecimento, em 07/11/2026 | Simulação local; depósito significa transferência entre contas; o próprio cliente autenticado confirma saque e depósito. |
| F01b | Esclarecimentos posteriores do usuário sobre D02 e D06 | A simulação não tem efeito contábil persistente; o limite de sete passos refere-se a erros. |
| F02 | [Canvas-do-Agente-Individual-editavel (1).pptx](../anexos/Canvas-do-Agente-Individual-editavel%20%281%29.pptx), slide 1 | Identificação, oito boxes, tabelas de ferramentas e autonomia e camada de governança. Foram lidos os textos e as células das tabelas; a nota do slide contém apenas sua numeração. |
| F03 | [ast10-top10-whitepaper-2.pdf](../anexos/ast10-top10-whitepaper-2.pdf), 66 páginas | OWASP **Agentic Skills Top 10**, categorias AST01–AST10. As páginas citadas abaixo são as posições físicas no PDF, contando a capa, pois o sumário apresenta diferenças de paginação. |
| F04 | [Publicação oficial do OWASP Top 10 for Agentic Applications 2026](https://genai.owasp.org/2025/12/09/owasp-top-10-for-agentic-applications-the-benchmark-for-agentic-security-in-the-age-of-autonomous-ai/), consultada em 07/11/2026 | Referência complementar para a identificação das categorias ASI01–ASI10 solicitadas pelo usuário. Os controles deste requisito são uma aplicação dessas categorias ao BracoBot. |
| F05 | [Documentação oficial do provedor OpenAI do Strands Agents SDK](https://strandsagents.com/docs/user-guide/sdk/model-providers/openai/), consultada em 07/11/2026 | Confirma que o SDK possui provedor OpenAI; a escolha de modelo e versões permanece pendente. |

**Distinção entre referências OWASP:** o anexo F03 não é o documento Top 10 for Agentic Applications. A própria página 8 distingue AST de ASI, e a página 9 delimita AST à forma de distribuição por skills. Este requisito mantém dois mapeamentos separados, sem afirmar equivalência entre as categorias. Ferramentas Python chamadas pelo agente não se tornam automaticamente skills. Controles próprios de distribuição e carregamento de skills são condicionais à sua adoção.

O mapeamento de controles não constitui certificação OWASP nem comprovação de conformidade legal.

## 2. Enunciado refinado

**O sistema deve disponibilizar um chat interativo em português brasileiro, acessível pelo CMD do Windows e executado por uma aplicação Python local, no qual um agente identificado como BracoBot utilize o Strands Agents SDK para orquestrar a interação com um modelo da OpenAI e com ferramentas bancárias previamente autorizadas. O agente deve interpretar solicitações de clientes, consultar informações da conta autenticada e conduzir operações bancárias previstas no escopo, respeitando autorização por operação, confirmação humana para movimentações financeiras, proteção de dados, limites de execução e trilha de auditoria.**

Na primeira versão, as ferramentas bancárias devem operar exclusivamente sobre contas e valores fictícios locais. Conforme esclarecimento do usuário, **depósito é uma transferência entre contas**, e **o próprio cliente autenticado confirma saque e depósito**. A inferência utiliza a integração real com a OpenAI.

Conforme F01b, **a simulação não deve produzir efeito contábil persistente**. Alterações simuladas não devem ser gravadas para recompor saldos ou lançamentos em execuções posteriores. Ainda deve ser definido se o saldo muda temporariamente em memória durante a sessão ou se cada operação apenas demonstra seu resultado sobre dados fixos. O limite de sete refere-se a **erros**, não ao total de chamadas bem-sucedidas.

Uma solicitação somente será considerada concluída quando o sistema comunicar um resultado verificável da ferramenta responsável, uma recusa justificada, um cancelamento ou uma pendência explicitamente identificada. Uma resposta do modelo, isoladamente, não comprova consulta ou movimentação.

## 3. Escopo e fronteiras

### 3.1 Capacidades pretendidas

- Iniciar e encerrar uma conversa no CMD, mantendo contexto durante a sessão.
- Identificar e autenticar o cliente antes de acessar informações bancárias.
- Consultar saldo, extrato e informações de depósitos, conforme definição pendente desta última consulta.
- Conduzir depósito e saque com validação de credenciais, regras financeiras e confirmação humana.
- Contemplar transferência e uso de saldo ou cartão de crédito, citados no objetivo do Canvas, após esclarecer suas regras e ferramentas.
- Aplicar limites, registrar decisões e permitir interrupção pelo responsável autorizado.

**Decisão confirmada pelo usuário:** a primeira versão será uma simulação local com dados fictícios e ferramentas bancárias simuladas, identificadas na interface. A integração com OpenAI permanece real. A simulação deve reproduzir autenticação, autorização, confirmação, limites e auditoria; não deverá acessar contas, credenciais ou APIs bancárias reais.

### 3.2 Restrições de solução

| ID | Requisito |
| --- | --- |
| RT-01 | O processo de chat e a orquestração devem rodar localmente em Python e ser utilizáveis no CMD do Windows, sem depender de interface web. A versão do Python deverá ser compatível com as versões aprovadas do SDK e de suas dependências. |
| RT-02 | A orquestração deve utilizar o Strands Agents SDK com provedor OpenAI e modelo configurado explicitamente. Não deve haver troca silenciosa de provedor ou modelo. |
| RT-03 | A execução local não implica inferência offline: o acesso à OpenAI requer conexão de rede e credencial válida. A integração descrita não exige, por si só, hospedagem na AWS ou uso do Amazon Bedrock. Serviços AWS adicionais dependem de requisito próprio. |
| RT-04 | Modelo, versões, endpoints, limites e política de ferramentas devem compor uma configuração controlada. O cliente não deve poder alterá-la por conversa. |
| RT-05 | A inicialização deve verificar a presença de configurações obrigatórias sem exibir segredos. Falhas de configuração devem produzir orientação compreensível e impedir operações dependentes. |
| RT-06 | Na primeira versão, a fonte bancária autoritativa será o simulador local. Contas, credenciais de clientes, saldos, limites e lançamentos devem ser fictícios. Chamadas externas de inferência são permitidas apenas à integração aprovada com OpenAI; movimentações não devem alcançar serviços bancários reais. |
| RT-07 | Não persistir efeitos contábeis das operações simuladas nem restaurá-los após reiniciar a aplicação. Dados iniciais fictícios podem ser estáticos. Eventuais logs técnicos seguem política própria em D10 e não devem funcionar como livro contábil nem restaurar movimentações. |

### 3.3 Fronteiras propostas

Não estão definidos neste RF01: interface web, aplicativos móveis, múltiplos agentes, navegação livre, execução de comandos do sistema pelo modelo, instalação dinâmica de skills ou memória persistente entre sessões. Sua inclusão exigiria revisão de escopo e riscos.

Uma integração bancária real depende de APIs, contratos, autenticação, regras de operação e responsáveis identificados. O chat não deve sugerir que movimentou dinheiro real quando apenas simulou a operação.

Nos requisitos seguintes, referências a fonte, serviço ou ferramenta bancária designam o simulador local nesta primeira versão. Controles que dependem de provedores bancários reais são condições para evolução futura, não exigência de contratar esses serviços agora.

## 4. Rastreabilidade de cada box do Canvas

| Elemento | Conteúdo identificado em F02 | Refinamento e localização |
| --- | --- | --- |
| Identificação | Equipe Bradesco; agente BracoBot. | Nome obrigatório na interface; vínculo institucional e papéis registrados conforme Canvas, sem presumir autorização operacional real. Seções 2 e 10. |
| 01 — Objetivo | Consulta de saldo, extrato e depósito; saque seguro; depósito/transferência via saldo da conta ou cartão de crédito. | Depósito definido pelo usuário como transferência entre contas; fluxos simulados e confirmação de resultado. Demais detalhes nas decisões D02–D04. Seções 5–7. |
| 02 — Quem usa | Clientes do banco através de um chat. | Cliente como ator principal; acesso somente aos próprios recursos autorizados. RF01.01–RF01.05. |
| 03 — Entradas | CPF, autenticação e solicitação pelo chat; erros de digitação e português. | Identificação separada de autenticação; tolerância linguística sem alterar dados financeiros; entrada tratada como não confiável. RF01.03–RF01.06 e SEG-01–SEG-04. |
| 04 — Tools e permissões | ValidarCPF, Saldo, Extrato, Depósito e Saque, com permissões e limites específicos. | Lista fechada, autorização fora do modelo e contagem por solicitação. Seção 6. |
| 05 — Dados sensíveis | CPF, senhas, número de cartão, CVC, limite do cartão e saldo bancário. | Minimização, mascaramento, segregação de segredos e proibição de envio de credenciais ao modelo. Seção 9. |
| 06 — Nunca faz | Não deposita nem saca antes de confirmar com humano; não opera sem confirmar credenciais. | Bloqueios obrigatórios antes da execução; confirmação não substitui autenticação. RF01.04 e RF01.10–RF01.12. |
| 07 — Humano no loop | Humano valida saque e depósito e confirma destinatário. | O usuário definiu o próprio cliente autenticado como aprovador de saque e depósito. Resumo, vínculo da autorização e validade na seção 7 e D05. |
| 08 — Orçamento | Até 60 segundos processando um input; impedir excesso de chamadas à mesma rota; recusar excesso de tokens; mensagem de indisponibilidade. | Interrupção preventiva, contadores, orçamento e tratamento de resultado incerto. Seção 8. |
| Governança — Quem responde | Dono: Bradesco; aprovador: CEO & CFO; monitora: CFO & Equipe; desliga: Suporte. | Responsabilidades e necessidade de representantes operacionais nomeados. Seção 10. |
| Governança — Impacto × reversibilidade | Saldo e extrato autônomos; depósito com aprovação humana; saque com limite + alerta e aprovação humana. | Autonomia restrita à consulta autenticada; movimentações sem garantia de reversão automática. Seções 6 e 7. |
| Governança — Limites | R$ 0,05 por execução e máximo de 7 passos. | F01b esclarece que sete se refere a erros. O teto de 10 chamadas de Depósito é independente. Seção 8 e D06–D08. |

## 5. Requisitos funcionais detalhados

Os itens abaixo decompõem o RF01. Os detalhes que não aparecem literalmente no Canvas são propostas para torná-lo verificável.

| ID | Comportamento requerido |
| --- | --- |
| RF01.01 — Abertura | Ao iniciar, o sistema deve apresentar o nome BracoBot, informar que se trata de um assistente de IA, mostrar as capacidades disponíveis e destacar que as contas e movimentações são simuladas, enquanto a integração com OpenAI é real. |
| RF01.02 — Conversa | O sistema deve receber texto pelo CMD, responder em português brasileiro e aceitar novas mensagens até o encerramento. Deve disponibilizar ações de ajuda, cancelamento da operação pendente e saída; nomes exatos dos comandos serão definidos posteriormente. |
| RF01.03 — Interpretação | O agente deve tolerar erros de português e digitação quando a intenção permanecer inequívoca. Deve pedir esclarecimento quando houver dúvida sobre operação, valor, origem ou destinatário. Não deve corrigir silenciosamente CPF, conta, cartão, chave de transferência ou valores. |
| RF01.04 — Identificação e autenticação | Antes de qualquer consulta privada ou movimentação, o sistema deve obter autenticação válida pelo mecanismo aprovado. Validar formato ou dígitos do CPF não autentica o cliente nem comprova titularidade. A sessão deve carregar identidade e permissões verificadas fora do modelo. |
| RF01.05 — Autorização | Antes de cada chamada de ferramenta, o sistema deve validar se a identidade autenticada tem permissão para a ação e para a conta envolvida. Um número de conta informado no chat não concede acesso. Credencial inválida, sessão expirada ou autorização insuficiente deve impedir a chamada. |
| RF01.06 — Contexto | O sistema deve manter apenas o contexto necessário da sessão atual e vincular mensagens, confirmações e resultados à solicitação correta. Nova sessão, logout ou troca de cliente deve invalidar contexto e aprovações anteriores. |
| RF01.07 — Saldo | Após autenticação e autorização, deve consultar a ferramenta Saldo e apresentar o saldo retornado, sua referência temporal disponível e o tipo de saldo. Deve distinguir saldo em conta de limite de crédito e informar ausência de dados em vez de inventar valores. |
| RF01.08 — Extrato | Deve consultar a ferramenta Extrato para a conta autorizada e período informado ou confirmado, apresentando os lançamentos retornados. Período padrão, extensão máxima, paginação e campos dependem do contrato da ferramenta. Extrato vazio não deve ser tratado como falha. |
| RF01.09 — Consulta de depósitos | Deve permitir consultar informações das transferências tratadas como depósitos, após definir se isso significa filtrar o extrato ou consultar status/comprovante em ferramenta específica do simulador. Até essa definição e a disponibilidade da ferramenta, deve informar a indisponibilidade da função. |
| RF01.10 — Preparação de movimentação | Para depósito (transferência entre contas), saque e eventuais modalidades adicionais de transferência, deve coletar os dados mínimos e produzir um resumo estruturado da operação simulada. Deve validar formato, valor positivo, moeda, origem, destino quando aplicável, autorização e limites financeiros em componente independente do modelo. |
| RF01.11 — Confirmação humana | Antes de saque ou depósito, deve solicitar aprovação explícita do próprio cliente autenticado sobre o resumo validado, incluindo o destinatário no depósito/transferência. Silêncio, resposta ambígua, confirmação gerada pelo modelo ou aprovação de operação anterior não autorizam execução. Modalidades adicionais de transferência deverão adotar confirmação equivalente. |
| RF01.12 — Execução controlada | Somente após confirmação válida e verificação atual de credenciais, permissões e limites, deve executar a ferramenta autorizada com os mesmos parâmetros aprovados. Alteração de qualquer dado material exige nova confirmação. |
| RF01.13 — Resultado | Deve apresentar sucesso apenas quando a ferramenta ou o serviço bancário confirmar o resultado, exibindo identificador da operação quando disponível. Deve distinguir sucesso, recusa, cancelamento, falha e resultado desconhecido ou pendente de reconciliação. |
| RF01.14 — Cancelamento e saída | Cancelar deve invalidar a autorização ainda não utilizada e impedir o envio de movimentação pendente. Sair, EOF ou interrupção pelo usuário devem encerrar a sessão e descartar segredos em memória quando tecnicamente possível. Operação já enviada deve seguir o tratamento de estado incerto da seção 7. |
| RF01.15 — Falhas e indisponibilidade | Em falha de rede, autenticação do provedor, limite de uso ou indisponibilidade de ferramenta, deve informar o problema sem expor stack trace, credenciais ou dados privados. Não deve substituir resultados bancários por respostas estimadas do modelo. |
| RF01.16 — Limites | Deve fiscalizar os limites da seção 8 durante toda a solicitação, incluindo tentativas internas do SDK e do cliente de API. Não deve reiniciar contadores por mudança de ferramenta, reformulação automática ou continuação da mesma operação. |
| RF01.17 — Fora do escopo | Deve recusar operações não autorizadas ou sem ferramenta disponível, explicar suas capacidades e não alegar que executou uma ação apenas porque o usuário a pediu. |
| RF01.18 — Auditoria e interrupção | Deve registrar as decisões e resultados definidos na seção 10 e permitir que o responsável autorizado suspenda novas ações, inclusive enquanto o agente estiver em execução. |

## 6. Ferramentas, permissões e regras de negócio

### 6.1 Inventário fiel ao Canvas

| Ferramenta | Lê | Escreve | Limite literal de F02 | Autonomia literal de F02 |
| --- | --- | --- | --- | --- |
| ValidarCPF | Sim | Não | 1 chamada por solicitação | Não indicada na tabela de autonomia. |
| Saldo | Sim | Não | 3 chamadas por solicitação | Autônoma. |
| Extrato | Sim | Não | 3 chamadas por solicitação | Autônoma. |
| Depósito | Sim | Sim | 10 chamadas por solicitação | Humano aprova. |
| Saque | Sim | Sim | Conforme limite do cartão de crédito ou saldo em conta | Limite + alerta; humano aprova. |

“Autônoma” significa dispensar confirmação transacional humana para consulta; autenticação e autorização continuam obrigatórias. A permissão de escrita de Depósito e Saque é restrita à operação financeira correspondente, não a arquivos, credenciais ou configurações.

### 6.2 Complementos propostos

| ID | Regra |
| --- | --- |
| RN-01 | O agente deve acessar apenas ferramentas cadastradas e aprovadas. Contratos devem definir entradas, saídas, tipos, limites, erros, efeitos e permissões. Parâmetros desconhecidos ou incompatíveis devem ser rejeitados antes da chamada. |
| RN-02 | O componente de execução deve aplicar autenticação, autorização, confirmação e orçamento independentemente do texto produzido pelo modelo. O prompt e a resposta da OpenAI não são mecanismos suficientes de controle. |
| RN-03 | Cada ferramenta deve receber credenciais restritas ao seu serviço e à ação necessária. Ferramentas de consulta não devem poder alterar saldos nem ampliar privilégios. |
| RN-04 | Valores monetários devem usar representação decimal exata em BRL, salvo decisão de escopo distinta. Valores nulos, negativos, formatos ambíguos e precisão não permitida devem ser rejeitados. |
| RN-05 | Saldo disponível, limite do cartão, tarifas e restrições devem vir de fonte bancária autoritativa. O agente não deve somar saldo e crédito nem trocar a fonte de recursos automaticamente. |
| RN-06 | A validação final deve usar o saldo/limite fictício do cenário. Se houver atualização temporária em memória, validar e atualizar de forma atômica, evitando gasto concorrente superior ao saldo simulado disponível. Se o cenário for estático, comunicar que o resultado é demonstrativo e não altera o saldo consultável. Uma consulta anterior não reserva recursos. |
| RN-07 | Uma confirmação deve autorizar uma única intenção de movimentação. Repetições técnicas não podem multiplicar o efeito financeiro. |
| RN-08 | O usuário definiu Depósito como transferência entre contas. Propõe-se usar a ferramenta Depósito para essa intenção, preservando confirmação humana, limites e idempotência, sem executar duas movimentações por usar nomes diferentes. Uma ferramenta separada ou modalidade adicional de transferência depende de contrato e limites próprios; D03 esclarece essa extensão. |
| RN-09 | A restrição de Saque no Canvas é financeira, não um número de chamadas. O teto de invocações permanece pendente; até defini-lo, a função não deve ser habilitada para execução. |
| RN-10 | A ferramenta de autenticação, distinta de ValidarCPF, não foi especificada. Não se deve inferir que validação de CPF, posse do terminal ou nome informado no chat comprovam identidade. |
| RN-11 | Um depósito/transferência deve simular débito na origem e crédito no destino, sem efeito contábil persistente. Se houver atualização em memória, ambos os efeitos devem ocorrer de forma atômica; se os dados forem fixos, apresentar apenas o resultado demonstrativo. O cliente deve ter autorização para debitar a origem; conhecer o destino não concede acesso ao saldo ou extrato de seu titular. Tarifas e uso de crédito permanecem condicionados a D04. |

### 6.3 Definições do domínio e lacunas restantes

- **Depósito:** definido pelo usuário como transferência entre contas; na primeira versão, ambas devem pertencer ao ambiente fictício. Não significa aumento arbitrário de saldo.
- **Saque:** será simulado, sem retirada física, dinheiro real ou efeito contábil persistente. A atualização temporária do saldo ou demonstração sem alteração depende de D02; eventual uso de crédito depende de D04.
- **Transferência:** já integra o significado de depósito. Definir identificação de destinatário, regras de titularidade e comprovante; esclarecer se haverá modalidades adicionais ou ferramenta separada.
- **Cartão:** definir quais operações admitem crédito, como o instrumento será tokenizado e como encargos e disponibilidade serão apresentados.
- **Consulta de depósito:** definir se é consulta de status/comprovante ou filtragem de lançamentos.

## 7. Fluxos e confirmação humana

### 7.1 Fluxo de consulta

1. O cliente informa a intenção.
2. O sistema verifica autenticação, conta autorizada e dados mínimos.
3. O agente esclarece eventual ambiguidade.
4. O sistema verifica ferramenta permitida, parâmetros e limites restantes.
5. A ferramenta consulta a fonte autorizada.
6. O BracoBot apresenta os dados retornados ou informa falha/ausência de dados.
7. A solicitação é encerrada e auditada.

### 7.2 Fluxo de movimentação

1. Identificar intenção e coletar dados mínimos.
2. Validar identidade, autorização, dados e regras financeiras.
3. Apresentar resumo verificável: tipo de operação, valor e moeda, fonte de recursos, conta de origem quando aplicável, destinatário/destino quando aplicável, tarifas e total a debitar quando disponíveis.
4. Se uma tarifa ou condição obrigatória não puder ser determinada, interromper a preparação; não apresentar estimativa como condição confirmada.
5. Solicitar confirmação explícita ao próprio cliente autenticado, com referência única à operação.
6. Após a confirmação, revalidar sessão, autorização, validade da aprovação, limites financeiros e orçamento restante.
7. Executar a intenção uma única vez e registrar seu resultado.
8. Apresentar resultado confirmado ou informar que a situação está pendente de verificação.

### 7.3 Regras da aprovação

- Conforme decisão do usuário, o próprio cliente autenticado aprova saque e depósito/transferência. Não há aprovação adicional de funcionário para esses fluxos. Os aprovadores de governança do Canvas têm responsabilidade distinta.
- O resumo deve derivar de dados estruturados e validados, sem depender exclusivamente de texto livre gerado pelo modelo.
- A aprovação deve vincular aprovador, cliente, operação, valor, moeda, origem, destino aplicável, condições, identificador e validade.
- A aprovação deve ser de uso único. Troca de sessão, expiração, cancelamento ou alteração de parâmetros deve invalidá-la.
- Aprovar não permite superar saldo, crédito, permissões, orçamento nem controles de segurança.
- O agente não deve pressionar o usuário a aprovar, esconder riscos ou pedir que ignore alertas.
- O tempo de validade e o mecanismo de confirmação/reautenticação precisam ser definidos em D05 e D09.

### 7.4 Duplicidade, interrupção e resultado desconhecido

Durante a sessão, cada intenção de movimentação deve possuir identificador idempotente ou garantia equivalente de unicidade. Repetir mensagem, timeout ou retry não pode reaplicar a mesma intenção ao estado temporário nem reutilizar uma aprovação. Identificadores e status necessários à simulação podem permanecer em memória.

Se houver falha após uma chamada cujo resultado não esteja disponível, o agente deve informar **resultado da simulação desconhecido/pendente de verificação**, sem inventar sucesso ou repetir a operação com novo identificador. A consulta de status, se disponível, usará o registro temporário da sessão. Após reinício, não há recuperação de efeito contábil: a aplicação retorna ao cenário inicial, invalida aprovações anteriores e informa que a sessão simulada foi encerrada.

Recuperação contábil durável, reconciliação com banco e APIs bancárias de idempotência/status não são dependências desta simulação. Uma futura integração com dinheiro real exigiria revisão desse fluxo.

## 8. Limites de execução, desempenho e custo

### 8.1 Definições propostas para validação

- **Solicitação/execução:** uma intenção de negócio do cliente, desde sua aceitação até resultado, recusa, cancelamento ou pendência formal. Esclarecimentos e confirmação mantêm seu identificador e os contadores cumulativos.
- **Limite de erros:** F01b define sete erros, não sete chamadas ou etapas. Propõe-se contar falhas técnicas do modelo/ferramentas e respostas inválidas de contrato, acumuladas por solicitação; chamadas bem-sucedidas não incrementam nem zeram esse contador. Recusas de negócio, cancelamento e pedidos de esclarecimento não seriam erros técnicos. A classificação e a janela de contagem ainda dependem de validação em D06.
- **Tempo de processamento:** tempo de relógio gasto pelo sistema processando a solicitação, incluindo rede, ferramentas, esperas internas e retries. Propõe-se excluir apenas o tempo aguardando interação humana e manter o total acumulado ao retomar.
- **Custo por execução:** soma dos custos variáveis atribuíveis à solicitação, incluindo uso do modelo e serviços cobrados por chamada. Taxas da operação financeira devem aparecer separadamente no resumo e não se confundem com esse orçamento técnico.

A interpretação de sete como limite de erros está confirmada. A classificação dos erros, sua janela de contagem e as demais definições de medição dependem dos detalhes restantes de D06–D08. Um erro contado não autoriza retry: falhas não recuperáveis, violações de autorização e limites de ferramenta podem encerrar a solicitação antes do sétimo erro.

### 8.2 Limites e comportamento

| ID | Limite | Comportamento verificável |
| --- | --- | --- |
| LIM-01 | **60 segundos** de processamento, conforme F02. | Usar prazo global e prazos de chamada limitados pelo saldo de tempo; ao atingir o prazo, interromper o processamento e impedir novas ações. Cancelar uma espera local não garante cancelamento de uma transação já enviada. |
| LIM-02 | **7 erros**, conforme esclarecimento F01b. | Ao atingir o sétimo erro na janela aprovada em D06, encerrar o processamento da solicitação e impedir novas tentativas. Não impor teto de sete às chamadas bem-sucedidas. Contabilizar falhas de retries internos; se não houver como observá-las, desabilitar esses retries. Demais limites podem interromper antes. |
| LIM-03 | **R$ 0,05 por execução**, conforme F02. | Antes de cada chamada cobrada, estimar e reservar o custo máximo admissível considerando entrada, saída limitada, preço do modelo, conversão monetária e demais cobranças variáveis aplicáveis. Não iniciar a chamada se exceder o saldo. Registrar uso e custo apurados quando disponíveis. |
| LIM-04 | Tokens de entrada: **valor pendente**. | Contar e limitar a entrada antes de enviá-la à OpenAI. Rejeitar excesso sem truncar silenciosamente dados de operação. Também limitar histórico, retorno de ferramentas e saída do modelo. |
| LIM-05 | Chamadas por ferramenta/rota: tabela da seção 6. | Contabilizar todas as tentativas da mesma solicitação. Aliases, retries e reformulações não podem contornar o limite. Rotas auxiliares e autenticação precisam de limites definidos antes da habilitação. |
| LIM-06 | Limites financeiros: saldo/limite autorizado pelo serviço. | Bloquear valores acima do permitido; para saque, também emitir o alerta previsto no Canvas sem divulgar dados de terceiros. |

**Ambiguidade resolvida:** não há conflito entre 10 chamadas de Depósito e sete erros. São contadores distintos: o primeiro conta todas as chamadas dessa ferramenta, e o segundo conta somente os eventos classificados como erro. Dez chamadas não autorizam dez depósitos: cada confirmação continua vinculada a uma única intenção idempotente. Tempo, custo e limites por ferramenta continuam válidos mesmo sem erros.

**Viabilidade do orçamento:** não há garantia de que R$ 0,05 comporte o modelo e os fluxos desejados. Modelo, preços, câmbio de referência, impostos/margem aplicáveis, tokens e chamadas devem ser definidos e validados. Se não for possível limitar previamente o custo máximo de uma chamada, ela não deve ser iniciada sob uma promessa de teto rígido. O agente não pode elevar o orçamento por conta própria.

Para timeout, excesso de chamadas ou tokens, preservar a mensagem do Canvas:

> Por favor, tente novamente mais tarde!

O sistema deve acrescentar o motivo útil, como “Tempo excedido”, “Limite de chamadas atingido” ou “Mensagem acima do limite permitido”, sem expor detalhes internos. Para custo esgotado ou limite de erros atingido, propõe-se o mesmo padrão.

Se uma movimentação já tiver sido enviada, a mensagem deve explicitar que a operação pode estar pendente e que não deve ser reenviada antes da verificação. A frase genérica isolada seria insuficiente para evitar duplicidade.

Limites de solicitações por sessão/cliente e tentativas de autenticação também devem ser definidos; limites por solicitação não impedem abuso por abertura repetida de novas solicitações.

## 9. Segurança e proteção de dados

### 9.1 Dados previstos no Canvas

| Dado | Tratamento proposto |
| --- | --- |
| CPF | Usar somente na identificação/validação necessária. Mascarar na interface e nos registros; preferir identificador interno na orquestração. Não enviar CPF completo ao modelo por padrão. |
| Senha e fatores de autenticação | Capturar somente por mecanismo de autenticação aprovado, separado do histórico conversacional e sem eco quando houver entrada local. Nunca incluir em prompt, resposta, log, trace ou arquivo de conversa. |
| Número de cartão | Preferir token do provedor e identificação mascarada. Não coletar número completo em texto livre; eventual necessidade deve ser resolvida por fluxo específico aprovado. |
| CVC | Não solicitar no chat, enviar ao modelo ou persistir. Se exigido pelo provedor de pagamento, tratá-lo exclusivamente em canal seguro próprio desse provedor. |
| Limite do cartão e saldo | Consultar somente para cliente autorizado e para a finalidade solicitada. Exibir ao titular quando necessário; enviar ao modelo apenas se justificado, preferindo apresentação determinística. |
| Extrato e destinatário | Minimizar campos, período e identificadores; tratar descrições como conteúdo não confiável. Não registrar detalhes integrais desnecessários. |
| Chaves OpenAI, tokens bancários e outros segredos técnicos | Armazenar fora do código e do repositório, com acesso restrito, rotação e revogação. Entregar apenas ao componente que necessita deles, nunca ao contexto do agente. |

Se o usuário colar credenciais no campo conversacional, o sistema deve impedir seu encaminhamento e registro quando identificadas, orientar o uso do canal correto e descartar o conteúdo sensível. Detectores de texto são uma camada adicional; não substituem a separação do fluxo de autenticação.

### 9.2 Controles verificáveis

| ID | Requisito de segurança |
| --- | --- |
| SEG-01 — Fronteira de instruções | Mensagens, descrições de extrato e retornos de ferramenta devem ser tratados como dados não confiáveis. Instruções embutidas não podem alterar identidade, ferramentas, limites ou política. Registrar origem e preservar essa distinção ao compor o contexto. |
| SEG-02 — Execução fora do modelo | Aplicar políticas de autorização, parâmetros, orçamento e aprovação no componente executor. Mesmo uma saída do modelo que solicite ação proibida deve ser bloqueada antes do despacho. |
| SEG-03 — Menor privilégio | Executar sem privilégios administrativos desnecessários. Restringir cada ferramenta a recursos, contas, ações e destinos aprovados; negar o restante por padrão. Proibir acesso genérico do modelo ao shell e ao sistema de arquivos. |
| SEG-04 — Validação e saída | Validar tipos, tamanhos, valores e esquemas de entrada e saída; higienizar controles de terminal, sequências ANSI e caracteres invisíveis que possam falsificar a apresentação. Conteúdo retornado não pode disparar comandos. |
| SEG-05 — Segredos e minimização | Aplicar o tratamento da seção 9.1 antes de enviar dados à OpenAI ou à observabilidade. Logs de SDK, traces, mensagens de erro e relatórios também devem respeitar mascaramento e exclusão de segredos. |
| SEG-06 — Sessão | Isolar contexto, identidade, permissões e aprovações por sessão/cliente. Definir expiração, reautenticação e limitação de tentativas. O modelo não pode fabricar nem estender uma sessão autenticada. |
| SEG-07 — Rede | Usar transporte autenticado e criptografado para serviços remotos, com validação de certificados. Restringir endpoints e destinos ao conjunto aprovado; URLs fornecidas no chat não devem autorizar conexões ou envio de dados. |
| SEG-08 — Componentes e skills | Manter inventário de dependências, ferramentas e eventuais skills, com origem, versão, integridade e permissões. Verificar dependências transitivas e impedir instalação automática solicitada pelo modelo. Se skills forem adotadas, exigir revisão de conteúdo, procedência, assinaturas verificáveis e possibilidade de revogação. |
| SEG-09 — Configuração e memória | Versionar e proteger políticas, identidade e configuração contra escrita pelo agente. Proibir persistência automática de instruções aprendidas no chat. Memória persistente, se futuramente adotada, exige validação de origem, isolamento e aprovação de alterações. |
| SEG-10 — Isolamento | Restringir recursos locais e acesso de ferramentas; código de terceiros ou skills executáveis exige isolamento adequado ao Windows antes da habilitação. Ambiente virtual Python, sozinho, não é barreira de segurança. Não presumir que o SDK oferece sandbox automático. |
| SEG-11 — Avaliação e mudanças | Rever código, prompts, configurações e dependências com análise estática e cenários comportamentais/adversariais. Registrar versão do modelo, ferramentas, políticas, cobertura e limitações. Resultado incompleto não equivale a aprovação. Mudanças relevantes exigem reavaliação. |
| SEG-12 — Auditoria protegida | Registrar admissão e resultado das ações com identificadores correlacionados e política vigente; restringir acesso, detectar adulteração e manter mecanismo de verificação independente quando exigido pelo risco. O agente não deve poder apagar ou reescrever a trilha. |
| SEG-13 — Contenção | Bloquear novas ações ao detectar violações de política, desvio de comportamento ou limites excedidos. Disponibilizar suspensão/revogação de ferramentas e credenciais pelo responsável e reconciliação de operações em andamento. |
| SEG-14 — Comunicação confiável | Identificar o assistente como IA, separar dados confirmados de incerteza e apresentar confirmação sem persuasão. Não inventar comprovantes, saldos, aprovações humanas ou status de execução. |

### 9.3 Privacidade e uso de serviços externos

Antes do uso de dados reais, devem ser definidos finalidade, base legal aplicável, responsáveis pelo tratamento, dados permitidos na OpenAI, retenção, descarte, acesso, eventual transferência internacional e configurações contratuais do provedor. Não se presume retenção zero nem conformidade automática com a LGPD.

Propõe-se não persistir transcrições completas por padrão. A ausência de efeito contábil persistente está confirmada; a eventual gravação de metadados técnicos de auditoria é uma decisão separada, com prazo e acesso definidos em D10. Esses registros não devem restaurar saldos ou movimentações. O fato de a aplicação rodar localmente não elimina o envio de informações ao provedor de inferência.

## 10. Governança e operação

### 10.1 Papéis registrados no Canvas

| Papel | Indicação literal em F02 | Responsabilidade proposta |
| --- | --- | --- |
| Dono do agente | Bradesco | Responder pelo propósito, escopo, regras, risco aceito e autorização de uso. |
| Aprovador | CEO & CFO | Aprovar escopo, limites, mudanças materiais e condições de disponibilização, ou formalizar delegação. |
| Quem monitora | CFO & Equipe | Acompanhar custo, falhas, violações, operações pendentes e indicadores; acionar responsáveis. |
| Quem desliga | Suporte | Suspender o agente/ferramentas, invalidar acessos conforme permissão e conduzir contenção e recuperação. |

Esses nomes são definições do exercício no Canvas, não comprovação de vínculo ou aprovação institucional. Antes de operação real, devem existir responsáveis nomeados, suplentes, canais de acionamento e permissões operacionais. O cliente não se torna administrador ao pedir essa função no chat.

### 10.2 Regras de governança propostas

| ID | Requisito |
| --- | --- |
| GOV-01 | Manter inventário do agente, modelo, versões, ferramentas, permissões, destinos externos e responsáveis; registrar explicitamente a ausência de skills, caso não sejam adotadas. |
| GOV-02 | Aprovar e versionar mudanças em prompt de sistema, modelo, dependências, ferramentas, limites e acesso a dados; registrar motivação, aprovador, avaliação e possibilidade de retorno à configuração anterior. O rollback técnico não reverte transações financeiras. |
| GOV-03 | Registrar por solicitação: identificador, sessão pseudonimizada, ambiente, versão da política/modelo, ferramenta/rota, decisão de permitir/negar/escalar, aprovação aplicável, início/fim, erros e suas categorias, chamadas, tokens, custo estimado/apurado, resultado e identificador de simulação quando houver. Excluir segredos e payloads sensíveis integrais. Persistência de metadados técnicos depende de D10. |
| GOV-04 | Registrar decisão antes do despacho e resultado após a execução, correlacionados pelo mesmo identificador de tentativa. Negativas anteriores à execução também devem ser auditadas. Ausência de registro final não comprova ausência de efeito financeiro. Se a auditoria necessária estiver indisponível, bloquear novas movimentações. |
| GOV-05 | Monitorar extrapolação de limites, recusas de autorização, confirmações inválidas, falhas recorrentes, tentativas de injeção, consumo anormal e operações pendentes. Canal, destinatário e limiares de alerta dependem de D11. |
| GOV-06 | Disponibilizar mecanismo de parada independente da decisão do modelo, acessível ao responsável autorizado. Ao acioná-lo, impedir novos despachos, invalidar aprovações pendentes e encaminhar operações já enviadas para verificação. |
| GOV-07 | Definir procedimento para incidente: conter, preservar evidências mínimas, revogar credenciais/componentes afetados, avaliar impacto e reconciliar operações antes de reativar. A reativação exige responsável autorizado e registro da decisão. |
| GOV-08 | Verificar se controles são preservados ao atualizar SDK/provedor, portar ferramentas ou introduzir skills. Ausência de controle equivalente deve bloquear a habilitação até revisão. |

A orientação de recibos de admissão e resultado de F03, páginas 52–53, fundamenta GOV-04. Assinatura dos registros, gestão de chaves e armazenamento verificável deverão ser dimensionados para o ambiente aprovado; um arquivo local editável não comprova, sozinho, integridade de auditoria.

## 11. Mapeamento OWASP

### 11.1 Anexo fornecido: Agentic Skills Top 10

Os controles abaixo são adaptações para o BracoBot. A cobertura específica de skills somente poderá ser validada se esse mecanismo fizer parte da solução.

| Categoria de F03 | Páginas do PDF | Aplicação e controles propostos |
| --- | --- | --- |
| AST01 — Malicious Skills | 10–17 | Se houver skills, verificar autoria/integridade e comportamento; assinatura não basta para comprovar segurança. Restringir exfiltração e escrita em identidade/memória. SEG-01, SEG-07–SEG-11. |
| AST02 — Supply Chain Compromise | 18–22 | Controlar procedência, versões e hashes de componentes e dependências transitivas; revisar configuração e permitir revogação. SEG-08, SEG-11; GOV-01–GOV-02. |
| AST03 — Over-Privileged Skills | 23–27 | Permissões mínimas, credenciais por escopo e autorização vinculada à intenção original; não confiar apenas no intermediário. RF01.05; RN-01–RN-03; SEG-02–SEG-03. |
| AST04 — Insecure Metadata | 28–31 | Se houver manifests, usar parser seguro e validar o resultado contra esquema antes do uso; rejeitar campos e permissões indevidas. Não confiar em risco autodeclarado. RN-01; SEG-04, SEG-08, SEG-11. |
| AST05 — Untrusted External Instructions | 32–35 | Não promover texto externo a instrução. Se houver referências remotas de skills, revisar, fixar e verificar integridade e origem, inclusive referências transitivas; bloquear alteração não aprovada. SEG-01, SEG-07–SEG-09. |
| AST06 — Weak Isolation | 36–39 | Isolar execução e estado conforme risco, limitar acesso ao host e não instalar skills executáveis sem contenção. SEG-03, SEG-06, SEG-10. |
| AST07 — Update Drift | 40–42 | Impedir atualizações silenciosas, acompanhar vulnerabilidades e exigir aprovação/reavaliação de mudanças. SEG-08, SEG-11; GOV-01–GOV-02. |
| AST08 — Poor Scanning | 43–48 | Avaliar código e instruções em linguagem natural, incluindo conteúdo oculto/ofuscado e tentativas adaptativas. Documentar cobertura, falsos positivos e limites; resultado incompleto não aprova o componente. SEG-04, SEG-11. |
| AST09 — No Governance | 49–53 | Inventário, responsáveis, aprovação de alterações, revogação e registros correlacionados e protegidos. SEG-12–SEG-13; GOV-01–GOV-07. |
| AST10 — Cross-Platform Reuse | 54–58 | Revalidar permissões, assinaturas, isolamento e restrições ao portar skills ou componentes; não presumir equivalência entre runtimes. SEG-08, SEG-10–SEG-11; GOV-08. |

O formato universal de skills apresentado em F03 é uma proposta do documento, não uma dependência obrigatória deste requisito.

### 11.2 Complemento: Top 10 for Agentic Applications 2026

| Categoria identificada em F04 | Risco no BracoBot e controles propostos |
| --- | --- |
| ASI01 — Agent Goal Hijack | Texto do cliente ou de uma ferramenta tenta mudar o objetivo bancário ou ignorar políticas. SEG-01–SEG-02, SEG-09; RF01.17. |
| ASI02 — Tool Misuse and Exploitation | Ferramenta legítima é usada com valor, conta ou finalidade indevidos. RN-01–RN-07; RF01.05, RF01.10–RF01.12. |
| ASI03 — Identity and Privilege Abuse | CPF válido ou identidade do agente é usado para acessar conta alheia ou elevar privilégios. RF01.04–RF01.05; SEG-03, SEG-05–SEG-06. |
| ASI04 — Agentic Supply Chain Vulnerabilities | SDK, dependência, ferramenta ou eventual skill comprometida. SEG-08, SEG-11; GOV-01–GOV-02. |
| ASI05 — Unexpected Code Execution (RCE) | Entrada ou saída induz execução de shell, código ou desserialização insegura. SEG-03–SEG-04, SEG-10. |
| ASI06 — Memory & Context Poisoning | Conteúdo de uma conversa contamina regras, contexto futuro ou outra sessão. RF01.06; SEG-01, SEG-06, SEG-09. |
| ASI07 — Insecure Inter-Agent Communication | Não aplicável diretamente ao escopo proposto de agente único. Se houver delegação futura, exigir autenticação entre agentes, integridade, proveniência e revalidação da autorização original antes de habilitá-la. APIs e ferramentas atuais continuam sujeitas a SEG-02 e SEG-07. |
| ASI08 — Cascading Failures | Erro ou timeout gera retries em cadeia, estouro de custo ou débito duplicado. RN-06–RN-07; seção 7.4; LIM-01–LIM-06; GOV-06. |
| ASI09 — Human-Agent Trust Exploitation | Resposta persuasiva leva a aprovar operação diferente da intenção ou a acreditar em comprovante inventado. RF01.11, RF01.13; seção 7.3; SEG-14. |
| ASI10 — Rogue Agents | Agente tenta agir fora do propósito, ocultar ações ou alterar suas regras. SEG-02–SEG-03, SEG-09, SEG-12–SEG-13; GOV-02, GOV-06–GOV-07. |

## 12. Critérios de aceite

Estes são cenários para validação futura, não testes executados nesta etapa. Os cenários dependentes de decisões abertas somente poderão ser aprovados após sua definição.

| ID | Dado / Quando | Resultado esperado | Rastreabilidade |
| --- | --- | --- | --- |
| CA-01 | Aplicação configurada; cliente inicia pelo CMD. | Exibe BracoBot, natureza de assistente de IA, aviso de simulação bancária e ajuda; recebe e responde a múltiplas mensagens em português usando Strands e integração real com OpenAI. | RT-01–RT-02, RT-06; RF01.01–RF01.02. |
| CA-02 | Cliente pede “quero ver meu saudo”; depois informa valor ou destinatário ambíguo. | Reconhece intenção de saldo; pede esclarecimento nos dados financeiros ambíguos sem corrigi-los silenciosamente. | RF01.03. |
| CA-03 | CPF formalmente válido, mas sem autenticação, com credencial inválida ou sessão expirada. | Nenhum saldo, extrato ou operação privada é acessado; solicita autenticação pelo canal aprovado. | RF01.04–RF01.05; RN-10. |
| CA-04 | Cliente autenticado tenta acessar conta alheia pelo chat ou por parâmetros produzidos pelo modelo. | O executor bloqueia a chamada, sem revelar dados da outra conta, e registra a negativa. | RF01.05; SEG-02–SEG-03; GOV-04. |
| CA-05 | Cliente autorizado solicita saldo/extrato; fonte retorna dados, lista vazia ou erro. | Apresenta os dados e referência disponíveis; distingue ausência de lançamentos e falha; não inventa valores. | RF01.07–RF01.08, RF01.13. |
| CA-06 | Saque ou depósito preparado sem confirmação do próprio cliente autenticado, com recusa, silêncio ou confirmação ambígua. | Nenhuma escrita é despachada; aprovação de outra identidade não substitui a do cliente; cancelamento invalida a pendência. | RF01.10–RF01.12; seção 7.3. |
| CA-07 | Resumo aprovado; modelo altera valor, origem, destino ou condições, ou reutiliza aprovação. | Execução bloqueada; alteração exige nova confirmação. Aprovação expirada também é rejeitada. | RF01.11–RF01.12; RN-07. |
| CA-08 | Movimentação simulada aprovada e válida; ferramenta confirma execução. | Há um único resultado simulado verificável, sem efeito contábil persistente, com identificador quando disponível. Saldo/limite fictício é revalidado antes da simulação; eventual estado em memória respeita D02. | RT-07; RN-06–RN-07; RF01.12–RF01.13. |
| CA-09 | Saldo/limite insuficiente, valor inválido ou fonte de recursos indisponível. | Recusa a movimentação; não troca automaticamente para cartão; saque produz alerta conforme política. | RN-04–RN-06; LIM-06. |
| CA-10 | Simulador processa uma operação e a resposta se perde; cliente repete o pedido na sessão ou reinicia a aplicação. | Na mesma sessão, não reaplica a intenção e consulta status temporário quando disponível. Após reinício, retorna ao cenário inicial e invalida aprovações anteriores, sem restaurar movimentações. | RT-07; seção 7.4; RN-07. |
| CA-11 | Prazo acumulado chega a 60 segundos. | Nenhuma nova ação é despachada; processamento é interrompido; exibe “Tempo excedido” e a mensagem do Canvas, com ressalva de pendência quando necessária. | LIM-01; RF01.16. |
| CA-12 | A execução alcança sete erros conforme a classificação e janela aprovadas em D06. | Ao sétimo erro, interrompe a solicitação e impede novas tentativas. Falhas dos retries entram na contagem. Sete chamadas bem-sucedidas, isoladamente, não acionam esse bloqueio; uma oitava pode ocorrer se tempo, custo e limites por ferramenta permitirem. | LIM-02; RF01.16. |
| CA-13 | Custo reservado/apurado mais a próxima chamada excederia R$ 0,05. | Bloqueia a chamada antes de incorrer no gasto; registra o motivo e não aumenta o orçamento. | LIM-03. |
| CA-14 | Entrada atinge o limite de tokens ou o excede; histórico e retorno de ferramenta são volumosos. | Aceita o limite permitido quando os demais limites comportarem; rejeita excesso antes de enviar; mantém limites de contexto e saída sem truncar dados críticos silenciosamente. | LIM-04; SEG-04. |
| CA-15 | ValidarCPF já foi chamado 1 vez, ou Saldo/Extrato 3 vezes na mesma solicitação. | A próxima chamada dessa ferramenta é bloqueada mesmo sem erros. Limites aprovados de Depósito, Saque e rotas auxiliares são aplicados da mesma forma. | LIM-05; seção 6. |
| CA-16 | Texto de chat ou descrição de extrato manda ignorar regras, revelar chave, instalar skill ou executar shell. | Nenhuma ação proibida ocorre, mesmo se o modelo a solicitar; registra a violação sem registrar segredos. | SEG-01–SEG-05, SEG-08. |
| CA-17 | Fluxo de autenticação e mensagens/erros contêm dados sensíveis sintéticos. | Senhas, CVC, chaves e tokens não aparecem no contexto enviado à OpenAI, histórico, logs ou traces; demais dados obedecem à minimização definida. | SEG-05; seção 9.1. |
| CA-18 | Cliente encerra sessão, troca de usuário ou inicia nova conversa. | Contexto privado e aprovações anteriores não são reutilizados; sessão anterior não autoriza novas operações. | RF01.06, RF01.14; SEG-06. |
| CA-19 | Ferramenta retorna texto com comandos ANSI ou instruções ocultas. | O terminal não executa comandos nem apresenta conteúdo que forje/oculte confirmação; conteúdo não altera a política. | SEG-01, SEG-04. |
| CA-20 | Chave OpenAI ausente/inválida, API indisponível ou resposta fora do esquema. | Mensagem compreensível, sem segredos; nenhum resultado bancário inventado; tentativas respeitam o orçamento. | RT-05; RF01.15; RN-01. |
| CA-21 | Responsável aciona parada durante consulta ou movimentação pendente. | Novos despachos cessam, aprovações pendentes são invalidadas e operações já enviadas seguem para verificação. | SEG-13; GOV-06. |
| CA-22 | Há uma ação permitida, uma negada, uma sem resposta e falha no mecanismo de auditoria. | Registros correlacionam admissão/resultado ou identificam pendência; não contêm segredos; novas movimentações são bloqueadas quando a auditoria exigida estiver indisponível. | SEG-12; GOV-03–GOV-04. |
| CA-23 | Modelo, SDK, ferramenta ou skill muda de versão/permissão. | Mudança não entra em uso silenciosamente; exige avaliação registrada. Skill não aprovada, revogada ou com integridade inválida é recusada se esse recurso existir. | SEG-08, SEG-11; GOV-02, GOV-08. |
| CA-24 | Usuário solicita modalidade adicional de transferência, consulta de depósito ou uso de cartão sem contrato definido. | Informa que a capacidade ainda não está disponível e não improvisa ferramenta ou movimentação. | RF01.09, RF01.17; RN-08; D02–D04. |
| CA-25 | Cliente confirma depósito de R$ 10,00 entre contas fictícias, com saldo inicial de R$ 100,00 na origem e R$ 20,00 no destino, em cenário sem tarifas. | Resultado simulado corresponde a R$ 90,00 e R$ 30,00; sua aplicação temporária ao saldo consultável depende de D02. Não há gravação de efeito contábil; reiniciar mantém o cenário inicial de R$ 100,00 e R$ 20,00. Não ocorre chamada a API bancária real nem acesso indevido aos dados do destinatário. | RT-06–RT-07; RN-06–RN-07, RN-11; RF01.05, RF01.11–RF01.13. |

## 13. Registro de decisões e perguntas pendentes

**Decisões confirmadas em F01a:** simulação local com OpenAI real; depósito como transferência entre contas; confirmação de saque e depósito pelo próprio cliente autenticado. As demais sugestões continuam sujeitas à validação. Os identificadores foram preservados para manter a rastreabilidade.

**Decisões adicionais confirmadas em F01b:** não haverá efeito contábil persistente; sete é o limite de erros, não de chamadas totais. D02 e D06 mantêm apenas detalhes operacionais pendentes.

| ID | Situação ou pergunta | Definição confirmada ou sugestão para discussão | Impacto |
| --- | --- | --- | --- |
| D01 | **Resolvida:** ambiente inicial. | Usuário escolheu simulação local com ferramentas e dados bancários fictícios, mantendo integração real com OpenAI. | Não haverá movimentação real nem integração com APIs bancárias na primeira versão. |

| D02 | **Decisão central resolvida:** depósito é transferência entre contas e não há efeito contábil persistente. O saldo muda temporariamente na sessão ou cada operação usa dados fixos? Como consultar depósitos? | Sugestão: estado em memória durante a sessão e retorno ao cenário inicial ao encerrar; consulta dos lançamentos simulados da sessão. Essa opção ainda precisa de confirmação. | Define o resultado de consultas após operações, sem introduzir persistência contábil. |

| D03 | Haverá modalidades adicionais de transferência ou ferramenta separada de Depósito? Como identificar destinatário e comprovante? | Usar Depósito para a transferência entre contas já definida, evitando duplicação; definir separadamente qualquer extensão. | Completa a relação entre a intenção de transferência e o inventário do Canvas. |

| D04 | Cartão de crédito entra na primeira versão? Se sim, quais operações, limites e tarifas fictícias? | Sugestão: começar somente com saldo em conta. Se houver crédito, usar instrumento fictício identificado por alias e regras locais, sem contratar provedor ou coletar cartão/CVC reais. | Fecha o escopo financeiro do simulador e o conteúdo das confirmações. |

| D05 | **Parcialmente resolvida:** quem confirma saque e depósito é o próprio cliente autenticado. Qual o mecanismo e a validade da confirmação? | Não há exigência de aprovação adicional por funcionário. Definir confirmação explícita vinculada à operação e seu prazo de expiração. | Fixa o humano no loop; mantém pendentes os detalhes da confirmação. |

| D06 | **Decisão central resolvida:** limite de sete erros. Quais eventos contam e em qual janela: acumulados por solicitação, consecutivos ou por sessão? | Sugestão: falhas técnicas e respostas inválidas acumuladas por solicitação; parar no sétimo erro; não contar saldo insuficiente, cancelamento ou esclarecimento. Falha não recuperável pode interromper antes. | Remove o conflito com 10 chamadas de Depósito; mantém limites de tempo, custo e chamadas independentes. |

| D07 | Qual modelo OpenAI, limite de tokens, preço/câmbio de referência e abrangência do teto de R$ 0,05? | Validar custo de fluxos representativos antes de escolher parâmetros finais. | Sem isso, não é possível demonstrar viabilidade ou garantir o teto. |
| D08 | Os 60 segundos são acumulados por intenção ou por mensagem? A espera por confirmação humana fica fora? | Usar tempo acumulado de processamento por intenção e excluir apenas espera humana. | Evita ambiguidade de timeout e orçamento em múltiplas mensagens. |
| D09 | Qual mecanismo de autenticação, expiração de sessão, reautenticação e limitação de tentativas? | Separar autenticação do chat e do LLM; definir validade e política por risco. | CPF sozinho não atende ao requisito de credenciais. |
| D10 | Quais dados fictícios podem ir à OpenAI? Logs técnicos ficam somente em memória ou também em arquivo local, por quanto tempo? | Sugestão: somente dados fictícios mínimos no modelo; sem credenciais ou transcrições completas. Definir retenção de metadados técnicos separadamente da proibição de persistência contábil. | Define observabilidade da simulação sem reintroduzir armazenamento de saldos ou lançamentos. |
| D11 | Os papéis Bradesco/CEO/CFO/Suporte são ilustrativos ou representam responsáveis reais? Como ocorrerão alertas e parada? | Nomear representantes operacionais, suplentes e canais. | Torna governança e resposta a incidentes executáveis. |
| D12 | Qual período padrão/máximo do extrato e quais limites por sessão/cliente, de Saque e por rota auxiliar? | Definir valores junto aos contratos do simulador e ao orçamento; o limite de sete erros não substitui esses limites. | Completa limites ainda ausentes no Canvas. |

| D13 | **Simplificada por D02:** não recuperar efeitos contábeis após reinício. | Manter identificadores/status necessários apenas durante a sessão, invalidar aprovações ao encerrá-la e reiniciar com dados fictícios iniciais. A escolha entre cenário estático e estado temporário está em D02. | Recuperação contábil durável deixa de ser dependência da primeira versão. |

### 13.1 O que falta antes do system prompt e da implementação

| Momento | Decisões necessárias | Encaminhamento proposto, ainda não aprovado |
| --- | --- | --- |
| Antes de finalizar o system prompt | Comportamento dos saldos e extratos na sessão (D02), operações disponíveis e uso de cartão (D03–D04). | Saldo em memória durante a sessão; Depósito e Transferência como nomes da mesma operação; apenas saldo em conta inicialmente. |
| Antes de finalizar o system prompt | Autenticação fictícia e confirmação da operação (D05, D09). | CPF fictício + PIN de teste em entrada separada do chat; confirmação explícita com identificador da operação; definir expiração da sessão e da confirmação. |
| Antes de finalizar o system prompt | Significado operacional dos erros e do tempo de processamento (D06, D08). | Sete erros técnicos acumulados por solicitação; 60 segundos acumulados de processamento, excluindo a espera humana. |
| Antes de implementar as integrações | Modelo OpenAI, tokens, custo e limites por ferramenta/cliente (D07, D12). | Escolher modelo compatível com ferramentas; avaliar seu custo frente a R$ 0,05; definir tokens de entrada/contexto/saída e teto de Saque. Não prometer viabilidade sem essa avaliação. |
| Antes de implementar observabilidade | Retenção de logs, responsáveis locais, alertas e parada (D10–D11). | Operador local como responsável pelo protótipo; alertas no CMD e interrupção local; decidir se metadados técnicos serão gravados. |

É possível elaborar um rascunho do system prompt com parâmetros pendentes, mas sua versão final deve refletir as regras escolhidas e os contratos das ferramentas. Autenticação, autorização, contagem de erros, timeout, custo e idempotência precisam de controles no código; instruções no prompt não os garantem.

Contratos técnicos, nomes de funções, organização de módulos e versões compatíveis das dependências podem ser propostos durante o projeto da implementação, sem transformar cada escolha técnica em uma pergunta ao usuário. Os requisitos relativos a dinheiro real e governança corporativa não bloqueiam a simulação local; os controles proporcionais do protótipo continuam aplicáveis.

## 14. Condição para a próxima etapa

Esta entrega limita-se ao refinamento documental do RF01. Nenhum código do agente, integração, instalação de dependências ou teste de movimentação foi realizado. A implementação deve aguardar instrução explícita do usuário e resolução das decisões que condicionam o escopo escolhido.
