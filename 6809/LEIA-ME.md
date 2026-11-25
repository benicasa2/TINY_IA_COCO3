# Tiny 2.1 para Tandy Color Computer 3

Port nativo para **MC6809, 2 MB com DAT/MMU estendida compatível com a Disto e Disk Extended Color BASIC**. O pacote inclui quatro imagens RS-DOS de 35 trilhas, o código-fonte e os pesos originais. Use a ROM do CoCo 3 e a ROM Disk BASIC da sua máquina ao configurar o emulador.

Para ativar busca e memória persistente no XRoar, execute `INICIAR-WEB.CMD`. [Guia da extensão Web](../WEB-E-MEMORIA.md)

## Iniciar no Windows

Execute `INICIAR-TINY.CMD` na pasta extraída. Ele configura o XRoar para CoCo 3 com 2048 KB e cartucho RS-DOS, monta os quatro discos e inicia o Tiny automaticamente. O lançador desativa o limite de velocidade do emulador por padrão. Defina `XROAR_REALTIME=1` para reproduzir a velocidade real da máquina. A sessão de chat abre com a gravação nas imagens desativada. Para usar o modo em lote, siga as instruções de montagem gravável abaixo.

No workspace original, o lançador encontra o XRoar e as ROMs usados nos testes. Em outra pasta ou computador, coloque o executável do XRoar na subpasta `xroar` (ou no PATH), e `coco3.rom` e `disk11.rom` na subpasta `roms`. Também é possível definir as variáveis de ambiente `XROAR_EXE` (arquivo executável) e `XROAR_ROM_DIR` (pasta das ROMs). O ZIP contém o lançador, as imagens e o fonte.

## Executar

No XRoar, escolha **Tandy CoCo 3**, configure **2048 KB**, use o cartucho **RS-DOS** e monte os discos na ordem abaixo. No hardware, as imagens também podem ser gravadas em disquetes compatíveis.

| Unidade | Imagem |
|---|---|
| 0 | `TINY1.DSK` |
| 1 | `TINY2.DSK` |
| 2 | `TINY3.DSK` |
| 3 | `TINY4.DSK` |

No prompt do Disk BASIC, digite cada linha e pressione Enter.

```basic
PCLEAR 1
RUN "START.BAS:0"
```

Se houver apenas uma unidade e for possível trocar os discos enquanto o programa roda, use `RUN "SWAP.BAS:0"` no lugar da segunda linha. Comece com o disco 1 na unidade 0. Coloque os discos 2, 3 e 4 quando solicitado, voltando ao disco 1 no final. Pressione Enter após cada troca.

O carregador testa os quatro segmentos de 512 KB antes de ler os pesos. Depois de carregar o modelo, o Tiny usa o modo rápido do CoCo 3 durante a sessão. A inferência pode levar minutos em velocidade real, dependendo do tamanho da pergunta e da resposta. O indicador animado mostra `READING QUESTION` durante a leitura e `GENERATING ANSWER` durante a resposta. A primeira letra pode levar de dezenas de segundos a minutos, dependendo da pergunta e do emulador. `BREAK` cancela no próximo ponto de verificação da rede.

A abertura mostra a chuva de caracteres. Pressione qualquer tecla para pular a animação.

## Controles

| Comando | Ação |
|---|---|
| `/0` a `/9` | Criatividade. Use `/0` para testes determinísticos. O padrão é `/5`. |
| `F1` ou `HELP` | Mostra os comandos. |
| `F2` | Liga ou desliga o som. |
| `Shift+F1` | Liga ou desliga a voz. Equivale ao F3 do DOS. |
| `Shift+F2` | Avança a criatividade em um nível, de 9 para 0 ao completar o ciclo. Equivale ao F4 do DOS. |
| Seta para cima | Recupera a última pergunta no modo com monitor. |
| `DEMO` ou `/DEMO` | Digita e responde as mesmas 12 perguntas do modo de demonstração do DOS. Pressione qualquer tecla para retomar o chat. |
| `CLS` | Limpa o chat. |
| `/P` e `/FULL` | Alternam entre texto simples e a tela de 80 colunas com monitor. |
| `/QUIET` e `/VOICE` | Alternam o som e os tons que acompanham as letras. |
| `BREAK` | Interrompe a geração. No prompt, encerra a sessão. |
| `QUIT` ou `EXIT` | Encerra a sessão e volta ao BASIC. |

