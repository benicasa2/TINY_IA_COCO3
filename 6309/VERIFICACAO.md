# Verificação da edição HD6309

Foi usada a pergunta `hi`, com criatividade `/0`, nos dois binários, no XRoar 1.13.1, com CoCo 3, 2 MB, sem limite de velocidade e sem áudio no teste automatizado. O tempo é o observado no computador que executou o emulador.

| Edição e CPU emulada | Primeira letra | Resposta completa e retorno ao chat | Resposta |
|---|---:|---:|---|
| 6809 | 45,43 s | 151,46 s | `Hello!` |
| HD6309 | 39,83 s | 119,07 s | `Hello!` |

Os 97 valores de ponto flutuante antes da primeira letra foram idênticos byte a byte (485 bytes). O erro absoluto máximo em comparação com uma versão de referência compilada do fonte DOS com os mesmos pesos foi 0,000005076 nas duas edições.

Um produto escalar com pesos positivos, negativos e termos zero retornou exatamente −11,375. O teste de detecção com CPU 6809 emulada exibiu a mensagem de requisito e devolveu o controle ao BASIC. A recompilação reproduziu os hashes de todas as quatro imagens.

Os tempos foram medidos no emulador. A edição ainda precisa ser testada em hardware físico.
