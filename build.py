#! /usr/bin/env python
import os
import re
import json
import shutil
import sqlite3
from ast import parse
from distutils.dir_util import copy_tree
from configparser import SafeConfigParser

SETTINGS = {
    "ModName": "ROGZIS",
    "Version": "3.3",
    "IniFiles": [
        "ZCONFIG"
    ]
}


def ZRead(BuildFolder, LumpName):
    # Includes
    IncludePattern = re.compile("#include\\s+\"(.+)\"", re.IGNORECASE)
    Lines = []
    with open(BuildFolder+"/"+LumpName) as Input:
        for Line in Input:
            Include = IncludePattern.search(Line)
            if Include:
                print("  Including: "+Include.group(1))
                Lines.extend(ZRead(BuildFolder, Include.group(1))+"\n")
            else:
                Lines.append(Line)
    return "".join(Lines)


def ZReplace(BuildFolder, FullFile, IniFiles):
    # INI Loading
    print("Loading INI Settings")
    Config = SafeConfigParser()
    IniFiles = (BuildFolder+"/"+Ini+".ini" for Ini in IniFiles)
    InisFound = Config.read(IniFiles)
    for Ini in InisFound:
        print("  ", Ini[len(BuildFolder)+2:])

    # Database Loading
    Database = sqlite3.connect(BuildFolder+"/"+"GAMEDATA.sqlite").cursor()

    # JSON Loading
    print("Loading JSON Data")
    for Section in Config:
        for Key, Value in Config.items(Section):
            if Key[0] is "j":
                JsonFile = Value+".json"
                print("  ", JsonFile)
                with open(BuildFolder+"/"+JsonFile) as Input:
                    Value = "".join(Input)
                    Config[Section][Key] = Value

    # Dynamic Config
    print("Generating Dynamic Config")
    JsonFile = json.loads(Config["AI.EMOTION"]["jEmotions"])
    Config["AI.EMOTION"]["iPersDimensions"] = str(
        len(JsonFile["Personality"].items()))
    Config["AI.EMOTION"]["iPersFacets"] = str(
        len(list(JsonFile["Personality"].items())[0]))

    # INI Evaluation
    print("Evaluating INI Settings")
    for Section in Config:
        for Key, Value in Config.items(Section):
            if Key[0] in ["i", "d"]:
                Temp = eval(
                    compile(parse(Value, mode="eval"), "<string>", "eval"))
                if Key[0] is "i":
                    Temp = int(Temp)
                Config[Section][Key] = str(Temp)

    # Config Blocks
    print("Expanding Config Blocks")
    Pattern = re.compile("\\[Config\\](\\s*){([^{}]*)}", re.IGNORECASE)
    Call = Pattern.search(FullFile)
    while Call:
        Sections = Call.group(2).split(",")
        Replacement = ""
        for Section in Sections:
            Components = re.sub("\s+", " ", Section).split(":")
            Replacement += "const {0}=#config {1[0]}\", \"{1[1]};".format(
                Components[0].strip("\s*").replace("\"", ""), Components[1].split("."))
        FullFile = re.sub(
            "\\[Config\\](\\s*){{({})}}".format(Call.group(2)), Replacement, FullFile)
        Call = Pattern.search(FullFile)

    # Config Injection
    print("Injecting INI Settings")
    Pattern = re.compile(
        "#config\\s+\"([^\"\r\n]+)\"\\s*(\\s|,)\\s*\"([^\"\r\n]+)\"", re.IGNORECASE)
    Call = Pattern.search(FullFile)
    while Call:
        Section = Call.group(1)
        Option = Call.group(3)
        FullFile = re.sub("#config\\s+\"{}\"\\s*(\\s|,)\\s*\"{}\"".format(
            Section, Option), Config[Section][Option], FullFile, flags=re.IGNORECASE)
        Call = Pattern.search(FullFile)

    # ZScript Generation
    print("Generating ZScript")

    ## Defaults
    print("  Defaults:", end=" ")
    Pattern = re.compile("\\[Property\\](\\s*){([^{}]*)}", re.IGNORECASE)
    Call = Pattern.search(FullFile)
    while Call:
        Call = re.sub("\\s+", " ", Call.group(2))
        Sections = Call.split("[")
        Call = "Default{"
        for Section in Sections:
            if len(Section) < 2:
                continue
            Section = Section.split("]")
            SectionName = Section[0]
            for Default in Section[1].split(";"):
                if SectionName[:5] == "Flags":
                    Default = Default.split("=")
                    if len(Default) < 2:
                        continue
                    Call += "+" if Default[1] == "true" else "-"
                    if SectionName.find(".") > -1:
                        Call += SectionName.split(".")[1]+"."
                    Call += Default[0]+";"
                else:
                    if SectionName == "Type":
                        Call += Default+";"
                    else:
                        Default = Default.split("=")
                        if len(Default) < 2:
                            continue
                        if SectionName == "Info":
                            Call += "//$"+Default[0]+" "+Default[1]+"\n"
                        else:
                            if not SectionName == "Default":
                                Call += SectionName+"."
                            Call += Default[0]+" " + \
                                re.sub("[()]", "", Default[1])+";"
        FullFile = Pattern.sub(Call+"}", FullFile, 1)
        Call = Pattern.search(FullFile)
    print("Successful")

    ## Upgrades
    print("  Upgrades:")

    ### Marine Armor
    print("    Marine:")
    MAUpgrades = []
    for MAUpgrade in Database.execute("SELECT * FROM MarineArmorUpgrades"):
        ClassName = "ZMAU_{}".format(MAUpgrade[0])
        MAUpgrades.append(ClassName)
        print("      {}".format(ClassName))
        if MAUpgrade[2] == None:
            MAUpgrade[2] = 0
        Zsc = """
            class ZMAU_{0[0]}:ZArmorUpgrade{{
                const Priority={0[1]};
                const Strain={0[2]};
            }}
        """.format(MAUpgrade)
        FullFile = Zsc+FullFile
    print("    Inserting Marine Upgrades:", end=" ")
    FullFile = FullFile.replace("$ZMAUpgrades", str(MAUpgrades)[1:-1])
    print("Successful")

    ## AI
    print("  AI:")

    ### Emotion
    print("    Emotion:")
    JsonFile = json.loads(Config["AI.EMOTION"]["JEmotions"])

    ### Personality
    print("      Personality:")
    Zsc = """
        class ZPersonality{{
            const DIMENSIONS={0[iPersDimensions]};
            const FACETCOUNT={0[iPersFacets]};
    """.format(Config["AI.EMOTION"])
    print("        Dimensions:")
    Zsc += "private double"
    for Dimension in JsonFile["Personality"]:
        print("          {}".format(Dimension))
        Zsc += " {},".format(Dimension)
    Zsc = Zsc[:-1]+";"
    Zsc += ("double,"*len(JsonFile["Personality"]))[:-1]+" Summary(){return"
    for Dimension in JsonFile["Personality"]:
        Zsc += " {},".format(Dimension)
    Zsc = Zsc[:-1]+";}void Update(){"
    for Index, Dimension in zip(range(len(JsonFile["Personality"])), JsonFile["Personality"]):
        Zsc += "{}=Facets.Row({}).AAMean();".format(Dimension, Index)
    print("        Facets:")
    Zsc += "}double Facet(Name Facet){switch(Facet){"
    for Row, Dimension in zip(range(len(JsonFile["Personality"])), JsonFile["Personality"]):
        print("          {}:".format(Dimension))
        for Column, Facet in zip(range(len(JsonFile["Personality"][Dimension])), JsonFile["Personality"][Dimension]):
            print("            {}".format(Facet))
            Zsc += "case '{}': return Facets.Get({}, {});".format(
                Facet, Row, Column)
    FullFile = Zsc+"}return double.NaN;}}"+FullFile

    ### Mood
    print("      Mood:")
    Zsc = """
        class ZMood:ZFSM{{
            const DIMENSIONS={0[iPersDimensions]};
            const FACETCOUNT={0[iPersFacets]};
    """.format(Config["AI.EMOTION"])

    ## Generics
    print("  Generics:")

    ### Dictionary
    print("    ZDictionary")
    Template = open(BuildFolder+"/ZSCRIPT/TEMPLATE/DICTIONARY.zsc")
    Pattern = re.compile("ZDictionary\\s*<\\s*(\\w+)\\s*>")
    Call = Pattern.search(FullFile)
    while Call:
        print("      "+Call.group(1))
        FullFile += re.sub("@Type", Call.group(1),
                           Template.read(), flags=re.IGNORECASE)
        FullFile = re.sub("ZDictionary\\s*<\\s*"+Call.group(1)+"\\s*>",
                          "ZDictionary_"+Call.group(1), FullFile, flags=re.IGNORECASE)
        Call = Pattern.search(FullFile)

    # End
    print("Generating ZScript: Successful")
    return FullFile


