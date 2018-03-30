#! /usr/bin/env python
import os, re, json, shutil
from ast import parse
from distutils.dir_util import copy_tree
from configparser import SafeConfigParser

MODNAME="ROGZIS"
VERSION="3.3"

def ZRead(BuildFolder, LumpName):
    # Includes
    IncludePattern=re.compile("#include\\s+\"(.+)\"", re.IGNORECASE)
    Lines=[]
    with open(BuildFolder+"/"+LumpName) as Input:
        for Line in Input:
            Include=IncludePattern.search(Line)
            if Include:
                print("  Including: "+Include.group(1))
                Lines.extend(ZRead(BuildFolder, Include.group(1)))
            else: Lines.append(Line)
    return "".join(Lines)

def ZReplace(BuildFolder, FullFile):
    # INI Loading
    IniFiles=[
        "ZCONFIG"
    ]
    print("Loading INI Settings")
    Config=SafeConfigParser()
    IniFiles=(BuildFolder+"\\/"+Ini+".ini" for Ini in IniFiles)
    InisFound=Config.read(IniFiles)
    for Ini in InisFound:
        print("  Loading:", Ini[len(BuildFolder)+2:])
    # INI Evaluation
    print("Evaluating INI Settings")
    for Section in Config:
        for Key, Value in Config.items(Section):
            if Key[0] in ["i", "d"]:
                Temp=eval(compile(parse(Value, mode="eval"), "<string>", "eval"))
                if Key[0] is "i":
                    Temp=int(Temp)
                Config[Section][Key]=str(Temp)
    # Config Injection
    print("Injecting INI Settings")
    ConfigPattern=re.compile("#config\\s+\"([^\"\r\n]+)\"\\s*(\\s|,)\\s*\"([^\"\r\n]+)\"", re.IGNORECASE)
    ConfigCall=ConfigPattern.search(FullFile)
    while ConfigCall:
        Section=ConfigCall.group(1)
        Option=ConfigCall.group(3)
        FullFile=re.sub("#config\\s+\"{}\"\\s*(\\s|,)\\s*\"{}\"".format(Section, Option), Config[Section][Option], FullFile)
        #FullFile=re.sub("#config\\s+\""+Section+"\"\\s*(\\s|,)\\s*\""+Option+"\"", Config[Section][Option], FullFile)
        ConfigCall=ConfigPattern.search(FullFile)
    # JSON Loading
    print("Loading JSON Data")
    for Section in Config:
        for Key, Value in Config.items(Section):
            if Key[0] is "j":
                JsonFile=Value+".json"
                print("  Loading:", JsonFile)
                with open(BuildFolder+"/"+JsonFile) as Input:
                    Value="".join(Input)
                    Config[Section][Key]=Value
    # ZScript Generation
    print("Generating ZScript")
    ## Upgrades
    print("  Generating Upgrades:")
    Upgrades=json.loads(Config["DATA"]["jUpgrades"])
    ### Marine Armor
    print("    Generating Marine Upgrades:")
    MAUpgrades=[]
    for MAUpgrade in Upgrades["MAUpgrades"]:
        ClassName="ZMAU_{}".format(MAUpgrade["Info"]["ID"])
        MAUpgrades.append(ClassName)
        print("      {}".format(ClassName))
        Zsc="""
            class ZMAU_{0[ID]}:ZArmorUpgrade{{
                const Order={0[Order]};
                const Strain={0[Strain]};
            """.format(MAUpgrade["Info"])
        VarSections=MAUpgrade["Variables"]
        if "Config" in VarSections:
            for Key, Value in VarSections["Config"].items():
                ConfigCall=Value.split(".")
                Zsc+="\tconst {}={};\n\t".format(Key, Config[ConfigCall[0]][ConfigCall[1]])
        if "General" in VarSections:
            for Variables in VarSections["General"]:
                Zsc+="\t{};\n\t".format(Variables)
        if "Default" in VarSections:
            Zsc+="\toverride ZUpgrade Init(){\n\t"
            for Key, Value in VarSections["Default"].items():
                Zsc+="\t    {}={};\n\t".format(Key, Value)
            Zsc+="\t    return super.Init();\n\t\t}\n"
        Zsc+="\t    }\n"
        FullFile=Zsc+FullFile
    print("    Inserting Marine Upgrades:")
    FullFile=FullFile.replace("@ZMAUpgrades", str(MAUpgrades).replace("'", "\"")[1:-1])
    print("Generating ZScript: Successful")
    return FullFile

def ZStript(FullFile):
    ## Multi-line
    FullFile=re.sub("(?s)\\/\\*.*?\\*\\/", " ", FullFile)
    ## Single-line
    FullFile=re.sub("\\/\\/+.*", " ", FullFile)

    # Other points of minimization
    Tokens={"{", "}", "\\(", "\\)", "\\[", "\\]", "=", ";"}
    for Token in Tokens:
        FullFile=re.sub("\\s*"+Token+"\\s*", Token.replace("\\", ""), FullFile)

    # Whitespace
    FullFile=re.sub("\\s+", " ", FullFile)
    return FullFile

def ZBuild(Compress):
    # Clean build destination
    print("Cleaning Build Destination: ", end="")
    BuildFolder="dist/"+MODNAME
    if os.path.exists(BuildFolder):
        shutil.rmtree(BuildFolder)

    # Make build destination and duplicate files
    os.makedirs(BuildFolder)
    copy_tree("src", BuildFolder)
    print("Successful")

    os.chdir("dist/")
    BuildFolder=MODNAME

    # Compact ZScript
    print("Compacting ZScript")
    StartLump="ZSCRIPT.zsc"
    FullFile=ZRead(BuildFolder, StartLump)
    FullFile=ZReplace(BuildFolder, FullFile)
    if Compress:
        FullFile=ZStript(FullFile)
    FullFile="version \"{}\"".format(VERSION)+FullFile
    os.remove("ROGZIS/ZSCRIPT.zsc")
    with open(BuildFolder+"/"+StartLump, "w+") as Output:
        Output.write(FullFile)
    shutil.rmtree(BuildFolder+"/ZSCRIPT")
    print("Compacting ZScript: Successful")

    # Compression
    if os.path.isfile(BuildFolder+"/"+MODNAME+".zip"):
        os.remove(BuildFolder+"/"+MODNAME+".zip")
    ArchiveName=MODNAME+".pk3"
    if os.path.isfile(ArchiveName):
        os.remove(ArchiveName)
    if Compress:
        print("Compressing PK3 Archive: ", end="")
        shutil.make_archive(MODNAME, "zip", BuildFolder)
        shutil.rmtree(BuildFolder)
        os.rename(MODNAME+".zip", ArchiveName)
        print("Successful")

if __name__ == "__main__":
    from sys import argv
    Compress=False
    while argv:
        if argv[0]=='-c':
            Compress=True
        argv=argv[1:]
    ZBuild(Compress)