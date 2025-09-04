# test.ps1
# PowerShell script to send a test request to the running service.

param(
    # The port the local container is running on. Defaults to 8000.
    [string]$HostPort = "8000"
)

Write-Host "Running PowerShell test request against local container on port $HostPort..."

# Check if the required image files exist
if (-not (Test-Path "person.jpg")) {
    Write-Error "Error: 'person.jpg' not found in the current directory."
    exit 1
}
if (-not (Test-Path "garment.jpg")) {
    Write-Error "Error: 'garment.jpg' not found in the current directory."
    exit 1
}

# Construct the request body
$person_b64 = [Convert]::ToBase64String([System.IO.File]::ReadAllBytes("person.jpg"))
$garment_b64 = [Convert]::ToBase64String([System.IO.File]::ReadAllBytes("garment.jpg"))

$body = @{
    person_image = $person_b64
    garment_image = $garment_b64
} | ConvertTo-Json

$uri = "http://localhost:$HostPort/api/v1/tryon"

# Send the request
try {
    $response = Invoke-WebRequest -Uri $uri -Method POST -ContentType "application/json" -Body $body -UseBasicParsing
    Write-Host "Test request sent successfully. Status: $($response.StatusCode)"
    Write-Host "Response content:"
    # The response content is a JSON string, we can format it for readability
    $response.Content | ConvertFrom-Json | ConvertTo-Json -Depth 100
}
catch {
    Write-Error "Failed to send test request: $_"
    exit 1
}
