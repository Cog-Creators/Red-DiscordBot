$procarch = $env:PROCESSOR_ARCHITECTURE
$filename = $NULL

# Install python
if (((gcm "python.exe" -ErrorAction SilentlyContinue) -eq $null) -or -not ((gcm "python.exe" -ErrorAction SilentlyContinue | select -expand Version).major -eq 3 -and (gcm "python.exe" -ErrorAction SilentlyContinue | select -expand Version).minor -eq 5 -and (gcm "python.exe" -EA SilentlyContinue | select -expand Version).build -match '^4'))
{
echo "Downloading Python"
$wc = New-Object System.Net.WebClient
if ($procarch -eq "AMD64")
{
    $wc.DownloadFile("https://www.python.org/ftp/python/3.5.4/python-3.5.4-amd64.exe", (Get-Location).path + "\" + "python-3.5.4-amd64.exe")
    $filename = "python-3.5.4-amd64.exe"
}

else
{
    $wc.DownloadFile("https://www.python.org/ftp/python/3.5.4/python-3.5.4.exe", (Get-Location).path + "\" + "python-3.5.4.exe")
    $filename = "python-3.5.4.exe"
}
echo "Launching Python installer..."
$launchpath = (Get-Location).path + "\" + $filename
$ret = & $launchpath /passive PrependPath=1 InstallLauncherAllUsers=0
echo "Python installer has been launched. You can check its progress in its window."
echo "When the installer finishes, you can try running:"
echo "python install.py"
echo "If you get an error running that, log out and back in and try again"
}
