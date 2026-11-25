# Busca Web e memória persistente

A edição Web funciona com as CPUs 6809 e 6309 no XRoar para Windows. O programa do CoCo mostra os resultados, escolhe o armazenamento e consulta a memória. Uma ponte local em Python usa a porta Becker para receber as perguntas e fazer HTTPS em nome do CoCo.

## Iniciar

1. Extraia o pacote inteiro e siga as instruções da edição para instalar o XRoar e as ROMs do CoCo 3 e do Disk BASIC.
2. Instale Python 3 e mantenha `python.exe` no PATH.
3. Abra `INICIAR-WEB.CMD`. Ele inicia a ponte local e o XRoar com 2 MB, a CPU da edição, os quatro discos e `WEB.BAS`.
4. Digite `/DB` no chat para ver a configuração atual e a lista de comandos.

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
/WEB Marte
/SAVE
/FIND Marte
```

`/WEB` consulta a Wikipédia e exibe um trecho do artigo localizado, com o link e a data. Use `/LANG PT` ou `/LANG EN` para alterar o idioma da consulta. Após revisar o resultado, use `/SAVE` para arquivá-lo. `/FIND` consulta somente a memória. Uma pergunta normal também procura primeiro uma entrada salva quando o modo Web está ativo. Se houver uma entrada equivalente após normalizar caixa, espaços e pontuação, o Tiny exibe a informação arquivada. Caso contrário, ele usa sua rede local.

O aprendizado desta edição acontece na memória consultável. Os pesos originais continuam os mesmos. Para perguntas reformuladas, procure pelo mesmo nome ou pelas palavras usadas ao salvar. O banco local pode responder depois que o Windows perder o acesso à internet ou à pasta sincronizada. A operação em hardware físico com FujiNet e a sincronização com contas reais de nuvem precisam de teste separado.

[API de busca da Wikipédia](https://www.mediawiki.org/wiki/API:Search_and_discovery) · [Manual do XRoar](https://www.6809.org.uk/xroar/doc/xroar.shtml)

## Verificação

A consulta real a `Mars` foi executada pelo lançador Windows, com o XRoar, o Tiny 6809 e a API da Wikipédia. O resultado exibiu a fonte e foi salvo no SQLite com `/SAVE`. Nas duas CPUs, o teste com dados controlados confirmou a escolha do armazenamento no CoCo, a consulta local com a fonte Web indisponível, a exportação para pastas de teste e a importação para uma base vazia. Os clientes OneDrive e Google Drive com contas reais não fizeram parte desses testes.
