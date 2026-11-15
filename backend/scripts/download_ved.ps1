# Official Vehicle Energy Dataset (VED) downloader for Windows PowerShell.
# Source: https://github.com/gsoh/VED (Apache-2.0)
# Tonight: Part 1 is enough to begin. Download Part 2 only after the pipeline is proven.

param(
  [string]$Destination = "$PSScriptRoot\..\data\raw_ved",
  [switch]$Part2
)

New-Item -ItemType Directory -Force -Path $Destination | Out-Null

$part1 = "https://github.com/gsoh/VED/raw/refs/heads/master/Data/VED_DynamicData_Part1.7z"
$part2 = "https://github.com/gsoh/VED/raw/refs/heads/master/Data/VED_DynamicData_Part2.7z"

Write-Host "Downloading official VED Part 1..."
Invoke-WebRequest -Uri $part1 -OutFile (Join-Path $Destination "VED_DynamicData_Part1.7z")

if ($Part2) {
  Write-Host "Downloading official VED Part 2..."
  Invoke-WebRequest -Uri $part2 -OutFile (Join-Path $Destination "VED_DynamicData_Part2.7z")
}

Write-Host "Download complete. Extract the .7z archive(s) with 7-Zip into the same raw_ved folder."
Write-Host "Then run: python scripts/prepare_ved.py --input-dir data/raw_ved --output-dir data/prepared_ved --max-trips 80"
