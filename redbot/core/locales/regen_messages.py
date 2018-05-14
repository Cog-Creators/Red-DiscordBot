import subprocess

TO_TRANSLATE = ["../cog_manager.py", "../core_commands.py", "../dev_commands.py"]


def regen_messages():
    subprocess.run(["pygettext", "-n"] + TO_TRANSLATE)


if __name__ == "__main__":
    regen_messages()
