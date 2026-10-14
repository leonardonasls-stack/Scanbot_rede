# Cria (uma unica vez) um certificado de assinatura de codigo autoassinado "LLSystem"
# e o marca como confiavel para o usuario atual. Depois disso, o build.ps1 assina
# automaticamente o SCAN-BOT-Rede.exe e o Windows passa a exibir "Fornecedor: LLSystem".
#
# IMPORTANTE: certificado autoassinado so e reconhecido nas maquinas onde o arquivo
# LLSystem-CodeSigning.cer for instalado. Para reconhecimento publico em qualquer PC,
# e necessario um certificado de Code Signing emitido por uma CA (DigiCert, Sectigo etc.).
$ErrorActionPreference = "Stop"

$subject = "CN=LLSystem, O=LLSystem, C=BR"
$cerPath = Join-Path $PSScriptRoot "LLSystem-CodeSigning.cer"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "     Certificado de Assinatura de Codigo - LLSystem       " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$cert = Get-ChildItem Cert:\CurrentUser\My -CodeSigningCert |
    Where-Object { $_.Subject -like "CN=LLSystem*" -and $_.NotAfter -gt (Get-Date) } |
    Sort-Object NotAfter -Descending |
    Select-Object -First 1

if ($cert) {
    Write-Host "[1/3] Certificado existente encontrado (validade: $($cert.NotAfter.ToShortDateString()))." -ForegroundColor Yellow
} else {
    Write-Host "[1/3] Gerando novo certificado '$subject'..." -ForegroundColor Yellow
    $cert = New-SelfSignedCertificate `
        -Type CodeSigningCert `
        -Subject $subject `
        -FriendlyName "LLSystem Code Signing" `
        -KeyAlgorithm RSA -KeyLength 3072 -HashAlgorithm SHA256 `
        -CertStoreLocation Cert:\CurrentUser\My `
        -NotAfter (Get-Date).AddYears(5)
}

Write-Host "[2/3] Exportando chave publica para $cerPath ..." -ForegroundColor Yellow
Export-Certificate -Cert $cert -FilePath $cerPath | Out-Null

Write-Host "[3/3] Marcando como confiavel (o Windows pedira confirmacao)..." -ForegroundColor Yellow
Import-Certificate -FilePath $cerPath -CertStoreLocation Cert:\CurrentUser\Root | Out-Null
Import-Certificate -FilePath $cerPath -CertStoreLocation Cert:\CurrentUser\TrustedPublisher | Out-Null

Write-Host "==========================================================" -ForegroundColor Green
Write-Host "  Pronto! Execute .\build.ps1 para gerar o .exe assinado.  " -ForegroundColor Green
Write-Host "  Para outros PCs, instale o arquivo LLSystem-CodeSigning.cer" -ForegroundColor Green
Write-Host "  em 'Autoridades de Certificacao Raiz Confiaveis' e        " -ForegroundColor Green
Write-Host "  'Fornecedores Confiaveis' (Computador Local)." -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green
