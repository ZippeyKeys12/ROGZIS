import re
import sqlite3
from ast import parse
from configparser import SafeConfigParser


def ZData(FullFile, IniFiles):
    # INI Loading
    print("Loading INI Settings")
    Config = SafeConfigParser()
    IniFiles = (Ini + ".ini" for Ini in IniFiles)
    InisFound = Config.read(IniFiles)
    for Ini in InisFound:
        print("  ", Ini)

    # Database Loading
    Database = sqlite3.connect("GAMEDATA.sqlite").cursor()

    # JSON Loading
    print("Loading JSON Data")
    for Section in Config:
        for Key, Value in Config.items(Section):
            if Key[0] == "j":
                JsonFile = Value + ".json"
                print("  ", JsonFile)
                with open(JsonFile) as Input:
                    Value = "".join(Input)
                    Config[Section][Key] = Value

    # INI Evaluation
    print("Evaluating INI Settings")
    for Section in Config:
        for Key, Value in Config.items(Section):
            if Key[0] in ["i", "d"]:
                Temp = eval(compile(parse(Value, mode="eval"), "<string>", "eval"))
                if Key[0] == "i":
                    Temp = int(Temp)
                Config[Section][Key] = str(Temp)

    # End
    return {"CONFIG": Config, "DATABASE": Database}
