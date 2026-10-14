# Script PowerShell para geração do executável Standalone Windows
$ErrorActionPreference = "Stop"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "     Compilando SCAN BOT Rede com PyInstaller            " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# Garante instalação das dependências
Write-Host "[1/3] Verificando dependências..." -ForegroundColor Yellow
python -m pip install -r requirements.txt

# Executa os testes automatizados antes do empacotamento
Write-Host "[2/3] Executando suíte de testes..." -ForegroundColor Yellow
python -m unittest discover -s tests -p "test_*.py"

# Executa o PyInstaller
Write-Host "[3/3] Gerando executável com PyInstaller..." -ForegroundColor Yellow
python -m PyInstaller --noconfirm --onedir --windowed `
    --name "SCAN-BOT-Rede" `
    --add-data "backend;backend" `
    --add-data "frontend;frontend" `
    --hidden-import "httpx" `
    --hidden-import "reportlab" `
    --hidden-import "flet" `
    main.py

Write-Host "==========================================================" -ForegroundColor Green
Write-Host "  Sucesso! Executável gerado na pasta dist/SCAN-BOT-Rede/  " -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green
