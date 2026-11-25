# Verificação

## Revisão da inferência em ponto flutuante

A referência numérica foi compilada a partir de `dos/TINY.C` do projeto, com as operações em ponto flutuante e o mesmo arquivo original de pesos. No XRoar, com o CoCo 3 de 2 MB, foram lidos os 97 valores para o próximo caractere logo depois da pergunta e do separador.

| Pergunta | CoCo anterior, erro absoluto máximo | CoCo revisado, erro absoluto máximo | Primeiro caractere |
|---|---:|---:|---|
| `2+2?` | 0,002691924 | 0,000005729 | `T` nas três execuções |
| `hi` | — | 0,000005076 | `H` na referência e no CoCo revisado |

O executável `TINY.EXE` distribuído pelo projeto foi executado no DOSBox Staging com criatividade zero. Ele respondeu `Hello!` a `hi`, `The answer is 4.` a `2+2?` e `13.` a `12+3`. A última resposta exemplifica um erro do próprio modelo original. O CoCo revisado também completou `Hello!` para `hi` com criatividade zero e voltou ao chat. O teste em XRoar sem limite de velocidade levou cerca de 126 segundos.

A inspeção do executável DOS confirmou o multiplicador `0x015A4E35`, o incremento de 1 e a leitura de 15 bits da palavra alta do estado de 32 bits. O depurador do XRoar verificou oito saídas consecutivas com semente 1 na implementação 6809.

Após recompilar com `build.py`, os hashes das quatro imagens reconstruídas coincidiram com os arquivos distribuídos. O REA com Ghidra verificou a imagem 6809 em `$2000`. Evidência `ev_7ce30f864e8f6030d1fe45efb2f42683111c7be3f1d568dccb7286ece504ea3b`. SHA-256 da imagem bruta `e3409523f7f5471adfc912dcb85d4f99536294a8d1fd832aa7a7690394ee8fe4`.

## Correção anterior para WHAT YOUR NAME?

A versão anterior levou cerca de 28 segundos até a primeira previsão e 70 segundos até voltar ao prompt em uma execução de XRoar sem limite de velocidade. A resposta completa foi `I am called Tiny.`, igual à referência DOS com criatividade zero. A espera decorre da inferência em software no 6809. O tempo observado varia com a pergunta, a resposta e o computador que executa o emulador.

O novo indicador é desenhado antes da primeira camada e atualizado entre as camadas. Foi possível cancelar a inferência com `BREAK` antes da primeira letra. O lançador Windows desativa o limite de velocidade por padrão. As projeções de saída que ficavam sem uso enquanto o modelo lia a pergunta foram removidas.

Na correção, a pergunta em maiúsculas gerou `My name is Tiny.` com criatividade 5 e `I am called Tiny.` com criatividade zero. Os dois testes simultâneos no XRoar retornaram ao chat em cerca de 74 e 76 segundos, respectivamente.

O REA com Ghidra confirmou o mapeamento da nova imagem bruta 6809 em `$2000` com resultado `verified`. ID `ev_e22ef3a52c5f1ee995b2593ab482c7d1c94a8716a095f83d8f6d8712ad2423f7`. SHA-256 `9642669940af74f7d43dd4947e4792cc708b417b7172aabb26e5356ac6fb1aec`.

## Comparação de 12 perguntas na revisão anterior

As mesmas perguntas foram executadas com criatividade zero no `TINY.EXE` original, no DOSBox Staging 0.83.1, e no port, no XRoar 1.13.1 com MC6809 e 2048 KB. A comparação usa a resposta exibida ao usuário, mantendo maiúsculas, pontuação e espaços internos. O prompt, a contagem de tempo e o preenchimento da tela ficam fora da comparação. As entradas no XRoar foram fornecidas via depurador.

**Resultado: 12 de 12 respostas coincidiram.** A tabela completa está em `PARIDADE.csv`.

A amostra reúne aritmética, geografia, animais, ortografia, química, astronomia, vocabulário e algarismos romanos. Ela mede a coincidência nas perguntas listadas. Diferenças de ponto flutuante e de amostragem ainda podem aparecer em outras perguntas ou com criatividade maior que zero.

## Validação da revisão anterior

- A tela de abertura exibiu caracteres em queda e passou ao chat quando recebeu uma tecla.
- Os quatro atalhos de função foram testados no XRoar pela injeção dos respectivos estados da matriz de teclado após a leitura da ROM. Ajuda, som, voz e criatividade responderam como esperado.
- `DEMO.BAS` digitou a primeira pergunta original, iniciou a resposta e voltou ao chat ao receber uma tecla.
- `BATCH.BAS` leu uma pergunta de `ASK.TXT`, gravou a resposta em `ANSWERS.TXT` e fechou o arquivo. A pergunta e a resposta `56.` foram confirmadas também por leitura da imagem de disco gravada.
- O Ghidra 12.1.4 importou e analisou o executável original como MZ com `x86:LE:16:Real Mode`. O SHA-256 do executável DOS analisado é `c271eae89de3dedbdef90794a017a1f4d452d52a14d90e3cebebf9ace39022d8`.
- O REA com Ghidra verificou a imagem 6809 desta revisão, extraída dos registros LOADM e mapeada em `$2000`. A verificação retornou `verified`. ID `ev_b6b315f2e745e330c8c6223b6104bd9049b100df55d71e938a2a7963dfd371e9`. SHA-256 da imagem bruta `6862b56b0a68c5dc5d1d92581acd6451dcc1096ec42482edb8e8e0dc39c6e08d`.

- A recompilação por `build.py` reproduziu o SHA-256 das quatro imagens, inclusive após a correção descrita acima.


