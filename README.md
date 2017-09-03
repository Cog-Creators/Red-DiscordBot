[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg?style=flat-square)](http://makeapullrequest.com)

# Red - Discord Bot v3

**This is alpha and very much a work in progress. Regular use is not recommended.
There will not be any effort not to break current installations.**

# How to install

Red V3 has a very similar way to V2 to start, but still a bit different.

## I already have a running V2 Red bot on my machine

This section is for those who already have the requirements installed (git and python)

### Windows

Open a new git bash window by right-clicking in a folder and selection `Git bash here` and type the following command:

```
git clone -b V3/develop --single-branch https://github.com/Twentysix26/Red-DiscordBot.git Red-DiscordBot
```

Install the requirements by opening a command prompt, moving to your `Red-DiscordBot` folder using the `cd` command (example: `cd Documents/Discord/Bots/Red-DiscordBot`) and type this command:

```
pip install -U -r requirements.txt
```

Now you can run Red using `start_launcher.bat`. Follow [this guide](https://twentysix26.github.io/Red-Docs/red_guide_bot_accounts/#creating-a-new-bot-account) to create a new bot user token.

### Mac and Linux

Open a new terminal and type the following command:

```
git clone -b V3/develop --single-branch https://github.com/Twentysix26/Red-DiscordBot.git Red-DiscordBot
```

Note that if you want the folder in another location, you can move to your directory using `cd` (example: `cd Documents/Discord/Bots`)

**This command is only for Mac users** Run this command:

```
export PATH=$PATH:/usr/local/Cellar/opus/1.1.2/lib/
```

Now open the folder, still trough the terminal, by typing this:

```
cd Red-DiscordBot
```

And install the requirements

```
pip install -U -r requirements.txt
```

Now you can run Red launching `main.py` instead of `launcher.py` which is empty for now:

```
python3.6 main.py
```

Follow [this guide](https://twentysix26.github.io/Red-Docs/red_guide_bot_accounts/#creating-a-new-bot-account) to create a new bot user token.

## I have no running Red bot on my machine

Then you need to install all of the requirements needed

### Windows

You need to install [Git](https://git-scm.com/download/win) and [Python](https://www.python.org/downloads/)

Open the respectives links and follow the installations steps. **Note that for Git, you need to tick this case**

![git](http://i.imgur.com/guis7EE.png)

**For Python, you also need to tick this case**

![python](http://i.imgur.com/tTeIWaW.png)

Now that the softwares are installed, open a new git bash window by right-clicking in a folder and selection `Git bash here` and type the following command:

```
git clone -b V3/develop --single-branch https://github.com/Twentysix26/Red-DiscordBot.git Red-DiscordBot
```

Install the requirements by opening a command prompt, moving to your `Red-DiscordBot` folder using the `cd` command (example: `cd Documents/Discord/Bots/Red-DiscordBot`) and type this command:

```
pip install -U -r requirements.txt
```

Now you can run Red using `start_launcher.bat`. Follow [this guide](https://twentysix26.github.io/Red-Docs/red_guide_bot_accounts/#creating-a-new-bot-account) to create a new bot user token.

### Mac

Open a new terminal and install brew:

```
 /usr/bin/ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"
```

Install the required softwares:

```
brew install python3 --with-brewed-openssl
brew install git
brew install ffmpeg --with-ffplay
brew install opus
```

Now type the following command:

```
git clone -b V3/develop --single-branch https://github.com/Twentysix26/Red-DiscordBot.git Red-DiscordBot
```

Note that if you want the folder in another location, you can move to your directory using `cd` (example: `cd Documents/Discord/Bots`)

Run this command:

```
export PATH=$PATH:/usr/local/Cellar/opus/1.1.2/lib/
```

Open the folder, still trough the terminal, by typing this:

```
cd Red-DiscordBot
```

And install the requirements

```
pip install -U -r requirements.txt
```

Now you can run Red launching `main.py` instead of `launcher.py` which is empty for now:

```
python3.6 main.py
```

Follow [this guide](https://twentysix26.github.io/Red-Docs/red_guide_bot_accounts/#creating-a-new-bot-account) to create a new bot user token.

### Linux

Open a new terminal and install pre-requirements by typing these commands depending on your distro:

__Ubuntu__:

```
apt-get install python3.5-dev python3-pip build-essential libssl-dev libffi-dev git ffmpeg libopus-dev unzip -y
```

__Debian 8__:

```
echo "deb http://httpredir.debian.org/debian jessie-backports main contrib non-free" >> /etc/apt/sources.list
apt-get update
apt-get install build-essential libssl-dev libffi-dev git ffmpeg libopus-dev unzip -y
wget https://www.python.org/ftp/python/3.6.0/Python-3.6.0.tgz
tar xvf Python-3.6.0.tgz
cd Python-3.6.0
./configure --enable-optimizations
make -j4
make altinstall
cd ..
wget https://bootstrap.pypa.io/get-pip.py
python3.6 get-pip.py
```

__Archlinux__:

```
pacman -S python python-pip git ffmpeg base-devel openssl libffi libsodium
```

__CentOS__:

```
yum -y groupinstall development
yum -y install https://centos7.iuscommunity.org/ius-release.rpm
yum -y install yum-utils wget which python35u python35u-pip python35u-devel openssl-devel libffi-devel git opus-devel
sh -c "$(wget https://gist.githubusercontent.com/mustafaturan/7053900/raw/27f4c8bad3ee2bb0027a1a52dc8501bf1e53b270/latest-ffmpeg-centos6.sh -O -)"
```

*For other distro, look at the official [V2 guide](https://twentysix26.github.io/Red-Docs/red_install_linux/) and look at the* `Install pre-requirements` *part*

Type the following command:

```
git clone -b V3/develop --single-branch https://github.com/Twentysix26/Red-DiscordBot.git Red-DiscordBot
```

Note that if you want the folder in another location, you can move to your directory using `cd` (example: `cd Documents/Discord/Bots`)


Now open the folder, still trough the terminal, by typing this:

```
cd Red-DiscordBot
```

And install the requirements

```
pip install -U -r requirements.txt
```

Now you can run Red launching `main.py` instead of `launcher.py` which is empty for now:

```
python3.6 main.py
```

Follow [this guide](https://twentysix26.github.io/Red-Docs/red_guide_bot_accounts/#creating-a-new-bot-account) to create a new bot user token.