def ZComment(FullFile):
    # Multi-line
    FullFile = re.sub("(?s)\\/\\*.*?\\*\\/", " ",
                      FullFile, flags=re.IGNORECASE)
    # Single-line
    FullFile = re.sub("\\/\\/+.*", " ", FullFile, flags=re.IGNORECASE)
    return FullFile


def ZStript(FullFile):
    FullFile = ZComment(FullFile)
    # Other points of minimization
    Tokens = {"{", "}", "\\(", "\\)", "\\[", "\\]", "=", ";"}
    for Token in Tokens:
        FullFile = re.sub(
            "\\s*"+Token+"\\s*", Token.replace("\\", ""), FullFile, flags=re.IGNORECASE)

    # Whitespace
    FullFile = re.sub("\\s+", " ", FullFile, flags=re.IGNORECASE)
    return FullFile


def ZBuild(Settings, Compress):
    # Build Settings
    ModName = Settings["ModName"]
    # Clean build destination
    print("Cleaning Build Destination: ", end="")
    BuildFolder = "dist/"+ModName
    if os.path.exists(BuildFolder):
        shutil.rmtree(BuildFolder)

    # Make build destination and duplicate files
    os.makedirs(BuildFolder)
    copy_tree("src", BuildFolder)
    print("Successful")

    os.chdir("dist/")
    BuildFolder = ModName

    # Compact ZScript
    print("Compacting ZScript")
    StartLump = "ZSCRIPT.zsc"
    FullFile = ZRead(BuildFolder, StartLump)
    FullFile = ZComment(FullFile)
    FullFile = ZReplace(BuildFolder, FullFile, Settings["IniFiles"].copy())
    if Compress:
        FullFile = ZStript(FullFile)
    FullFile = "version \"{}\"".format(Settings["Version"])+FullFile
    os.remove("ROGZIS/ZSCRIPT.zsc")
    with open(BuildFolder+"/"+StartLump, "w+") as Output:
        Output.write(FullFile)
    shutil.rmtree(BuildFolder+"/ZSCRIPT")
    print("Compacting ZScript: Successful")

    # Compression
    if os.path.isfile(BuildFolder+"/"+ModName+".zip"):
        os.remove(BuildFolder+"/"+ModName+".zip")
    ArchiveName = ModName+".pk3"
    if os.path.isfile(ArchiveName):
        os.remove(ArchiveName)
    if Compress:
        print("Compressing PK3 Archive: ", end="")
        shutil.make_archive(ModName, "zip", BuildFolder)
        shutil.rmtree(BuildFolder)
        os.rename(ModName+".zip", ArchiveName)
        print("Successful")


if __name__ == "__main__":
    from sys import argv
    Compress = False
    while argv:
        if argv[0] == '-c':
            Compress = True
        argv = argv[1:]
    ZBuild(SETTINGS, Compress)
