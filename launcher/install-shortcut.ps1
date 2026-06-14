$shell = New-Object -ComObject WScript.Shell
$desktop = [Environment]::GetFolderPath('Desktop')
$shortcutPath = Join-Path $desktop 'Scour.lnk'

$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = 'cmd.exe'
$shortcut.Arguments = '/c "' + $PSScriptRoot + '\start-scour.bat"'
$shortcut.WorkingDirectory = Split-Path $PSScriptRoot -Parent
$shortcut.Description = 'Launch Scour'
$shortcut.IconLocation = $PSScriptRoot + '\scour.ico,0'
$shortcut.WindowStyle = 7
$shortcut.Save()

Write-Host "Scour shortcut created at: $shortcutPath"
