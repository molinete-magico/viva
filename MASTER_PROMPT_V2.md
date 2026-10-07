# MASTER PROMPT V2 — VIVA
## REDE SOCIAL VIVA / SIMULAÇÃO SOCIAL AUTÔNOMA / EXPERIÊNCIA ABERTA

> Este documento substitui instruções anteriores quando houver conflito.
> O objetivo não é apenas completar endpoints: é fazer o produto **se comportar como uma cidade social viva**.
> O repositório já possui uma implementação parcial. **Nunca assuma que uma feature está concluída só porque existe uma rota, modelo ou teste para ela.**
> Sempre valide o comportamento real ponta a ponta.

---

# 1. OBJETIVO DO PRODUTO

VIVA é uma rede social fictícia persistente de uma cidade.

A sensação desejada é:

> “Estou abrindo uma rede social de uma cidade onde as pessoas realmente vivem.”

Não é:

- um chatbot disfarçado;
- um visual novel linear;
- um conjunto de telas CRUD;
- um simulador em que tudo espera pelo jogador;
- uma sequência de eventos pré-programados.

A cidade deve continuar existindo quando o jogador não está olhando.

NPCs têm:

- relações entre si;
- rotina;
- trabalho;
- desejos;
- conflitos;
- amizades;
- opiniões;
- segredos;
- memórias;
- vida social;
- iniciativa própria.

O jogador é **um morador**, não o protagonista absoluto.

---

# 2. REFERÊNCIA DE EXPERIÊNCIA

Buscar a sensação de aplicativos de simulação social como Status, sem copiar:

- identidade visual;
- personagens;
- textos;
- nomes;
- assets;
- código;
- lore;
- interface proprietária.

O produto deve combinar:

- rede social;
- mensagens;
- feed;
- descoberta;
- eventos;
- relações;
- vida cotidiana;
- narrativa emergente;
- simulação temporal.

---

# 3. REGRA DE OURO — AGÊNCIA

O jogador nunca deve sentir:

> “Só posso clicar em uma das opções que o sistema imaginou.”

Eventos devem oferecer:

1. ações sugeridas;
2. ação livre em texto.

Exemplo:

> “Chamo Aiko para conversar em particular e pergunto se ela está bem.”

A ação livre deve ser considerada pela narrativa.

Ela pode:

- funcionar;
- falhar;
- ser parcialmente possível;
- gerar uma consequência;
- alterar o rumo da cena;
- revelar informação;
- criar tensão;
- aproximar pessoas;
- encerrar a situação.

**Não transformar ação livre em texto decorativo.**

O backend continua sendo a autoridade sobre efeitos reais.

---

# 4. AGÊNCIA NÃO SIGNIFICA PODER ILIMITADO

O jogador pode tentar qualquer coisa plausível.

Mas:

- não pode controlar NPCs;
- não pode inventar dinheiro;
- não pode teleportar sem justificativa;
- não pode obrigar outro personagem a gostar dele;
- não pode alterar o mundo diretamente;
- não pode declarar consequências como fatos.

Fluxo:

```
intenção do jogador
↓
interpretação narrativa
↓
validação de plausibilidade
↓
resultado da cena
↓
efeitos de domínio
↓
persistência
```

O LLM interpreta a intenção.

O domínio decide o que realmente aconteceu.

---

# 5. NPCs DEVEM TER VIDA PRÓPRIA

NPC não deve existir apenas para responder ao jogador.

NPC pode:

- mandar DM primeiro;
- convidar para evento;
- cancelar convite;
- discutir com outro NPC;
- fazer amizade;
- perder amizade;
- publicar;
- comentar;
- trabalhar;
- faltar ao trabalho;
- mudar de local;
- visitar alguém;
- criar evento;
- recusar convite;
- guardar segredo;
- descobrir algo;
- espalhar rumor;
- mudar de opinião;
- ficar alguns dias sem aparecer.

NPCs também podem ignorar o jogador.

Silêncio é comportamento válido.

---

# 6. GRAFO SOCIAL

A simulação deve possuir relações NPC ↔ NPC.

