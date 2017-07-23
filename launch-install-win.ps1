$procarch = $env:PROCESSOR_ARCHITECTURE
$filename = $NULL

# Install python

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
& $launchpath /passive PrependPath=1 InstallLauncherAllUsers=0

# Python installed

echo "Done installing Python. Downloading launcher"


