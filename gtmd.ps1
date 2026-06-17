$ErrorActionPreference = "Stop"

function Wait-ForTap {
    param([string]$Message = "Press any key to continue to the next step...")
    Write-Host ""
    Write-Host $Message -ForegroundColor Cyan
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    Write-Host ""
}

function Print-Header {
    param([string]$Title)
    Write-Host "=======================================================" -ForegroundColor Magenta
    Write-Host "🚀 $Title" -ForegroundColor Magenta
    Write-Host "=======================================================" -ForegroundColor Magenta
}

Clear-Host
Print-Header "Movie Scraper API - Interactive Journey"
Write-Host "Before we begin, ensure your Docker Compose services are running!" -ForegroundColor Yellow
Write-Host "The API should be available at http://localhost:8000" -ForegroundColor Gray
Wait-ForTap "Press any key to start the journey..."

# ---------------------------------------------------------
# Step 1: Health Check
# ---------------------------------------------------------
Print-Header "Step 1: Check System Health (No Auth)"
Write-Host "Executing: GET http://localhost:8000/health" -ForegroundColor DarkGray
try {
    $health = Invoke-RestMethod -Uri "http://localhost:8000/health" -Method Get
    $health | ConvertTo-Json | Write-Host -ForegroundColor Green
}
catch {
    Write-Host "Failed to connect. Is the server running?" -ForegroundColor Red
    exit
}

Wait-ForTap "Health is good! Tap to Login..."

# ---------------------------------------------------------
# Step 2: Login
# ---------------------------------------------------------
Print-Header "Step 2: Login as Admin"
Write-Host "Executing: POST http://localhost:8000/auth/login" -ForegroundColor DarkGray
$loginBody = @{
    username = "admin"
    password = "admin123"
} | ConvertTo-Json

try {
    $tokenResponse = Invoke-RestMethod -Uri "http://localhost:8000/auth/login" -Method Post -Body $loginBody -ContentType "application/json"
    $tokenResponse | ConvertTo-Json | Write-Host -ForegroundColor Green
    
    $global:token = $tokenResponse.access_token
    $global:headers = @{
        "Authorization" = "Bearer $global:token"
        "Content-Type"  = "application/json"
    }
    Write-Host "`n✅ Successfully acquired JWT token!" -ForegroundColor Cyan
}
catch {
    Write-Host "Login failed." -ForegroundColor Red
    exit
}

Wait-ForTap "Token saved in memory. Tap to fetch the Movie list..."

# ---------------------------------------------------------
# Step 3: List Movies
# ---------------------------------------------------------
Print-Header "Step 3: List Movies (Protected)"
Write-Host "Executing: GET http://localhost:8000/movies?page=1&limit=5" -ForegroundColor DarkGray

$movies = Invoke-RestMethod -Uri "http://localhost:8000/movies?page=1&limit=5" -Method Get -Headers $global:headers
$movies | ConvertTo-Json -Depth 4 | Write-Host -ForegroundColor Green

Write-Host "`nTotal Active Movies in DB: $($movies.meta.total)" -ForegroundColor Cyan

if ($movies.data.Count -eq 0) {
    Write-Host "`n❌ No movies found! You need to run the scraper first." -ForegroundColor Red
    exit
}

# Grab the first movie ID to play with
$targetMovie = $movies.data[0]
$movieId = $targetMovie.id

Wait-ForTap "We grabbed movie ID: $movieId. Tap to fetch that specific single movie..."

# ---------------------------------------------------------
# Step 3.5: GET Single Movie
# ---------------------------------------------------------
Print-Header "Step 3.5: GET Single Movie (Protected)"
Write-Host "Executing: GET http://localhost:8000/movies/$movieId" -ForegroundColor DarkGray

$singleMovie = Invoke-RestMethod -Uri "http://localhost:8000/movies/$movieId" -Method Get -Headers $global:headers
$singleMovie | ConvertTo-Json -Depth 4 | Write-Host -ForegroundColor Green


Wait-ForTap "Notice the title of the movie. Tap to Update it..."

# ---------------------------------------------------------
# Step 4: Update Movie (PATCH)
# ---------------------------------------------------------
Print-Header "Step 4: Update Movie Title (Protected)"
$newTitle = "$($targetMovie.title) (HACKED BY POWERSHELL)"
Write-Host "Executing: PATCH http://localhost:8000/movies/$movieId" -ForegroundColor DarkGray
Write-Host "Payload: { title: '$newTitle' }" -ForegroundColor DarkGray

$patchBody = @{
    title = $newTitle
} | ConvertTo-Json

$updatedMovie = Invoke-RestMethod -Uri "http://localhost:8000/movies/$movieId" -Method Patch -Headers $global:headers -Body $patchBody
$updatedMovie | ConvertTo-Json | Write-Host -ForegroundColor Green

Wait-ForTap "The title in the database has been updated. Tap to Hard-Delete it..."

# ---------------------------------------------------------
# Step 5: Delete Movie (DELETE)
# ---------------------------------------------------------
Print-Header "Step 5: Hard-Delete Movie (Protected)"
Write-Host "Executing: DELETE http://localhost:8000/movies/$movieId" -ForegroundColor DarkGray

Invoke-RestMethod -Uri "http://localhost:8000/movies/$movieId" -Method Delete -Headers $global:headers
Write-Host "✅ Server returned 204 No Content (Successfully deleted)." -ForegroundColor Green

Wait-ForTap "The movie has been permanently deleted from the DB. Tap to verify it's gone from the API..."

# ---------------------------------------------------------
# Step 6: Verify Deletion
# ---------------------------------------------------------
Print-Header "Step 6: Verify Deletion"
Write-Host "Executing: GET http://localhost:8000/movies/$movieId" -ForegroundColor DarkGray

try {
    Invoke-RestMethod -Uri "http://localhost:8000/movies/$movieId" -Method Get -Headers $global:headers
}
catch {
    Write-Host "✅ Server correctly returned 404 Not Found!" -ForegroundColor Green
}

Write-Host "`nLet's check the total list count again..." -ForegroundColor DarkGray
$moviesAfter = Invoke-RestMethod -Uri "http://localhost:8000/movies?page=1&limit=5" -Method Get -Headers $global:headers
Write-Host "Total Active Movies now: $($moviesAfter.meta.total) (It went down by 1!)" -ForegroundColor Green

Wait-ForTap "Journey Complete! Press any key to exit..."
Write-Host "Done." -ForegroundColor Magenta