Não faça:

```
todos os NPCs → jogador
```

Faça:

```
NPC A ↔ NPC B
NPC A ↔ NPC C
NPC B ↔ NPC D
NPC C ↔ jogador
...
```

Relações possuem:

- familiarity;
- friendship;
- trust;
- romance;
- respect;
- tension.

Uma relação pode melhorar ou piorar sem intervenção do jogador.

---

# 7. INICIATIVA SOCIAL

A cidade deve possuir uma fila econômica de oportunidades sociais.

Exemplos:

- DM inesperada;
- convite;
- comentário;
- pedido de ajuda;
- encontro casual;
- notícia;
- rumor;
- evento;
- conflito;
- reconciliação.

Não gerar tudo ao mesmo tempo.

Utilizar:

- cooldown;
- limites por NPC;
- relevância;
- contexto;
- prioridade;
- variedade.

Nunca transformar a cidade em uma máquina de notificações.

---

# 8. LOOP PRINCIPAL

O loop real deve ser:

```
abrir app
↓
catch-up
↓
ver o que aconteceu
↓
feed
↓
explorar
↓
perfil
↓
DM
↓
evento
↓
ação livre
↓
consequência
↓
relação/memória
↓
future hook
↓
nova DM/evento/post
↓
feed
↓
fechar app
↓
mundo continua
```

Cada camada deve conseguir alimentar outra.

---

# 9. FEED COMO OBSERVAÇÃO DO MUNDO

O feed não deve ser apenas uma lista de posts artificiais.

Posts podem representar:

- rotina;
- trabalho;
- opinião;
- acontecimento;
- evento;
- relacionamento;
- humor;
- descoberta;
- consequência;
- notícia local.

Nem tudo deve virar post.

Algumas coisas só aparecem:

- em DM;
- em comentário;
- em notificação;
- em evento;
- em perfil;
- por rumor;
- por descoberta casual.

---

# 10. DESCOBERTA GRADUAL

O jogador não deve conhecer toda a ficha do NPC imediatamente.

Informação pode ser descoberta através de:

- conversa;
- evento;
- perfil;
- post;
- comentário;
- memória;
- observação;
- outro NPC.

O nível de descoberta deve ser consequência da convivência, não apenas de abrir o perfil.

---

# 11. DMs

DM é uma conversa persistente.

A conversa deve sobreviver a:

- sair da tela;
- fechar o app;
- passar tempo;
- mudar de sessão.

NPC pode iniciar conversa sem o jogador abrir a tela.

Uma nova sessão não apaga a anterior.

O contexto do NPC deve considerar:

- personalidade;
- relação;
- memórias relevantes;
- eventos recentes;
- rotina;
- local;
- horário;
- mensagens recentes;
- acontecimentos recentes envolvendo o jogador.

---

# 12. DMs DEVEM TER SUBTEXTO

NPC não deve responder somente ao texto literal.

Deve considerar:

- humor;
- confiança;
- tensão;
- histórico;
- intimidade;
- assunto anterior;
- momento do dia.

Exemplo:

NPC desconfiado não responde igual a NPC íntimo.

---

# 13. EVENTOS

Evento é uma cena contextual, não uma página de texto.

Deve possuir:

- local;
- participantes;
- horário;
- estado do mundo;
- relações;
- memórias;
- ações;
- consequências;
- possibilidade de abandono;
- possibilidade de conclusão.

O evento deve poder mudar de rumo.

---

# 14. EVENTOS NÃO PODEM SER LINEARES

Não implementar:

```
turno 1 → turno 2 → turno 3 → final fixo
```

Preferir:

```
estado atual
↓
ação do jogador
↓
interpretação
↓
mudança de estado
↓
próxima cena
```

A mesma cena pode produzir resultados diferentes.

---

# 15. AÇÃO LIVRE É OBRIGATÓRIA

Todo evento interativo deve possuir um campo equivalente a:

> “Ou faça qualquer outra coisa.”

O texto do jogador deve ser enviado ao backend.

O backend deve:

