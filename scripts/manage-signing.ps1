<#
.SYNOPSIS
    Manage code signing for Busy Whatsapp Bridge.
.DESCRIPTION
    Generates a self-signed certificate and signs executables.
#>

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("generate", "sign")]
    [string]$Action,

    [Parameter(Mandatory=$false)]
    [string]$File
)

$ErrorActionPreference = "Stop"

$CertName = "vibhor1102 Developer"
$CertFile = "vibhor1102-dev.pfx"
$PublicCertFile = "vibhor1102-dev.cer"
$Password = "busy-bridge-sign" # Internal password for the PFX

function Generate-Certificate {
    # If PFX already exists, we don't need to do anything (unless we want to refresh public cert)
    if (Test-Path $CertFile) {
        Write-Host "Found existing PFX certificate: $CertFile" -ForegroundColor Green
        
        # Ensure public CER still exists
        if (-not (Test-Path $PublicCertFile)) {
            Write-Host "Public certificate missing. Extracting from PFX..." -ForegroundColor Yellow
            $cert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2($CertFile, $Password)
            $export = $cert.Export([System.Security.Cryptography.X509Certificates.X509ContentType]::Cert)
            [System.IO.File]::WriteAllBytes((Join-Path (Get-Location) $PublicCertFile), $export)
        }
        return
    }

    Write-Host "PFX not found. Checking for existing certificate in Windows Store..." -ForegroundColor Cyan
    $existing = Get-ChildItem Cert:\CurrentUser\My | Where-Object { $_.Subject -like "*CN=$CertName*" }
    
    if ($existing) {
        Write-Host "Found existing certificate in store. Exporting..." -ForegroundColor Green
        $Cert = $existing[0]
    } else {
        Write-Host "Creating new self-signed certificate..." -ForegroundColor Yellow
        $Cert = New-SelfSignedCertificate -Type CodeSigningCert -Subject "CN=$CertName" -HashAlgorithm SHA256 -KeyLength 2048 -CertStoreLocation "Cert:\CurrentUser\My" -NotAfter (Get-Date).AddYears(5)
    }

    # Export PFX (private key + cert)
    $pwd = ConvertTo-SecureString -String $Password -Force -AsPlainText
    Export-PfxCertificate -Cert $Cert -FilePath $CertFile -Password $pwd
    
    # Export CER (public cert only)
    Export-Certificate -Cert $Cert -FilePath $PublicCertFile
    
    Write-Host "Done! Generated files:" -ForegroundColor Green
    Write-Host "  $CertFile (Private Key - DO NOT DISTRIBUTE)"
    Write-Host "  $PublicCertFile (Public Cert - SHARE WITH USERS)"
}

function Sign-File {
    if (-not $File) {
        Write-Error "File path is required for sign action."
        exit 1
    }

    if (-not (Test-Path $File)) {
        Write-Error "File not found: $File"
        exit 1
    }

    Write-Host "Signing $File ..." -ForegroundColor Cyan
    
    # Check if PFX exists
    if (-not (Test-Path $CertFile)) {
        Write-Host "PFX file not found. Generating first..." -ForegroundColor Yellow
        Generate-Certificate
    }

    # Load certificate from PFX
    $cert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2($CertFile, $Password, [System.Security.Cryptography.X509Certificates.X509KeyStorageFlags]::Exportable)

    $null = Set-AuthenticodeSignature -FilePath $File -Certificate $cert -HashAlgorithm SHA256 -TimestampServer "http://timestamp.digicert.com"

    $status = Get-AuthenticodeSignature -FilePath $File
    if ($status.SignatureType -eq "None" -or -not $status.SignerCertificate) {
        Write-Error "Signing failed: no signature embedded in file."
        exit 1
    }

    if ($status.Status -eq "Valid") {
        Write-Host "Successfully signed: $File" -ForegroundColor Green
    } elseif ($status.Status -in @("UnknownError", "NotTrusted")) {
        Write-Host "Signed with status: $($status.Status) (signature is present)." -ForegroundColor Yellow
    } else {
        Write-Error "Signing failed: status is '$($status.Status)'."
        exit 1
    }
}

switch ($Action) {
    "generate" { Generate-Certificate }
    "sign" { Sign-File }
}
