import asyncio


def confirm(m=""):
    return input(m).lower().strip() in ("y", "yes")


def interactive_config(red, token_set, prefix_set):
    loop = asyncio.get_event_loop()
    token = ""

    print("Red - Discord Bot | Configuration process\n")

    if not token_set:
        print("Please enter a valid token:")
        while not token:
            token = input("> ")
            if not len(token) >= 50:
                print("That doesn't look like a valid token.")
                token = ""
            if token:
                loop.run_until_complete(red.db.set_global("token", token))

    if not prefix_set:
        prefix = ""
        print("\nPick a prefix. A prefix is what you type before a "
              "command. Example:\n"
              "!help\n^ The exclamation mark is the prefix in this case.\n"
              "Can be multiple characters. You will be able to change it "
              "later and add more of them.\nChoose your prefix:\n")
        while not prefix:
            prefix = input("Prefix> ")
            if len(prefix) > 10:
                print("Your prefix seems overly long. Are you sure it "
                      "is correct? (y/n)")
                if not confirm("> "):
                    prefix = ""
            if prefix:
                loop.run_until_complete(red.db.set_global("prefix", [prefix]))

    return token