1. validar;
2. persistir;
3. contextualizar para o LLM;
4. gerar resposta;
5. validar a resposta;
6. aplicar apenas consequências autorizadas pelo domínio.

---

# 16. CONSEQUÊNCIAS

Consequências podem ser:

- relação;
- memória;
- dinheiro;
- evento futuro;
- DM futura;
- post;
- comentário;
- rumor;
- convite;
- mudança de rotina;
- descoberta.

Não gerar todas em toda interação.

Consequências devem ser proporcionais.

---

# 17. MEMÓRIA

Memória deve ser bilateral quando fizer sentido.

Se o jogador vive algo importante com NPC:

- jogador pode lembrar;
- NPC pode lembrar.

Memórias importantes devem influenciar futuras interações.

Não mandar banco inteiro para o LLM.

Usar recuperação contextual.

---

# 18. FUTURE HOOKS

Eventos e DMs importantes podem criar:

```
FutureHook
```

Exemplo:

```
evento hoje
↓
“depois te mando mensagem”
↓
FutureHook
↓
mundo avança
↓
NPC envia DM amanhã
```

Future hooks devem ser:

- persistentes;
- idempotentes;
- temporais;
- canceláveis quando necessário;
- limitados para evitar spam.

---

# 19. MUNDO ASSÍNCRONO

Não exigir que o usuário pressione “avançar um dia” para a cidade funcionar.

O relógio deve avançar por:

- tempo real decorrido;
- catch-up;
- eventos;
- testes/dev controls.

O botão de avançar tempo é ferramenta de desenvolvimento/UX, não o motor narrativo principal.

---

# 20. CATCH-UP

Ao retornar:

```
last_simulated_at
↓
tempo decorrido
↓
rotinas
↓
trabalho
↓
eventos
↓
relações relevantes
↓
future hooks
↓
algumas iniciativas sociais
↓
relatório
```

Não simular cada minuto.

Não gerar milhares de eventos.

---

# 21. RELATÓRIO DE RETORNO

O jogador deve conseguir perceber:

> “Enquanto eu estava fora, a cidade fez coisas.”

Exemplos:

- “Aiko trabalhou até tarde.”
- “O restaurante fechou mais cedo ontem.”
- “Rafael publicou uma foto.”
- “Você recebeu uma mensagem de Aiko.”
- “Dois moradores começaram a seguir um ao outro.”
- “O evento de sexta foi cancelado.”

O relatório deve priorizar acontecimentos relevantes ao jogador.

---

# 22. LIBERDADE DE MOVIMENTO SOCIAL

O jogador deve poder descobrir e interagir com locais.

Locais devem oferecer atividades.

Exemplos:

- comer;
- trabalhar;
- conversar;
- observar;
- comprar;
- descansar;
- participar de evento;
- encontrar moradores;
- criar evento.

Não transformar tudo em menus decorativos.

---

# 23. HUBS SOCIAIS

Locais como o restaurante de ramen devem funcionar como hubs.

Um hub deve possuir:

- frequentadores recorrentes;
- funcionários;
- horários;
- relações;
- acontecimentos;
- pequenas cenas;
- encontros inesperados.

A mesma pessoa pode aparecer em horários diferentes.

---

# 24. PERSONALIDADE

Personalidade deve mudar comportamento observável.

Afeta:

- tamanho das mensagens;
- iniciativa;
- humor;
- formalidade;
- assuntos;
- frequência;
- tolerância;
- forma de conflito;
- forma de carinho;
- uso de emojis.

Não basta armazenar personalidade em JSON se ela não aparece no comportamento.

---

# 25. NPCs PODEM DISCORDAR

NPCs não devem concordar com o jogador por padrão.

Eles podem:

- discordar;
- recusar;
- mudar de assunto;
- ficar ofendidos;
- desconfiar;
- brincar;
- ignorar;
- pedir desculpas;
- mudar de ideia.

---

# 26. SEGREDOS E RUMORES

Adicionar gradualmente:

```
Secret
Rumor
Discovery
```

Um segredo pode:

```
NPC A sabe
↓
NPC B descobre
↓
B comenta com C
↓
jogador ouve rumor
↓
jogador investiga
```

