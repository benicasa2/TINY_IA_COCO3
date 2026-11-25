@echo off
setlocal EnableExtensions DisableDelayedExpansion
set "DISKS=%~dp0."
set "LOCAL_WORK=%~dp0..\..\work"

for %%D in (1 2 3 4) do if not exist "%DISKS%\TINY%%D.DSK" (
    echo Disco ausente: TINY%%D.DSK. Extraia o ZIP inteiro antes de iniciar.
    goto :failure
)

if defined XROAR_EXE goto :check_exe
set "XROAR_EXE=%DISKS%\xroar.exe"
if exist "%XROAR_EXE%" goto :check_exe
set "XROAR_EXE=%DISKS%\xroar\xroar.exe"
if exist "%XROAR_EXE%" goto :check_exe
set "XROAR_EXE="
for /d %%I in ("%LOCAL_WORK%\xroar-bin\xroar-*") do if not defined XROAR_EXE if exist "%%~fI\xroar.exe" set "XROAR_EXE=%%~fI\xroar.exe"
if defined XROAR_EXE goto :check_exe
for %%I in (xroar.exe) do set "XROAR_EXE=%%~$PATH:I"

:check_exe
if not exist "%XROAR_EXE%" (
    echo XRoar ausente. Coloque o emulador na subpasta xroar ou configure XROAR_EXE.
    goto :failure
)

if defined XROAR_ROM_DIR goto :check_roms
set "XROAR_ROM_DIR=%DISKS%\roms"
if exist "%XROAR_ROM_DIR%\coco3.rom" if exist "%XROAR_ROM_DIR%\disk11.rom" goto :check_roms
set "XROAR_ROM_DIR=%LOCAL_WORK%"

:check_roms
if not exist "%XROAR_ROM_DIR%\coco3.rom" goto :missing_roms
if not exist "%XROAR_ROM_DIR%\disk11.rom" goto :missing_roms
for %%I in ("%XROAR_ROM_DIR%\.") do set "XROAR_ROM_DIR=%%~fI"
for %%I in ("%DISKS%") do set "DISKS=%%~fI"

set "SPEED=-no-ratelimit -no-vo-vsync -fskip 2"
if "%XROAR_REALTIME%"=="1" set "SPEED=-ratelimit"

set "BRIDGE=%DISKS%\bridge.py"
if not exist "%BRIDGE%" set "BRIDGE=%DISKS%\..\bridge.py"
where python.exe >nul 2>&1
if errorlevel 1 (
    echo Instale Python 3 para usar a ponte WEB.
    goto :failure
)
python "%BRIDGE%" --port 0 -- "%XROAR_EXE%" %SPEED% -default-machine coco3 -machine coco3 -machine-cpu 6309 -ram 2048 -rompath "%XROAR_ROM_DIR%" -extbas "%XROAR_ROM_DIR%\coco3.rom" -cart rsdos -cart-becker -becker-ip 127.0.0.1 -cart-rom "%XROAR_ROM_DIR%\disk11.rom" -no-disk-write-back -load-fd0 "%DISKS%\TINY1.DSK" -load-fd1 "%DISKS%\TINY2.DSK" -load-fd2 "%DISKS%\TINY3.DSK" -load-fd3 "%DISKS%\TINY4.DSK" -type "PCLEAR 1\r\rRUN \"WEB.BAS:0\"\r"
if errorlevel 1 (
    echo O XRoar terminou com erro.
    goto :failure
)
exit /b 0

:missing_roms
echo ROMs ausentes. Coloque coco3.rom e disk11.rom na subpasta roms ou configure XROAR_ROM_DIR.

:failure
pause
exit /b 1