Digite as perguntas em inglês. Para reproduzir os testes, digite `/0` e depois `What is 7 times 8?` ou `what is the capital of peru`.

## Demonstração ao iniciar

Com as quatro imagens montadas, use `PCLEAR 1` seguido de `RUN "DEMO.BAS:0"` para abrir diretamente na demonstração.

## Perguntas e respostas em arquivo

Use `PCLEAR 1` seguido de `RUN "BATCH.BAS:0"` com as quatro imagens montadas e a unidade 3 gravável. A quarta imagem traz um exemplo `ASK.TXT`, com uma pergunta ASCII por linha e um retorno de carro (CR) no fim de cada linha. O programa usa criatividade zero, aceita até 72 caracteres por linha e grava cada pergunta e sua resposta em linhas separadas em `ANSWERS.TXT`, na unidade 3. O modo recria `ANSWERS.TXT` a cada execução.

## Fidelidade e testes

O modelo original ocupa 48 bancos no CoCo. O empacotamento preserva os pesos int8 e converte escalas e ganhos IEEE para os cinco bytes do BASIC. A rede tem 4 camadas, largura 96, 4 cabeças, contexto de 128 caracteres e o mesmo cache quantizado de chaves e valores que o DOS já usa.

As projeções multiplicam cada peso pela ativação em ponto flutuante, acumulam na ordem do código DOS e aplicam a escala da linha ao final. A escolha aleatória usa a recorrência do Turbo C identificada no executável DOS. O CoCo tem representação de ponto flutuante e rotinas de raiz e exponencial próprias, além de uma semente baseada no relógio local. Para comparar respostas sem aleatoriedade, use `/0`.

Essa revisão prioriza a fidelidade e pode levar vários minutos para responder, inclusive no emulador. Ela usa o mesmo treinamento do DOS, com as limitações que isso implica. Por exemplo, o executável DOS original também respondeu `13.` a `12+3` no teste com criatividade zero.

O GIME exibe a chuva, o chat colorido e o monitor de atividade, confiança, letras e posição. O áudio usa tons do CoCo. O DOS tem opções de paleta VGA e mede letras por segundo, enquanto o port mostra a posição atual no contexto. A operação em arquivo usa o carregador do Disk BASIC.

Os testes foram realizados no XRoar 1.13.1 com MC6809 e 2048 KB e no DOSBox Staging com o executável DOS publicado. Veja `VERIFICACAO.md` para os testes numéricos e a resposta verificada desta revisão. O arquivo `PARIDADE.csv` registra as 12 respostas comparadas em uma revisão anterior. O hardware físico e o som em uma máquina real ainda precisam ser testados.

## Recompilar

Instale Python 3, CMOC com a biblioteca de ponto flutuante para Disk BASIC e LWTOOLS. Deixe `cmoc`, `lwasm` e `lwlink` no PATH. Compile a partir desta pasta.

```sh
python build.py imagens
```

`weights/TINY.BIN` é o modelo DOS original do commit `49348445661ffc9106f243afb4eafe499a51e286`. O `TINY.BIN` dentro de `TINY1.DSK` é o executável 6809. O script recria os discos usando o modelo incluído. [Tiny 2.1 original](https://github.com/WollyMonjac/Tiny-2.1/tree/49348445661ffc9106f243afb4eafe499a51e286)

O código adaptado mantém o aviso MIT de WollyMonjac em `LICENSE`. O executável empacotado foi vinculado ao runtime do CMOC, distribuído sob GPLv3 ou posterior. O texto correspondente e os fontes usados estão em `COPYING.CMOC` e `cmoc-runtime-source.zip`. As atribuições dos dados usados no modelo estão em `DATA_LICENSES.md`. [CMOC usado no build](https://github.com/stahta01/cmoc/tree/03f04a78f6426e84e2af72e26c8841adf18c4a8e)

