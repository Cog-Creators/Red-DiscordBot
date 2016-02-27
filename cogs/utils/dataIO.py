import json

def fileIO(filename, IO, data=None):
    if IO == "save" and data != None:
        with open(filename, encoding='utf-8', mode="w") as f:
            f.write(json.dumps(data,indent=4,sort_keys=True,separators=(',',' : ')))
    elif IO == "load" and data == None:
        with open(filename, encoding='utf-8', mode="r") as f:
            return json.loads(f.read())
    elif IO == "check" and data == None:
        try:
            with open(filename, encoding='utf-8', mode="r") as f:
                return True
        except:
            return False
    else:
        raise("Invalid fileIO call")

def get_value(filename, key):
    with open(filename, encoding='utf-8', mode="r") as f:
        data = json.loads(f.read())
    return data[key]

def set_value(filename, key, value):
    data = fileIO(filename, "load")
    data[key] = value
    fileIO(filename, "save", data)
    return True