To install/update pyenv, run the following command:

.. prompt:: bash

    command -v pyenv && pyenv update || curl https://pyenv.run | bash

After this command, you will see a warning about 'pyenv' not being in the load path. To address this,
you should run these commands:

.. prompt:: bash

    profile=$([ -n "$ZSH_VERSION" ] && echo ~/.zprofile || ([ -f ~/.bash_profile ] && echo ~/.bash_profile || echo ~/.profile))
    rcfile=$([ -n "$ZSH_VERSION" ] && echo ~/.zshrc || echo ~/.bashrc)
    printf '%s\n%s\n%s\n' 'export PYENV_ROOT="$HOME/.pyenv"' 'export PATH="$PYENV_ROOT/bin:$PATH"' "$([ -f "$profile" ] && cat "$profile")" > "$profile"
    echo 'eval "$(pyenv init --path)"' >> "$profile"
    echo 'eval "$(pyenv init -)"' >> "$rcfile"
    echo 'eval "$(pyenv virtualenv-init -)"' >> "$rcfile"

Then **log out and log back in** and run the following command:
