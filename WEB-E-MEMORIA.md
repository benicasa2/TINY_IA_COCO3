# Busca Web e memória persistente

A edição Web funciona com as CPUs 6809 e 6309 no XRoar para Windows. O programa do CoCo mostra os resultados, escolhe o armazenamento e consulta a memória. Uma ponte local em Python usa a porta Becker para receber as perguntas e fazer HTTPS em nome do CoCo.

## Iniciar

1. Extraia o pacote inteiro e siga as instruções da edição para instalar o XRoar e as ROMs do CoCo 3 e do Disk BASIC.
2. Instale Python 3 e mantenha `python.exe` no PATH.
3. Obtenha uma chave da SerpApi e defina a variável de ambiente do usuário `SERPAPI_API_KEY` no Windows. Abra uma nova janela ou reinicie o lançador para carregar a configuração. [Conta e chave da SerpApi](https://serpapi.com/manage-api-key)
4. Abra `INICIAR-WEB.CMD`. Ele inicia a ponte local e o XRoar com 2 MB, a CPU da edição, os quatro discos e `WEB.BAS`.
5. Digite `/DB` no chat para ver a configuração atual e a lista de comandos.

`INICIAR-TINY.CMD` abre a edição local tradicional. Para usar a memória quando a internet cair ou estiver desligada, continue usando `INICIAR-WEB.CMD`. A ponte e o banco local continuam funcionando sem conexão externa.

## Configurar o armazenamento no CoCo

| Comando no chat | Efeito |
|---|---|
| `/DRIVE LOCAL` | Usa apenas a base local no Windows. É o padrão. |
| `/DRIVE ONEDRIVE` | Seleciona a pasta montada do OneDrive. |
| `/DRIVE GOOGLE` | Seleciona a pasta montada do Google Drive. |
| `/DRIVE GOOGLE G:/Meu Drive` | Seleciona explicitamente o caminho, quando a descoberta automática falhar. |
| `/DRIVE ONEDRIVE C:/OneDrive` | Seleciona explicitamente a pasta do OneDrive. |
| `/SYNC` | Importa e exporta os registros disponíveis na pasta configurada. |

Entre na sua conta no aplicativo OneDrive ou Google Drive para computador e deixe a pasta montada no Windows. No Google Drive, mantenha a pasta de memória disponível offline se quiser que a ponte possa ler os arquivos em um PC novo mesmo sem conexão. A seleção é persistida a partir do chat. A sincronização entre computadores é responsabilidade do aplicativo de nuvem.

A base SQLite local fica em `%LOCALAPPDATA%\TinyIA-CoCo3\memory.sqlite3`. A pasta sincronizada recebe um arquivo JSON por registro aprovado em uma subpasta `TinyIA-CoCo3`. A cópia SQLite fica fora da nuvem, e cada registro armazena pergunta, resumo, título, URL e data de consulta. Uma nova instalação pode reconstruir a memória local selecionando a mesma pasta e importando os registros. Em caso de falha no armazenamento sincronizado, os fatos aprovados permanecem no banco local e podem ser exportados mais tarde com `/SYNC`.

Para caminhos longos, é possível indicar a pasta candidata no Windows por `TINY_GOOGLE_DIR` ou `TINY_ONEDRIVE_DIR` e selecionar o provedor no chat. Os comandos e as perguntas aceitam até 72 caracteres ASCII.

## Buscar e reutilizar

```text
/LANG PT
Quantas luas Marte tem?
/SAVE
/FIND Quantas luas Marte tem?
```

No modo Web, perguntas normais consultam primeiro uma resposta direta já salva. Se ela ainda não estiver na memória, a ponte envia a pergunta completa ao Google via SerpApi. O CoCo exibe o conteúdo da caixa de resposta direta ou da Visão Geral criada por IA que o Google devolver, com a fonte disponível. A tela mostra uma prévia dos textos longos. `/SAVE` guarda a resposta completa recebida. `/WEB` seguido da pergunta força uma nova consulta. Se o Google devolver somente links de pesquisa, o Tiny informa que a resposta direta ficou indisponível. `/LANG PT` e `/LANG EN` definem o idioma e a região da busca.

`/FIND` consulta somente a memória. Os resumos antigos da Wikipédia continuam disponíveis pelo arquivo e podem aparecer marcados como memória offline quando o Google estiver indisponível. A versão sem ponte, iniciada com `INICIAR-TINY.CMD`, continua a usar a inferência local original.

A chave permanece no Windows. A escolha entre pasta local, OneDrive e Google Drive continua no CoCo. A ponte e o SQLite local permitem a leitura offline dos fatos salvos. Os pesos da rede continuam os mesmos.

[Google Direct Answer Box via SerpApi](https://serpapi.com/direct-answer-box-api) · [Google AI Overview via SerpApi](https://serpapi.com/google-ai-overview-api)

## Verificação

Os testes de integração usam respostas de API controladas para validar a pergunta completa, a caixa de resposta, a Visão Geral, o salvamento e a recuperação offline. A consulta real ao Google requer uma chave SerpApi configurada. A operação em hardware físico com FujiNet e a sincronização com contas reais de nuvem ainda precisam ser testadas.