Informação não deve aparecer magicamente no perfil.

---

# 27. AÇÃO DO NPC SOBRE OUTROS NPCS

O mundo deve conseguir produzir:

- amizades NPC ↔ NPC;
- conflitos;
- romances;
- afastamentos;
- reconciliações;
- colaboração;
- rivalidades.

O jogador pode descobrir essas histórias sem ser participante.

Isso é essencial para evitar a sensação de “mundo cenográfico”.

---

# 28. ANTI-SPAM SOCIAL

Cada NPC deve possuir limites de:

- posts;
- DMs;
- convites;
- comentários;
- iniciativas.

Usar cooldown e prioridade.

Um NPC não deve mandar:

```
“Oi”
“Oi”
“Oi”
```

todos os dias.

---

# 29. LLM

LLM pode:

- interpretar intenção;
- escrever diálogo;
- gerar narrativa;
- sugerir consequência;
- gerar post;
- gerar rumor;
- gerar mensagem espontânea.

LLM nunca decide diretamente:

- dinheiro;
- relação;
- memória;
- estado;
- recompensa;
- autorização;
- propriedade;
- conclusão transacional.

Fluxo obrigatório:

```
LLM
↓
schema
↓
domain validation
↓
service
↓
transaction
↓
database
```

---

# 30. FALLBACK

Se LLM falhar:

- não perder mensagem;
- não perder evento;
- não corromper estado;
- não aplicar consequência parcial;
- permitir retry;
- permitir encerramento seguro.

---

# 31. IDEMPOTÊNCIA

Operações críticas devem ser idempotentes:

- enviar/confirmar consequência;
- finalizar evento;
- processar future hook;
- criar memória;
- aplicar relação;
- notificar;
- gerar milestone.

Repetir a mesma operação não pode duplicar efeitos.

---

# 32. TESTE DE COMPORTAMENTO

Não basta testar:

> “endpoint respondeu 200”.

Testar:

```
usuário age
↓
estado muda
↓
NPC lembra
↓
relação muda
↓
future hook nasce
↓
tempo passa
↓
NPC toma iniciativa
↓
usuário recebe DM
↓
feed reflete consequência
```

Esse é o teste de produto mais importante.

---

# 33. DEFINITION OF DONE

Uma feature só está pronta quando:

- backend existe;
- frontend usa;
- estado persiste;
- reload preserva;
- erro é tratado;
- mobile funciona;
- consequência aparece onde deveria;
- testes cobrem comportamento;
- feature funciona sem depender de estado falso no frontend.

**Não considerar “implementado” porque existe um botão, endpoint, modelo ou teste isolado.**

---

# 34. AUDITORIA OBRIGATÓRIA ANTES DE IMPLEMENTAR

Antes de alterar código:

1. ler arquitetura atual;
2. mapear o que realmente existe;
3. identificar features incompletas;
4. identificar código morto;
5. identificar mocks/fakes;
6. identificar fluxos que terminam cedo;
7. identificar divergência entre frontend e backend;
8. verificar migrations;
9. verificar testes;
10. executar/validar os fluxos críticos.

Nunca reconstruir algo que já funciona sem necessidade.

---

# 35. PRIORIDADE DE CORREÇÃO

Quando encontrar conflito, priorizar:

1. consistência do mundo;
2. persistência;
3. agência do jogador;
4. autonomia dos NPCs;
5. consequências;
6. DMs;
7. eventos;
8. feed;
9. mobile;
10. acessibilidade;
11. performance;
12. estética;
13. infraestrutura de produção.

---

# 36. REGRA CONTRA FEATURE FALSA

É proibido:

- botão sem função;
- página que apenas exibe mock;
- estado que não persiste;
- consequência apenas visual;
- “IA” que não é chamada;
- NPC que só existe no perfil;
- evento que não muda nada;
- notificação sem destino;
- feature declarada completa sem validação.

Se não puder implementar agora:

```
TODO explícito
+
motivo
+
próximo passo
```

---

# 37. UX

Mobile-first.

