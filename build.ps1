# Script PowerShell para geração do executável Standalone Windows
$ErrorActionPreference = "Stop"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "     Compilando SCAN BOT Rede com PyInstaller            " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# Garante instalação das dependências
Write-Host "[1/4] Verificando dependências..." -ForegroundColor Yellow
python -m pip install -r requirements.txt

# Executa os testes automatizados antes do empacotamento
Write-Host "[2/4] Executando suíte de testes..." -ForegroundColor Yellow
python -m unittest discover -s tests -p "test_*.py"

# Embute o cliente desktop do Flet no .exe. Sem isso, o app baixa o cliente do GitHub
# na primeira execução e falha em redes com inspeção SSL (CERTIFICATE_VERIFY_FAILED).
Write-Host "      Empacotando cliente desktop do Flet (offline)..." -ForegroundColor Yellow
python tools\bundle_flet_client.py "build\flet_client\flet-windows.zip"
if ($LASTEXITCODE -ne 0) { throw "Falha ao empacotar o cliente Flet." }

# Executa o PyInstaller (version_info.txt define o fornecedor LLSystem nos metadados)
Write-Host "[3/4] Gerando executável único (.exe) com PyInstaller..." -ForegroundColor Yellow
python -m PyInstaller --noconfirm --onefile --windowed `
    --name "SCAN-BOT-Rede" `
    --version-file "version_info.txt" `
    --add-data "backend;backend" `
    --add-data "frontend;frontend" `
    --collect-all "flet" `
    --collect-all "flet_desktop" `
    --collect-all "reportlab" `
    --hidden-import "httpx" `
    --add-data "build\flet_client\flet-windows.zip;flet_desktop\app" `
    main.py

# Assina digitalmente o executável para o Windows exibir "Fornecedor: LLSystem"
Write-Host "[4/4] Assinando digitalmente o executável (LLSystem)..." -ForegroundColor Yellow
$exePath = "dist\SCAN-BOT-Rede.exe"
$cert = Get-ChildItem Cert:\CurrentUser\My -CodeSigningCert |
    Where-Object { $_.Subject -like "CN=LLSystem*" -and $_.NotAfter -gt (Get-Date) } |
    Sort-Object NotAfter -Descending |
    Select-Object -First 1

if ($cert) {
    try {
        $sig = Set-AuthenticodeSignature -FilePath $exePath -Certificate $cert -HashAlgorithm SHA256 `
            -TimestampServer "http://timestamp.digicert.com"
    } catch {
        Write-Host "  Servidor de timestamp indisponível, assinando sem carimbo de tempo..." -ForegroundColor DarkYellow
        $sig = Set-AuthenticodeSignature -FilePath $exePath -Certificate $cert -HashAlgorithm SHA256
    }
    Write-Host "  Assinatura: $($sig.Status) - $($sig.SignerCertificate.Subject)" -ForegroundColor Green
} else {
    Write-Host "  Certificado LLSystem não encontrado. O .exe NÃO foi assinado." -ForegroundColor DarkYellow
    Write-Host "  Execute .\criar-certificado-llsystem.ps1 uma vez e rode o build novamente." -ForegroundColor DarkYellow
}

Write-Host "==========================================================" -ForegroundColor Green
Write-Host "  Sucesso! Executável único gerado: dist/SCAN-BOT-Rede.exe " -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green
