$procarch = $env:PROCESSOR_ARCHITECTURE
$filename = $NULL

# Powershell version check because ConvertFrom-JSON was introduced in
# v3 and is required for getting the latest Git for Windows version
if ($PSVersionTable.PSVersion.Major -lt 3)
{
    echo "You need at least PowerShell 3.0 to run me!"
    return
}

# Install python
if (((gcm "python.exe" -ErrorAction SilentlyContinue) -eq $null) -or -not ((gcm "python.exe" -ErrorAction SilentlyContinue | select -expand Version).major -eq 3 -and (gcm "python.exe" -ErrorAction SilentlyContinue | select -expand Version).minor -eq 5))
{
echo "Downloading Python"
if ($procarch -eq "AMD64")
{
    wget -Uri https://www.python.org/ftp/python/3.5.3/python-3.5.3-amd64.exe -OutFile "python-3.5.3-amd64.exe"
    $filename = "python-3.5.3-amd64.exe"
}
    
else
{
    wget -Uri https://www.python.org/ftp/python/3.5.3/python-3.5.3.exe -OutFile "python-3.5.3.exe"
    $filename = "python-3.5.3.exe"
}
echo $filename
echo "Launching Python"
$launchpath = ".\\" + $filename
$ret = & $launchpath /passive PrependPath=1 InstallLauncherAllUsers=0
echo $ret
echo "Done installing Python."
}
# Python installed

if ((gcm "git.exe" -ErrorAction SilentlyContinue) -eq $null)
{
echo "Downloading Git"

# Install Git

if ($procarch -eq "AMD64")
{
    $data = wget -Uri https://api.github.com/repos/git-for-windows/git/releases/latest
    $converted = ConvertFrom-JSON $data | select -expand assets | where { $_.name.EndsWith("64-bit.tar.bz2")}
    $gitfname = $converted.name
    wget -Uri $converted.browser_download_url -OutFile $gitfname
    echo "Finished downloading Git, extracting..."
    $gitdir = $env:LOCALAPPDATA + "\Programs\Git"
    python -m tarfile -e $gitfname $gitdir
    echo "Finished extracting Git. Adding to path..."
    $gitexedir = $gitdir + "\bin"
    $oldpath = (Get-ItemProperty -Path 'Registry::HKEY_CURRENT_USER\Environment' -Name PATH).path
    if ($oldpath.Split(";") -notcontains $gitexedir)
    {
        $newpath = "$oldpath;$gitexedir"
        Set-ItemProperty -Path 'Registry::HKEY_CURRENT_USER\Environment' -Name PATH -Value $newpath
    }
}
else
{
    $data = wget -Uri https://api.github.com/repos/git-for-windows/git/releases/latest
    $converted = ConvertFrom-JSON $data | select -expand assets | where { $_.name.EndsWith("32-bit.tar.bz2")}
    $gitfname = $converted.name
    wget -Uri $converted.browser_download_url -OutFile $gitfname
    echo "Finished downloading Git, extracting..."
    $gitdir = $env:LOCALAPPDATA + "\Programs\Git"
    python -m tarfile -e $gitfname $gitdir
    echo "Finished extracting Git. Adding to path..."
    $gitexedir = $gitdir + "\bin"
    $oldpath = (Get-ItemProperty -Path 'Registry::HKEY_CURRENT_USER\Environment' -Name PATH).path
    if ($oldpath.Split(";") -notcontains $gitexedir)
    {
        $newpath = "$oldpath;$gitexedir"
        Set-ItemProperty -Path 'Registry::HKEY_CURRENT_USER\Environment' -Name PATH -Value $newpath
    }
}

# Git installed
echo "Git installed"
}

if (((gcm "ffmpeg.exe" -ErrorAction SilentlyContinue) -eq $null) -or ((gcm "ffplay.exe" -ErrorAction SilentlyContinue) -eq $null) -or ((gcm "ffprobe.exe" -ErrorAction SilentlyContinue) -eq $null))
{
# Install ffmpeg
echo "Installing ffmpeg"
if ($procarch -eq "AMD64")
{
    wget -Uri https://ffmpeg.zeranoe.com/builds/win64/static/ffmpeg-latest-win64-static.zip -OutFile ffmpeg-latest-win64.zip
    $ffdir = $env:LOCALAPPDATA + "\Programs\ffmpeg"
    $extractdir = $ffdir + "\ffmpeg-latest-win64-static"
    $ffexedir = $ffdir + "\bin"
    python -m zipfile -e ffmpeg-latest-win64.zip $ffdir
    Move-Item -Path "$extractdir\*" -Destination $ffdir
    Get-ChildItem -Path $extractdir -Recurse -Directory | Remove-Item
    $oldpath = (Get-ItemProperty -Path 'Registry::HKEY_CURRENT_USER\Environment' -Name PATH).path
    if ($oldpath.Split(";") -notcontains $ffexedir)
    {
        $newpath = "$oldpath;$ffexedir"
        Set-ItemProperty -Path 'Registry::HKEY_CURRENT_USER\Environment' -Name PATH -Value $newpath
    }
}
else
{
    wget -Uri https://ffmpeg.zeranoe.com/builds/win32/static/ffmpeg-latest-win32-static.zip -OutFile ffmpeg-latest-win32.zip
    $ffdir = $env:LOCALAPPDATA + "\Programs\ffmpeg"
    $extractdir = $ffdir + "\ffmpeg-latest-win32-static"
    $ffexedir = $ffdir + "\bin"
    python -m zipfile -e ffmpeg-latest-win32.zip $ffdir
    Move-Item -Path "$extractdir\*" -Destination $ffdir
    Get-ChildItem -Path $extractdir -Recurse -Directory | Remove-Item
    $oldpath = (Get-ItemProperty -Path 'Registry::HKEY_CURRENT_USER\Environment' -Name PATH).path
    if ($oldpath.Split(";") -notcontains $ffexedir)
    {
        $newpath = "$oldpath;$ffexedir"
        Set-ItemProperty -Path 'Registry::HKEY_CURRENT_USER\Environment' -Name PATH -Value $newpath
    }
}
echo "ffmpeg installed"
}
# echo "Downloading install.py"
# wget -Uri http://example.com
echo "Done installing prerequisites for Red. You may now continue by running python install.py."
echo "If you have issues with that, try logging out and back into your account or restarting your computer"
