param(
    [string]$PgBin = "C:\Program Files\PostgreSQL\18\bin",
    [string]$PostgresUser = "postgres",
    [string]$DatabaseName = "fieldforce",
    [string]$AppUser = "fieldforce",
    [string]$AppPassword = "fieldforce_password"
)

$ErrorActionPreference = "Stop"

$psql = Join-Path $PgBin "psql.exe"
if (-not (Test-Path $psql)) {
    throw "psql.exe not found at $psql"
}

$vectorControl = "C:\Program Files\PostgreSQL\18\share\extension\vector.control"
$vectorDll = "C:\Program Files\PostgreSQL\18\lib\vector.dll"
if (-not (Test-Path $vectorControl) -or -not (Test-Path $vectorDll)) {
    throw "pgvector is not installed into PostgreSQL 18. Missing vector.control or vector.dll."
}

$schemaPath = Join-Path (Resolve-Path ".") "database\schema.sql"
if (-not (Test-Path $schemaPath)) {
    throw "Schema file not found at $schemaPath"
}

$securePassword = Read-Host "PostgreSQL password for user '$PostgresUser'" -AsSecureString
$passwordPtr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword)
$postgresPassword = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($passwordPtr)
[Runtime.InteropServices.Marshal]::ZeroFreeBSTR($passwordPtr)

try {
    $env:PGPASSWORD = $postgresPassword

    $adminSql = @"
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = '$DatabaseName'
  AND pid <> pg_backend_pid();

DROP DATABASE IF EXISTS $DatabaseName;

DO `$`$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '$AppUser') THEN
        CREATE ROLE $AppUser LOGIN PASSWORD '$AppPassword';
    ELSE
        ALTER ROLE $AppUser LOGIN PASSWORD '$AppPassword';
    END IF;
END
`$`$;

CREATE DATABASE $DatabaseName;
GRANT ALL PRIVILEGES ON DATABASE $DatabaseName TO $AppUser;
"@

    $adminSqlPath = Join-Path $env:TEMP "fieldforce_admin_setup.sql"
    Set-Content -Path $adminSqlPath -Value $adminSql -Encoding UTF8

    & $psql -v ON_ERROR_STOP=1 -U $PostgresUser -d postgres -f $adminSqlPath
    if ($LASTEXITCODE -ne 0) {
        throw "Admin database setup failed."
    }

    & $psql -v ON_ERROR_STOP=1 -U $PostgresUser -d $DatabaseName -f $schemaPath
    if ($LASTEXITCODE -ne 0) {
        throw "Schema apply failed."
    }

    $grantSql = @"
GRANT USAGE ON SCHEMA public TO $AppUser;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO $AppUser;
GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO $AppUser;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO $AppUser;
"@

    $grantSqlPath = Join-Path $env:TEMP "fieldforce_grants.sql"
    Set-Content -Path $grantSqlPath -Value $grantSql -Encoding UTF8

    & $psql -v ON_ERROR_STOP=1 -U $PostgresUser -d $DatabaseName -f $grantSqlPath
    if ($LASTEXITCODE -ne 0) {
        throw "Grant setup failed."
    }

    & $psql -U $PostgresUser -d $DatabaseName -c "\dx"
    & $psql -U $PostgresUser -d $DatabaseName -c "\dt"

    Write-Host ""
    Write-Host "Database setup complete." -ForegroundColor Green
    Write-Host "DATABASE_URL=postgresql+asyncpg://$AppUser`:$AppPassword@localhost:5432/$DatabaseName"
    Write-Host "SYNC_DATABASE_URL=postgresql://$AppUser`:$AppPassword@localhost:5432/$DatabaseName"
}
finally {
    Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
}
