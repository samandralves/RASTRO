# RASTRO — configuração técnica

## 1. Instalar as dependências

```bash
pip install -r requirements.txt
```

## 2. Criar o banco MySQL

No MySQL (via terminal, MySQL Workbench, phpMyAdmin etc.):

```sql
CREATE DATABASE rastro_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

## 3. Configurar as variáveis de ambiente

O app lê a conexão do banco a partir de variáveis de ambiente (com valores padrão
para desenvolvimento local em `root`/sem senha/`localhost`):

```bash
export MYSQL_HOST=localhost
export MYSQL_PORT=3306
export MYSQL_USER=root
export MYSQL_PASSWORD=sua_senha
export MYSQL_DB=rastro_db
export RASTRO_SECRET_KEY=troque-por-uma-chave-aleatoria-em-producao
```

No Windows (PowerShell), use `$env:MYSQL_HOST="localhost"` etc.

Se preferir apontar para outro banco de uma vez só (inclusive SQLite, útil para
testar sem MySQL), defina `DATABASE_URL` — ela tem prioridade sobre as variáveis
`MYSQL_*`:

```bash
export DATABASE_URL=sqlite:///rastro.sqlite3
```

Para a geração de metas por IA (mensal + 4 semanais + 140 diárias), configure também:

```bash
export ANTHROPIC_API_KEY=sua-chave-da-api-da-anthropic
```

Se essa variável não estiver definida, ou a chamada à API falhar por qualquer
motivo, o sistema usa automaticamente um gerador baseado em regras (o mesmo
motor de templates do TALK, só que expandido) — o usuário nunca fica sem
metas, e o rascunho gerado (por IA ou por regra) sempre passa pela aprovação
do admin do mesmo jeito.

## 4. Criar as tabelas

```bash
flask --app app init-db
```

(Isso também acontece automaticamente ao rodar `python app.py`, mas o comando acima
é útil se você estiver usando `flask run` ou rodando as tabelas em outro momento.)

## 5. Criar o primeiro usuário administrador

```bash
flask --app app create-admin
```

Vai pedir nome, e-mail e senha. Essa conta poderá entrar em **"É administrador? Entre
por aqui"**, no rodapé do formulário de login/cadastro da página inicial, e acessar
`/admin` — o painel com o registro completo do banco e as estatísticas de uso.

## 6. Rodar o projeto

```bash
python app.py
```

O site sobe em `http://localhost:5000`.

## Como funciona o desbloqueio progressivo

Todo usuário novo começa apenas com o **TALK** liberado. As demais áreas vão sendo
destravadas conforme o uso:

- **TALK → 1%**: ao terminar a conversa inicial do TALK (as 3 etapas).
- **1% → WORLD**: ao concluir a primeira ação do 1%.
- **WORLD → SECRET**: ao visitar o WORLD pela primeira vez.
- **SECRET → PERFIL**: ao publicar ou reagir a algo no SECRET.

Esses gatilhos ficam nas rotas `/talk`, `/onepct` e `/secret` em `routes/main.py`
e na rota `/world` em `routes/world.py` — é fácil ajustar a regra de cada etapa se
você quiser um critério diferente (por exemplo, exigir 3 metas concluídas em vez
de 1).

## Estrutura do projeto

```
app.py             monta o app: configuração, banco, blueprints e comandos
config.py          configuração vinda das variáveis de ambiente
cli.py             comandos de terminal (init-db, create-admin, create-volunteer)
helpers.py         sessão, @login_required / @admin_required e progresso do usuário
models.py          tabelas (SQLAlchemy)
data.py            conteúdo fixo: marcas do WORLD, benefícios, textos, regras

routes/            um blueprint por área — os endpoints são "área.view"
  auth.py            landing, login, cadastro, logout, entrada do admin
  main.py            home, TALK, 1%, SECRET, PERFIL, atualizar informações e APIs
  world.py           WORLD: a ilha, o Mundo Real e /api/world/*
  admin.py           painel /admin
  volunteer.py       voluntariado: chat do usuário e painel do voluntário
  db_sync.py         /admin/sync-db (sincroniza models.py com o banco)

services/          regras de negócio, sem rotas
  goal_engine.py     ciclo de metas (mensal / semanal / diária)
  ai_goals.py        geração das metas por IA, com fallback por regras

templates/
  base.html          layout comum (sidebar, bottom-nav, blocos head/scripts)
  auth/              landing.html, admin_login.html
  user/              home, talk, talk_menu, onepct, secret, perfil, atualizar
  world/             index.html, mundo_real.html, questionario.html
  admin/             dashboard.html
  volunteer/         chat.html, login.html, painel.html

static/
  css/style.css      estilos gerais do app
  css/world.css      estilos exclusivos do WORLD (só nas telas do WORLD)
  js/app.js          comportamento das telas gerais
  js/world.js        cena PixiJS da ilha + interface do WORLD
  js/estrela.js      fundo de estrelas
  img/               arte da ilha e dos elementos
```

