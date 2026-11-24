$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

$projeto = 'sistema-de-gest-o-de-estoque-e-vendas'
$base = @('compose','-p',$projeto,'-f','docker-compose.yml')
$combo = $base + @('-f','docker-compose.cluster.yml')

function Docker-OK {
    param([string[]]$Argumentos)
    & docker @Argumentos
    if ($LASTEXITCODE -ne 0) { throw "Falha no Docker (codigo $LASTEXITCODE)." }
}

function Couch {
    param([int]$Porta,[string]$Rota,[string]$Metodo='Get',$Dados=$null)
    $p = @{ Uri="http://127.0.0.1:$Porta$Rota"; Headers=$headers; Method=$Metodo; TimeoutSec=30; ErrorAction='Stop' }
    if ($null -ne $Dados) {
        $p.ContentType = 'application/json'
        $p.Body = ConvertTo-Json -InputObject $Dados -Depth 10 -Compress
    }
    Invoke-RestMethod @p
}

try {
    if (-not (Test-Path '.env')) {
        $senhaNova = [guid]::NewGuid().ToString('N')
        $cookieNovo = [guid]::NewGuid().ToString('N')
        $secretNovo = [guid]::NewGuid().ToString('N')
        @(
            'COUCHDB_USER=admin',
            "COUCHDB_PASSWORD=$senhaNova",
            "COUCHDB_ERLANG_COOKIE=$cookieNovo",
            "COUCHDB_SECRET=$secretNovo",
            'COUCHDB_DATABASE=estoque_vendas'
        ) | Set-Content -LiteralPath '.env' -Encoding ASCII
        Write-Host '.env local criado com credenciais aleatorias.'
    }
    $json = & docker @combo config --format json
    if ($LASTEXITCODE -ne 0) { throw 'Configuracao Compose invalida.' }
    $cfg = ($json -join "`n") | ConvertFrom-Json
    $envApp = $cfg.services.app.environment
    $usuario = [string]$envApp.COUCHDB_USER
    $senha = [string]$envApp.COUCHDB_PASSWORD
    $banco = [string]$envApp.COUCHDB_DATABASE
    if (-not $usuario -or -not $senha -or -not $banco) { throw 'Credenciais ou banco ausentes.' }
    $auth = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes("${usuario}:${senha}"))
    $headers = @{ Authorization = "Basic $auth" }

    Write-Host '1. Iniciando infraestrutura sem recriar containers...' -ForegroundColor Cyan
    # O Compose original cria a rede utilizada pelo arquivo de cluster.
    Docker-OK -Argumentos ($base + @('up','-d','--no-recreate','couchdb'))
    Docker-OK -Argumentos ($combo + @('up','-d','--no-recreate','couchdb1','couchdb2','couchdb3'))

    $portas = @(5985,5986,5987)
    $esperados = @('couchdb@couchdb1.local','couchdb@couchdb2.local','couchdb@couchdb3.local')
    Write-Host '2. Verificando disponibilidade e autenticacao...' -ForegroundColor Cyan
    foreach ($porta in $portas) {
        $online = $false
        for ($i=0; $i -lt 45; $i++) {
            try {
                $up = Invoke-RestMethod -Uri "http://127.0.0.1:$porta/_up" -TimeoutSec 3 -ErrorAction Stop
                if ($up.status -eq 'ok') { $online = $true; break }
            } catch {
                if ($_.Exception.Response -and [int]$_.Exception.Response.StatusCode -in @(401,403)) {
                    # Um servidor que exige autenticacao ja esta respondendo.
                    $online = $true; break
                }
            }
            Start-Sleep -Seconds 2
        }
        if (-not $online) { throw "No $porta indisponivel." }
        $sessao = Couch $porta '/_session'
        if ($sessao.userCtx.name -ne $usuario -or '_admin' -notin $sessao.userCtx.roles) { throw "Autenticacao administrativa falhou em $porta." }
    }

    Write-Host '3. Configurando cluster se necessario...' -ForegroundColor Cyan
    foreach ($porta in $portas) {
        $m = Couch $porta '/_membership'
        $estranhos = @($m.all_nodes + $m.cluster_nodes | Where-Object { $_ -notin $esperados })
        if ($estranhos.Count -gt 0) { throw "Nos inesperados em $porta. Nenhuma remocao automatica sera feita." }
        $estado = (Couch $porta '/_cluster_setup').state
        if ($estado -eq 'cluster_disabled') {
            Couch $porta '/_cluster_setup' 'Post' @{action='enable_cluster';bind_address='0.0.0.0';username=$usuario;password=$senha;node_count=3} | Out-Null
        } elseif ($estado -notin @('cluster_enabled','cluster_finished')) {
            throw "Estado inesperado em ${porta}: $estado"
        }
    }

    foreach ($hostRemoto in @('couchdb2.local','couchdb3.local')) {
        $m = Couch 5985 '/_membership'
        if ("couchdb@$hostRemoto" -notin $m.all_nodes) {
            Couch 5985 '/_cluster_setup' 'Post' @{action='enable_cluster';bind_address='0.0.0.0';username=$usuario;password=$senha;port=5984;node_count=3;remote_node=$hostRemoto;remote_current_user=$usuario;remote_current_password=$senha} | Out-Null
            Couch 5985 '/_cluster_setup' 'Post' @{action='add_node';host=$hostRemoto;port=5984;username=$usuario;password=$senha} | Out-Null
        }
    }
    if ((Couch 5985 '/_cluster_setup').state -ne 'cluster_finished') {
        Couch 5985 '/_cluster_setup' 'Post' @{action='finish_cluster'} | Out-Null
    }

    $pronto = $false
    for ($i=0; $i -lt 30; $i++) {
        $pronto = $true
        foreach ($porta in $portas) {
            $m = Couch $porta '/_membership'
            $estado = (Couch $porta '/_cluster_setup').state
            if (@($m.all_nodes).Count -ne 3 -or @($m.cluster_nodes).Count -ne 3 -or @($esperados | Where-Object { $_ -notin $m.all_nodes -or $_ -notin $m.cluster_nodes }).Count -ne 0 -or $estado -ne 'cluster_finished') { $pronto = $false }
        }
        if ($pronto) { break }
        Start-Sleep -Seconds 2
    }
    if (-not $pronto) { throw 'Os tres nos ainda nao confirmaram a configuracao completa.' }
    Write-Host 'PASSOU: tres nos no mesmo cluster.' -ForegroundColor Green

    Write-Host '4. Verificando banco e shards...' -ForegroundColor Cyan
    try { Couch 5985 "/$banco" | Out-Null } catch {
        if (-not $_.Exception.Response -or [int]$_.Exception.Response.StatusCode -ne 404) { throw }
        Couch 5985 "/${banco}?q=2&n=3" 'Put' | Out-Null
    }
    foreach ($porta in $portas) {
        $info = Couch $porta "/$banco"
        $shards = (Couch $porta "/$banco/_shards").shards.PSObject.Properties
        if ($info.cluster.q -ne 2 -or $info.cluster.n -ne 3 -or @($shards).Count -ne 2) { throw "Distribuicao diferente da esperada em $porta. Banco existente preservado." }
        foreach ($shard in $shards) {
            $replicas = @($shard.Value)
            if ($replicas.Count -ne 3 -or @($esperados | Where-Object { $_ -notin $replicas }).Count -ne 0) { throw 'Shard sem a distribuicao esperada.' }
        }
        Write-Host "PASSOU: banco e shards na porta $porta" -ForegroundColor Green
    }

    Write-Host '5. Iniciando a API...' -ForegroundColor Cyan
    Docker-OK -Argumentos ($combo + @('up','-d','--build','--no-recreate','app'))
    $apiOk = $false
    for ($i=0; $i -lt 30; $i++) {
        try {
            $status = Invoke-RestMethod -Uri 'http://127.0.0.1:8000/status' -TimeoutSec 3
            if ($status.status -eq 'online') { $apiOk = $true; break }
        } catch {}
        Start-Sleep -Seconds 2
    }
    if (-not $apiOk) { throw 'API nao respondeu ao endpoint /status.' }
    Docker-OK -Argumentos ($combo + @('exec','-T','app','python','-c',"from app.conexao import verificar_conexao, listar_documentos; verificar_conexao(); listar_documentos('produto'); print('PASSOU: acesso da aplicacao ao banco')"))
    Write-Host 'INICIALIZACAO E VERIFICACOES CONCLUIDAS.' -ForegroundColor Green
    Write-Host 'API: http://localhost:8000/docs'
} catch {
    Write-Host "ERRO: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
} finally {
    Remove-Variable senha, senhaNova, cookieNovo, secretNovo, auth, headers, cfg, json, envApp -ErrorAction SilentlyContinue
}