Evitar aparência de SaaS.

Priorizar:

- feed orgânico;
- perfis humanos;
- mensagens naturais;
- espaços sociais;
- tipografia;
- ritmo;
- pequenos detalhes;
- estados vazios narrativos;
- microinterações.

A UI deve parecer um aplicativo que alguém realmente usaria todos os dias.

---

# 38. ARQUITETURA ATUAL DO VIVA

Preservar a base:

```
React + Vite
↓
FastAPI
↓
SQLModel
↓
SQLite
↓
LLM Provider
```

Não adicionar cloud/produção durante o MVP.

Manter possibilidade futura de:

```
SQLite → PostgreSQL
```

---

# 39. SEGURANÇA

Frontend nunca define:

- dinheiro;
- relações;
- memórias;
- eventos;
- recompensas;
- autorização.

Secrets apenas no backend.

LLM apenas no backend.

Validar toda entrada.

---

# 40. ORDEM DE EXECUÇÃO

Para cada tarefa:

```
AUDITAR
↓
IDENTIFICAR CAUSA
↓
PLANEJAR
↓
IMPLEMENTAR
↓
TESTAR
↓
VALIDAR FLUXO COMPLETO
↓
CORRIGIR
↓
DOCUMENTAR
```

Não avançar apenas porque o código compila.

---

# 41. PRIMEIRO TRABALHO DO AGENTE

Ao receber este prompt:

1. audite o repositório existente;
2. compare implementação real com este documento;
3. produza uma matriz:

| Feature | Existe | Completa | Problema | Prioridade |
|---|---:|---:|---|---|

4. corrija primeiro as maiores quebras de comportamento;
5. implemente a liberdade de ação;
6. implemente autonomia social;
7. implemente consequências assíncronas;
8. depois faça polish.

Não declarar todas as fases concluídas sem evidência.

---

# 42. ACEITAÇÃO FINAL

O produto está no estado desejado quando o jogador consegue:

```
abrir VIVA
↓
ver acontecimentos recentes
↓
ler o feed
↓
receber uma DM que ele não iniciou
↓
responder
↓
descobrir algo novo sobre alguém
↓
encontrar pessoas em um local
↓
participar de evento
↓
descrever livremente o que quer fazer
↓
ter uma consequência real
↓
ver relação/memória mudar
↓
receber uma consequência futura
↓
fechar o app
↓
voltar depois
↓
descobrir que a cidade continuou vivendo
```

A sensação final deve ser:

> **“Eu não estou conversando com bots. Eu estou vivendo dentro de uma rede social que pertence a uma cidade.”**

---

# 43. REGRA FINAL

**Não otimize para quantidade de features. Otimize para causalidade.**

Uma pequena ação deve poder criar uma pequena consequência.

Uma pequena consequência pode criar uma memória.

Uma memória pode mudar uma relação.

Uma relação pode gerar uma iniciativa.

Uma iniciativa pode gerar um evento.

Um evento pode mudar o feed.

O feed pode revelar algo ao jogador.

Esse ciclo é o coração de VIVA.


## V2.1 — Correções de autonomia já implementadas

- **NPC↔NPC persistente:** durante catch-up, NPCs que ocupam o mesmo local podem interagir sem o jogador. A interação passa pelo RelationshipService e gera memória para os dois lados.
- **Cooldown social:** um mesmo par não recebe pulsos repetidos em janela curta; a memória usa chave diária para impedir duplicação.
- **Memória bilateral:** eventos relevantes deixam registro tanto para o personagem do jogador quanto para os NPCs envolvidos. O NPC pode reconhecer posteriormente que aquela experiência aconteceu.
- **Conclusão narrativa natural:** uma cena pode declarar flags.complete=true. O backend então encerra a sessão pelo mesmo caminho transacional de uma finalização manual, preservando idempotência e efeitos de domínio.
- **Autoridade do domínio preservada:** flags, narrativa e texto livre nunca aplicam dinheiro, relação, memória ou future hook diretamente; eles apenas orientam a narrativa. A materialização continua nos serviços de domínio.

### Definition of Done adicional

