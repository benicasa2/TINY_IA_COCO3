# Tiny IA para Tandy Color Computer 3

Port do [Tiny 2.1 para DOS](https://github.com/WollyMonjac/Tiny-2.1) para o Tandy Color Computer 3 com **2 MB de RAM e Disk BASIC**. O programa roda localmente no CoCo 3 e usa os pesos originais do modelo para gerar uma resposta em inglês, caractere por caractere.

## Baixar e iniciar

1. Abra [Releases](../../releases/latest) e baixe o ZIP da sua edição.
2. Extraia o pacote inteiro. No Windows, execute `INICIAR-TINY.CMD`. O lançador seleciona a CPU e 2048 KB no XRoar, monta os quatro discos e abre o chat.
3. Se o XRoar ainda não estiver no PATH, extraia o emulador para a subpasta `xroar`. Coloque `coco3.rom` e `disk11.rom` na subpasta `roms`. Também é possível definir `XROAR_EXE` e `XROAR_ROM_DIR`. [XRoar](https://www.6809.org.uk/xroar/)

| Edição | CPU | Guia |
|---|---|---|
| 6809 | Motorola MC6809 | [Instalação e controles](6809/LEIA-ME.md) |
| 6309 | Hitachi HD6309 | [Instalação e controles](6309/LEIA-ME.md) |

Em hardware físico, use uma expansão de 2 MB com DAT/MMU compatível com a Disto. Monte `TINY1.DSK` a `TINY4.DSK` nas unidades 0 a 3 e digite:

```basic
PCLEAR 1
RUN "START.BAS:0"
```

Para uma unidade, use `RUN "SWAP.BAS:0"` e siga as instruções de troca. Com quatro unidades, `RUN "DEMO.BAS:0"` abre a demonstração. `RUN "BATCH.BAS:0"` lê `ASK.TXT` e recria `ANSWERS.TXT` na unidade 3, que precisa estar gravável.

## Chat e controles

Digite as perguntas em inglês. Use `/0` para comparar respostas sem sorteio, ou `/1` a `/9` para variar a criatividade. O padrão é 5. O monitor mostra o progresso de leitura e geração. `BREAK` cancela a inferência e `QUIT` volta ao BASIC.

| Tecla ou comando | Ação |
|---|---|
| `F1` ou `HELP` | Ajuda |
| `F2` | Alterna o som |
| `Shift+F1` | Alterna a voz |
| `Shift+F2` | Avança a criatividade |
| Seta para cima | Recupera a última pergunta no chat com monitor |
| `DEMO`, `CLS` | Demonstração, limpeza do chat |
| `/P`, `/FULL` | Texto simples, chat com monitor |

O processamento em ponto flutuante é feito por software. Uma resposta pode levar minutos, inclusive no emulador. Algumas respostas incorretas vêm do próprio treinamento. No teste em DOS, por exemplo, o original respondeu `13.` à pergunta `12+3`.

## Implementação e testes

A rede mantém 4 camadas, largura 96, 4 cabeças, contexto de 128 caracteres e o mesmo cache quantizado de chaves e valores do DOS. Os pesos int8 são preservados, e as escalas e os ganhos são convertidos para o formato de ponto flutuante de cinco bytes do BASIC. A edição 6809 acumula em ponto flutuante na ordem do fonte DOS. A edição 6309 acelera o produto matriz-vetor com assembly em modo nativo, preservando os pontos de arredondamento e retornando ao modo compatível para permitir interrupções da ROM.

No XRoar 1.13.1, sem limite de velocidade, com a pergunta `hi` e criatividade zero:

| CPU | Primeira letra | Resposta completa | Texto |
|---|---:|---:|---|
| 6809 | 45,43 s | 151,46 s | `Hello!` |
| HD6309 | 39,83 s | 119,07 s | `Hello!` |

Os 97 valores antes da primeira letra foram idênticos byte a byte entre as duas edições. A edição 6309 levou cerca de 21% menos tempo para concluir essa resposta. A validação foi em emulador. A representação de ponto flutuante e a semente local ainda podem produzir diferenças em relação ao DOS.

- [Histórico e verificação da edição 6809](6809/VERIFICACAO.md)
- [Verificação da edição 6309](6309/VERIFICACAO.md)
- [Tempos brutos do benchmark](verificacao/benchmark-hi.csv)
- [Comparação de 12 perguntas de uma revisão anterior](verificacao/paridade-12-perguntas.csv)
- [Verificação REA/Ghidra do binário 6809](verificacao/rea-6809.json)
- [SHA-256 dos discos, pesos e dumps de logits](SHA256SUMS.txt)

## Recompilar

Instale Python 3, LWTOOLS e CMOC com sua biblioteca de ponto flutuante para Disk BASIC. Deixe `lwasm`, `lwlink` e `cmoc` no PATH. A partir da raiz do repositório:

```sh
python 6809/build.py imagens-6809
python 6309/build.py imagens-6309
```

Cada pasta de edição inclui o fonte C, o carregador de bancos, o empacotador, os pesos originais, as quatro imagens de disco e o lançador. O kernel específico do HD6309 está em [6309/dot6309.asm](6309/dot6309.asm).

## Créditos e licenças

O Tiny 2.1 original é de WollyMonjac, distribuído sob a licença MIT. O modelo incluído corresponde ao commit `49348445661ffc9106f243afb4eafe499a51e286`. As atribuições dos dados de treinamento e as licenças e fontes do runtime CMOC (GPLv3 ou posterior) acompanham cada edição. As ROMs e o emulador são obtidos separadamente. [Tiny 2.1 original](https://github.com/WollyMonjac/Tiny-2.1/tree/49348445661ffc9106f243afb4eafe499a51e286)
