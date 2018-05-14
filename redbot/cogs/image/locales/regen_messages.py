import subprocess

TO_TRANSLATE = ["../image.py"]


def regen_messages():
    subprocess.run(["pygettext", "-n"] + TO_TRANSLATE)


if __name__ == "__main__":
    regen_messages()