Uma funcionalidade social só é considerada concluída quando:
1. pode acontecer sem o jogador apertar um botão específico;
2. deixa estado persistente quando deveria deixar;
3. pode ser lembrada por mais de uma pessoa quando a experiência é compartilhada;
4. possui cooldown/idempotência contra repetição artificial;
5. aparece no retorno/catch-up de forma compreensível;
6. não depende do LLM para garantir invariantes ou autorização.


## V3 — Mundo vivo / camada social contínua

A simulação social não pode depender de um único pulso no retorno do jogador.

### Princípio operacional

O relógio do mundo é a fonte temporal. Quando passam 6 horas, o backend deve simular aproximadamente essas 6 horas em janelas menores, preservando os acontecimentos relevantes sem tentar reproduzir cada minuto.

A cada janela, o sistema pode:

- atualizar onde os NPCs estão conforme suas rotinas;
- detectar quem está no mesmo local;
- produzir encontros espontâneos entre NPCs;
- alterar relações e criar memórias bilaterais;
- publicar posts de moradores mesmo quando ninguém os segue;
- gerar respostas e curtidas entre moradores;
- criar uma atividade/evento espontâneo;
- permitir que um NPC convide o jogador;
- permitir que um NPC procure o jogador por iniciativa própria;
- manter a rede de follows e relações crescendo organicamente.

### O jogador não é o scheduler

Não usar:
- “o NPC só posta porque o jogador abriu o feed”;
- “o NPC só conversa porque o jogador abriu o DM”;
- “o NPC só existe quando uma tela precisa dele”.

O jogador pode observar a simulação, mas não é o relógio da cidade.

### Ritmo social

O mundo deve parecer movimentado sem virar spam:
- atividade social em pequenas ondas;
- limites por janela;
- cooldown por par;
- idempotência por dia;
- posts e comentários com variedade;
- apenas uma pequena parte dos NPCs deve tomar iniciativas mais fortes em cada período.

### Primeiro vínculo

Um personagem novo deve possuir pelo menos uma conexão social inicial autônoma. Essa conexão pode virar follow, DM, evento, amizade, rivalidade ou outra relação conforme a simulação evolui.

### Atividades

Além de eventos criados pelo jogador, o mundo pode criar atividades espontâneas. Elas devem:
1. ter local e horário;
2. possuir um NPC como anfitrião;
3. envolver outros moradores;
4. poder convidar o jogador;
5. deixar consequências quando o jogador participa.

### Definição de “mundo vivo”

Considerar a camada concluída somente quando, depois de algumas horas sem interação do jogador, seja possível observar pelo menos uma combinação de:
- novos posts;
- respostas entre NPCs;
- mudanças de localização;
- encontros;
- mudanças de relacionamento;
- novas memórias;
- atividade/evento espontâneo;
- DM iniciado por NPC.

O objetivo não é reproduzir Status visualmente. O objetivo é reproduzir a propriedade comportamental que torna uma rede social simulada convincente: **quando o jogador volta, ele encontra uma sociedade que continuou existindo sem ele.**


## V4 — Cidade socialmente auto-organizada

A camada social agora deve transformar relações em comportamento: NPCs mantêm e rompem follows, iniciam DMs, criam encontros, aceitam convites, reagem a publicações, espalham rumores, ganham ou perdem visibilidade e deixam a tensão esfriar quando não há contato. O jogador deve retornar a um mundo que produziu consequências sem ele.

Regras adicionais:
- personalidade, objetivos, compatibilidade, localização e arco social influenciam ações;
- NPC↔NPC deve continuar funcionando sem o jogador;
- ações sociais precisam deixar memória e/ou consequência persistente;
- atividades ambientais podem terminar sozinhas;
- feed pode priorizar relevância social sem substituir o histórico cronológico;
- “Enquanto você estava fora” deve destacar acontecimentos novos e socialmente relevantes;
- decisões de domínio continuam pertencendo ao backend; LLM só escreve superfície narrativa;
- toda autonomia precisa de limites diários, dedupe e comportamento determinístico suficiente para catch-up seguro.
