# Tiny 2.1 para CoCo 3 com HD6309 e 2 MB

Esta edição usa o mesmo modelo e os mesmos pesos do Tiny 2.1 para DOS. Requer um **Tandy Color Computer 3 com HD6309, 2 MB e DAT/MMU estendida compatível com a Disto**, ou a configuração equivalente no XRoar. O carregador e o interpretador Disk BASIC continuam a executar no modo compatível com 6809.

## Executar no Windows

Extraia o ZIP inteiro e abra `INICIAR-TINY.CMD`. O lançador seleciona o HD6309 e 2048 KB no XRoar, monta os quatro discos e inicia o Tiny. Na pasta original do workspace, ele encontra o XRoar e as ROMs usados nos testes. Em outro local, coloque o executável na subpasta `xroar` ou no PATH e as ROMs `coco3.rom` e `disk11.rom` na subpasta `roms`. Você também pode indicar esses caminhos por `XROAR_EXE` e `XROAR_ROM_DIR`.

## Executar pelo Disk BASIC

Na montagem com quatro unidades, coloque `TINY1.DSK`, `TINY2.DSK`, `TINY3.DSK` e `TINY4.DSK` nas unidades 0 a 3, respectivamente. Digite estas duas linhas.

```basic
PCLEAR 1
RUN "START.BAS:0"
```

Para uma unidade, use `RUN "SWAP.BAS:0"` e siga os pedidos de troca. Para demonstração automática com quatro unidades, use `RUN "DEMO.BAS:0"`. Para entrada e saída em arquivo, use `RUN "BATCH.BAS:0"` com a unidade 3 gravável. O modo em lote lê `ASK.TXT` e recria `ANSWERS.TXT` nessa unidade.

## No chat

Digite perguntas em inglês. `/0` seleciona o melhor próximo caractere sem sorteio. `/1` a `/9` variam a criatividade. `F1` mostra ajuda, `F2` alterna o som, `Shift+F1` alterna a voz e `Shift+F2` muda a criatividade. A seta para cima recupera a última pergunta. Durante a inferência, `BREAK` cancela. No prompt, use `QUIT` para voltar ao BASIC.

## O que mudou no HD6309

O produto matriz-vetor usa assembly em modo nativo e as rotinas de ponto flutuante do BASIC. Cada produto e cada soma volta ao formato de cinco bytes nos mesmos pontos em que isso acontecia na edição 6809. As parcelas de valor zero são descartadas, e as demais são acumuladas na ordem original. O kernel retorna ao modo compatível entre grupos de até oito termos para permitir interrupções com o formato de pilha esperado pela ROM.

A edição mantém a precisão da revisão 6809 para os casos verificados. O ponto flutuante do BASIC ainda tem pequenas diferenças em relação à referência compilada a partir do fonte DOS. Respostas incorretas do próprio modelo continuam possíveis. O tempo continua dependente da pergunta, do tamanho da resposta e da velocidade do emulador.

## Recompilar

Com Python 3, CMOC com biblioteca de ponto flutuante para Disk BASIC e LWTOOLS no PATH, execute `python build.py imagens`. O modelo original está em `weights/TINY.BIN`, e o código 6309 está em `dot6309.asm`. Os avisos MIT, GPL do runtime CMOC e atribuições de dados estão nos arquivos de licença incluídos. [Projeto Tiny 2.1](https://github.com/WollyMonjac/Tiny-2.1)
