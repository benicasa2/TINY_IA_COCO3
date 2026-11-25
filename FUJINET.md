# Tiny 2.1 no CoCo 3 físico com FujiNet

Esta edição usa **FujiNet via DriveWire/HDB-DOS** no CoCo 3 e uma ponte Python em um PC na rede local. Escolha as imagens para **6809** ou **HD6309** de acordo com a CPU do CoCo. As duas requerem 2 MB e DAT/MMU compatível com a Disto. A edição Web do XRoar usa Becker e tem imagens próprias.

## 1. Iniciar a ponte no PC

Conecte o PC e o FujiNet à mesma rede local. Veja o IPv4 do FujiNet na tela de configuração do dispositivo e obtenha o IPv4 do PC com `ipconfig`. Para buscas ao Google, configure a variável `SERPAPI_API_KEY` no Windows. As consultas a fatos já salvos funcionam com a ponte ligada mesmo sem acesso à internet.

Exemplo com PC em `192.168.1.10` e FujiNet em `192.168.1.25`. Substitua os endereços pelos seus e execute na pasta extraída:

```powershell
python bridge.py --listen 192.168.1.10 --allow 192.168.1.25 --port 65504
```

O endereço de escuta é o do **PC**. `--allow` identifica o **FujiNet** que pode acessar a ponte. Se o firewall solicitar, permita a conexão TCP na rede privada. Mantenha o terminal aberto durante o uso.

## 2. Carregar no CoCo 3

Configure o FujiNet para o CoCo 3, com HDB-DOS/DriveWire e interface serial correspondente ao seu equipamento. No CONFIG do FujiNet, monte as quatro imagens da sua CPU nas unidades 0 a 3, de preferência a partir do cartão SD. Confirme que `DIR 0` mostra `FUJI.BAS` e que as outras unidades estão acessíveis.

```basic
PCLEAR 1
RUN "FUJI.BAS:0"
```

Ao aparecer o pedido de endereço, digite `192.168.1.10:65504` (o IPv4 e a porta do PC). O programa usa o dispositivo TCP do FujiNet pelo HDB-DOS. Os vetores de leitura e escrita DriveWire esperados são `$D93F` e `$D941`. O endereço é solicitado em cada execução.

## 3. Buscar e salvar

Digite `/DB` para confirmar a comunicação. Para testar:

```text
/LANG PT
Quantas luas Marte tem?
/SAVE
/FIND Quantas luas Marte tem?
```

Use `/WEB` seguido da pergunta para forçar nova busca. `/DRIVE LOCAL`, `/DRIVE GOOGLE` e `/DRIVE ONEDRIVE` configuram a memória a partir do CoCo. O SQLite e a pasta sincronizada ficam no PC. A consulta offline significa que a internet pode cair, desde que a rede local e a ponte estejam acessíveis. Para inferência local com os pesos do Tiny e sem ponte, use `RUN "START.BAS:0"`.

Se `/DB` não responder, confirme o endereço mostrado no terminal da ponte, a regra de firewall e o IP do FujiNet permitido por `--allow`. Confirme também que o HDB-DOS consegue listar as quatro unidades pelo FujiNet. `BREAK` interrompe a espera entre operações DriveWire.

## Compilar

É preciso Python 3, CMOC com a biblioteca de ponto flutuante do Disk BASIC e LWTOOLS. No repositório:

```text
python 6809/build.py imagens-6809 --fujinet
python 6309/build.py imagens-6309 --fujinet
```

Dentro de um ZIP de uma única CPU, o comando equivalente é `python build.py imagens --fujinet`.

## Validação

Os dois binários foram executados no XRoar com as imagens desta edição. O teste automatizado interceptou as rotinas de leitura e escrita da ROM e simulou as respostas DriveWire, mantendo uma conexão TCP real com a ponte. Foram validados a digitação do IP no Disk BASIC, abertura de sessão, envio da pergunta, leitura em blocos, salvamento e consulta ao SQLite com a pesquisa externa indisponível. A resposta de busca usada no teste foi controlada. Ainda falta testar o cabo serial e o firmware em um CoCo 3 físico.

[Guia oficial do FujiNet para CoCo](https://fujinetwifi.github.io/fujinet-docs/getting-started/coco-basics/) · [Biblioteca FujiNet para CoCo](https://github.com/FujiNetWIFI/fujinet-lib/tree/a2c56e4438dab4ecf3eaadd75c8ab34dc9b0e17b/bus/coco) · [Protocolo DriveWire do firmware consultado](https://github.com/FujiNetWIFI/fujinet-firmware/tree/6432eb59f539c534ab4d041a85be84880675350d/lib/bus/drivewire)