As URLs não mudaram (`/world`, `/talk`, `/api/...` continuam iguais). O que mudou
foi o nome dos endpoints no `url_for`: cada rota agora se chama pelo blueprint
onde mora — `url_for("main.talk")`, `url_for("world.index")`,
`url_for("admin.dashboard")` e assim por diante.

### O WORLD

O WORLD tem **uma só implementação**: a cena interativa em PixiJS
(`static/js/world.js`). A versão antiga, que desenhava a ilha em CSS, foi
removida — não existe mais `templates/world.html` nem a rota `/world-novo`.

O servidor entrega o estado do mundo em `#world-state` (mesmo formato de
`/api/world/state`):

```json
{ "points": 60, "progress": 33.3, "remaining": 0,
  "elements": [{ "cost": 0, "emoji": "🌱", "label": "…", "owned": true }] }
```

Cada marca de `data.WORLD_ELEMENTS` tem um lugar fixo na ilha (`ELEMENT_SLOTS`,
em `world.js`). O que já foi conquistado aparece normal; o que falta aparece
apagado e pode ser obtido clicando — na ilha ou na lista lateral. A tela se
atualiza sozinha depois da compra, sem recarregar.

## ⚠️ Sobre o esquema do banco (mudança importante)

Esta versão substitui o antigo modelo simples de "3 metas do 1%" por um ciclo
completo: 1 meta mensal + 4 semanais + 140 diárias (35 por semana, 5 por dia),
com bloco de metas gerado por IA e aprovado por um admin antes de valer pro
usuário (ver `models.py`, `services/goal_engine.py`, `services/ai_goals.py`). A tabela antiga
`goals` continua existindo no código (por segurança), mas não é mais usada.

Como o esquema mudou bastante, se você já tinha um banco `rastro_db` criado
com a versão anterior, o mais simples é recriar as tabelas do zero:

```sql
DROP DATABASE rastro_db;
CREATE DATABASE rastro_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

E rodar `flask --app app init-db` e `flask --app app create-admin` de novo.

## Como funciona o novo ciclo de metas (mensal/semanal/diária)

1. Ao terminar o TALK (ou ao atualizar o objetivo em "Atualizar informações"),
   o sistema chama `ai_goals.generate_goal_payload` — tenta a API da Anthropic
   e, se não der, usa o fallback de regras — e cria um `AIGoalDraft` com
   status `pendente`.
2. Um admin revisa o rascunho em `/admin` (mensal, 4 semanais e as 140
   diárias) e aprova (`/admin/drafts/<id>/aprovar`) ou rejeita.
3. Ao aprovar, `goal_engine.activate_draft` cria o `MonthlyCycle` ativo, as
   4 `WeeklyGoal` e as 140 `DailyGoal` (só a semana 1 já com os diários
   disponíveis).
4. Cada meta diária concluída soma pontos e é contada em
   `MonthlyCycle.completed_items`. Ao atingir 5 itens, a semana 1 desbloqueia;
   a cada bloco de 35, a próxima semana desbloqueia (semana + seus diários).
5. Ao chegar em 145/145 (140 diárias + 4 semanais + 1 mensal), o ciclo fecha,
   o usuário ganha os 1000 pontos de bônus, e um novo `AIGoalDraft` já é
   solicitado automaticamente pro próximo ciclo (de novo, pendente de
   aprovação).

## Voluntariado / triagem

`/voluntario` deixa o usuário descrever o que quer conversar. O texto passa
por `data.classify_ticket_urgency` (baseado em palavras-chave — não é
diagnóstico). Casos classificados como "crítica" (risco de
autolesão/suicídio) **não** entram na fila: o usuário recebe na hora a
mensagem com o número do CVV (188). Os demais viram um `VolunteerTicket` na
fila, visível e editável em `/admin` (status, universidade parceira,
voluntário responsável).

## Estatísticas de insatisfação (anônimas)

`SatisfactionEntry` guarda só `context` (escola/empresa/cidade/outro),
`reason_text` e `origin` (`talk` ou `atualizar_info`) — sem `user_id` de
propósito. É coletado em dois pontos: uma pergunta opcional ao fim do TALK, e
o formulário em `/atualizar-informacoes`. O `/admin` mostra o percentual por
contexto. Há também `ProgramFeedback` ("o 1% tem ajudado?"), coletado na
mesma tela.
