@echo off
chcp 65001 >nul
rem NomadPick BOT-01 특가 수집을 이 PC(한국 IP)에서 30분마다 실행하는 Windows 작업 스케줄러 등록
rem   설치: deploy\windows-collect-task.bat install     (매일 09:00~21:30, 30분 간격)
rem   삭제: deploy\windows-collect-task.bat uninstall
rem   확인: schtasks /Query /TN NomadPick-RPA-Deals /V /FO LIST
rem 로그: logs\rpa-deals.log  (PC 가 켜져 있고 로그인되어 있을 때 실행)
setlocal
set TASK=NomadPick-RPA-Deals
set ROOT=%~dp0..
for %%I in ("%ROOT%") do set ROOT=%%~fI

if /I "%1"=="uninstall" (
  schtasks /Delete /TN %TASK% /F
  exit /b %errorlevel%
)
if /I not "%1"=="install" (
  echo 사용법: %~nx0 install ^| uninstall
  exit /b 1
)

if not exist "%ROOT%\logs" mkdir "%ROOT%\logs"
schtasks /Create /F /TN %TASK% /SC DAILY /ST 09:00 /RI 30 /DU 12:31 ^
  /TR "cmd /c cd /d \"%ROOT%\" && set PYTHONIOENCODING=utf-8 && .venv\Scripts\python.exe -m rpa.run deals >> logs\rpa-deals.log 2>&1"
if errorlevel 1 exit /b 1
echo 등록 완료: %TASK% (매일 09:00~21:30, 30분 간격) - %ROOT%
