def bold(text):
    return "**"+str(text)+"**"

def italics(text):
    return "*"+str(text)+"*"

def strikethrough(text):
    return "~~"+str(text)+"~~"

def underline(text):
    return "__"+str(text)+"__"

def box(text):
    return "```"+str(text)+"```"

def inline(text):
    return "`"+str(text)+"`"

def escape_mass_mentions(text):
    words = {
        "@everyone": "@\u200beveryone",
        "@here": "@\u200bhere"
    }
    for k, v in words.items():
        text = text.replace(k, v)
    return text