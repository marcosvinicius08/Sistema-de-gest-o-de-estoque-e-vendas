# Sistema de Gestão de Estoque e Vendas

Projeto acadêmico de Sistemas Operacionais — UFPI, nível 2.

## Sobre

Aplicação para cadastro e consulta de produtos, controle de entradas e saídas de estoque e registro de vendas, com atualização do estoque. A API REST é executada em um container e utiliza um banco NoSQL Apache CouchDB em cluster com três nós em containers no mesmo computador.

## Tecnologias

- Python 3.12 (imagem Docker), FastAPI, Uvicorn e HTTPX.
- Apache CouchDB 3.5.3 (cluster).
- Docker Desktop e Docker Compose.

## Requisitos para executar

Docker Desktop iniciado em modo de containers Linux, Docker Compose v2, Windows PowerShell 5.1 ou PowerShell 7, conexão à internet para baixar as imagens e dependências na primeira execução e portas locais 5984–5987 e 8000 disponíveis. Não é necessário instalar Python diretamente no Windows.

## Inicialização

1. Extraia o ZIP em uma pasta e abra o PowerShell nessa pasta (onde está o Dockerfile).
2. Confirme que o Docker está disponível: `docker info`.
3. Execute:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\configurar_cluster.ps1
```

O script cria um `.env` com credenciais aleatórias quando ele não existe, preserva um `.env` existente, inicia os serviços, configura o cluster via API administrativa quando necessário, cria o banco `estoque_vendas` se estiver ausente, verifica os shards e inicia a API. A rede Docker é criada pelo Compose original. A instância isolada na porta 5984 é mantida por compatibilidade com a configuração original; a aplicação utiliza o cluster (couchdb1.local:5984), não a instância isolada.

A primeira execução pode demorar devido ao download das imagens. Se houver um erro, consulte a mensagem, confira as portas e credenciais, e não exclua volumes para tentar corrigi-lo. O script não remove containers, volumes ou documentos preexistentes. A configuração é destinada a uma rede local de laboratório, não à exposição pública.

## Acesso

| Serviço | Endereço |
|---|---|
| API | http://localhost:8000 |
| Status | http://localhost:8000/status |
| Documentação e teste de endpoints (Swagger) | http://localhost:8000/docs |
| CouchDB 1 | http://localhost:5985/_utils/ |
| CouchDB 2 | http://localhost:5986/_utils/ |
| CouchDB 3 | http://localhost:5987/_utils/ |

O usuário e a senha do CouchDB estão no `.env` local. Não compartilhe esse arquivo nem credenciais reais no repositório.

## Arquitetura e distribuição

```text
Cliente -> API FastAPI -> CouchDB 1 <-> CouchDB 2 <-> CouchDB 3
                          \_____________________________/
                                    Cluster NoSQL
```

Os três nós usam a rede Docker e volumes próprios. O banco foi configurado com `q=2` (partições), `n=3` (réplicas por partição) e quóruns padrão `r=2` e `w=2` na configuração validada. A API acessa o cluster pelo nó 1. A disponibilidade automática da API quando esse nó falha não foi implementada/validada.

## Verificações e demonstração

```powershell
docker compose -p sistema-de-gest-o-de-estoque-e-vendas -f docker-compose.yml -f docker-compose.cluster.yml ps
curl.exe -u admin http://localhost:5985/_membership
curl.exe -u admin http://localhost:5985/estoque_vendas/_shards
```

Digite a senha do `.env` quando solicitada. Repita as consultas nas portas 5986 e 5987 para conferir a composição do cluster. O endpoint `/docs` permite demonstrar as operações da aplicação. O diretório `app/tests` contém scripts de teste; confira seu conteúdo antes de executá-los, pois podem criar, alterar ou excluir registros de teste.

Na configuração original do grupo, foram realizados testes de autenticação, pertencimento dos três nós, distribuição dos shards, criação e leitura de um documento por nós diferentes, atualização, escrita e leitura com um nó desligado, retorno desse nó e integração da aplicação com o banco. Esses testes não comprovam recuperação individual de cada réplica nem disponibilidade da API após falha do nó ao qual ela se conecta.

## Parar e reiniciar

Para interromper os serviços sem remover dados:

```powershell
docker compose -p sistema-de-gest-o-de-estoque-e-vendas -f docker-compose.yml -f docker-compose.cluster.yml stop
```

Para retomar, execute novamente `configurar_cluster.ps1`. Não use `down -v` se deseja preservar os dados.

## Estrutura

- `app/`: API, módulos de produtos, estoque, vendas, conexão, validações e testes.
- `Dockerfile`: imagem da aplicação.
- `docker-compose.yml`: aplicação e infraestrutura original.
- `docker-compose.cluster.yml`: três nós do cluster.
- `configurar_cluster.ps1`: inicialização e verificação.
- `requirements.txt`: dependências Python.
- `.env.example`: referência de variáveis de ambiente.

Referência: [Documentação oficial de configuração de cluster CouchDB](https://docs.couchdb.org/en/stable/setup/cluster.html).
