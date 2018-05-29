#! /usr/bin/env python
import os, re, json, shutil
from ast import parse
from distutils.dir_util import copy_tree
from configparser import SafeConfigParser

SETTINGS={
    "ModName":"ROGZIS",
    "Version":"3.3",
    "IniFiles":[
        "ZCONFIG"
    ]
}

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

def ZReplace(BuildFolder, FullFile, IniFiles):
    # INI Loading
    print("Loading INI Settings")
    Config=SafeConfigParser()
    IniFiles=(BuildFolder+"\\/"+Ini+".ini" for Ini in IniFiles)
    InisFound=Config.read(IniFiles)
    for Ini in InisFound:
        print("  ", Ini[len(BuildFolder)+2:])
    # JSON Loading
    print("Loading JSON Data")
    for Section in Config:
        for Key, Value in Config.items(Section):
            if Key[0] is "j":
                JsonFile=Value+".json"
                print("  ", JsonFile)
                with open(BuildFolder+"/"+JsonFile) as Input:
                    Value="".join(Input)
                    Config[Section][Key]=Value
    # Dynamic Config
    print("Generating Dynamic Config")
    JsonFile=json.loads(Config["AI.EMOTION"]["jEmotions"])
    Config["AI.EMOTION"]["iPersDimensions"]=str(len(JsonFile["Personality"].items()))
    Config["AI.EMOTION"]["iPersFacets"]=str(len(list(JsonFile["Personality"].items())[0]))
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
        FullFile=re.sub("#config\\s+\"{}\"\\s*(\\s|,)\\s*\"{}\"".format(Section, Option), Config[Section][Option], FullFile, flags=re.IGNORECASE)
        ConfigCall=ConfigPattern.search(FullFile)
    # ZScript Generation
    print("Generating ZScript")
    ## Defaults
    print("  Defaults:", end=" ")
    DefaultPattern=re.compile("\\[Property\\](\\s*){([^{}]*)}", re.IGNORECASE)
    DefaultCall=DefaultPattern.search(FullFile)
    while DefaultCall:
        DefaultCall=DefaultCall.group(2)
        DefaultCall=re.sub("\\s+", " ", DefaultCall)
        Sections=DefaultCall.split("[")
        DefaultCall="Default{"
        for Section in Sections:
            if len(Section)<2:
                continue
            Section=Section.split("]")
            SectionName=Section[0]
            for Default in Section[1].split(";"):
                if SectionName[:5]=="Flags":
                    Default=Default.split("=")
                    if len(Default)<2:
                        continue
                    DefaultCall+="+" if Default[1]=="true" else "-"
                    if SectionName.find(".")>-1:
                        DefaultCall+=SectionName.split(".")[1]+"."
                    DefaultCall+=Default[0]+";"
                else:
                    if SectionName=="Type":
                        DefaultCall+=Default+";"
                    else:
                        Default=Default.split("=")
                        if len(Default)<2:
                            continue
                        if SectionName=="Info":
                            DefaultCall+="// $"+Default[0]+" "+Default[1]+"\n"
                        else:
                            if not SectionName=="Default":
                                DefaultCall+=SectionName+"."
                            DefaultCall+=Default[0]+" "+re.sub("[()]", "", Default[1])+";"
        FullFile=DefaultPattern.sub(DefaultCall+"}", FullFile, 1)
        DefaultCall=DefaultPattern.search(FullFile)
    print("Successful")
    ## Upgrades
    print("  Upgrades:")
    JsonFile=json.loads(Config["DATA"]["jUpgrades"])
    ### Marine Armor
    print("    Marine:")
    MAUpgrades=[]
    for MAUpgrade in JsonFile["MAUpgrades"]:
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
                Zsc+="const {}={};".format(Key, Config[ConfigCall[0]][ConfigCall[1]])
        if "General" in VarSections:
            for Variables in VarSections["General"]:
                Zsc+="{};".format(Variables)
        if "Default" in VarSections:
            Zsc+="override ZUpgrade Init(){"
            for Key, Value in VarSections["Default"].items():
                if Value is None:
                    Value="null"
                Zsc+="{}={};".format(Key, Value)
            Zsc+="return super.Init();}"
        FullFile=Zsc+"}"+FullFile
    print("    Inserting Marine Upgrades:", end=" ")
    FullFile=FullFile.replace("@ZMAUpgrades", str(MAUpgrades).replace("'", "\"")[1:-1])
    print("Successful")
    ## AI
    print("  AI:")
    ### Emotion
    print("    Emotion:")
    #### Personality
    print("      Personality:")
    JsonFile=json.loads(Config["AI.EMOTION"]["JEmotions"])
    Zsc="""
        class ZPersonality{{
            const DIMENSIONS={0[iPersDimensions]};
            const FACETCOUNT={0[iPersFacets]};
    """.format(Config["AI.EMOTION"])
    print("        Dimensions:")
    for Dimension in JsonFile["Personality"]:
        print("          {}".format(Dimension))
        Zsc+="private double {};".format(Dimension)
    for Dimension in range(len(JsonFile["Personality"].items())-1):
        Zsc+="double,"
    Zsc+="double Summary(){return "
    for Dimension in JsonFile["Personality"]:
        Zsc+="{},".format(Dimension)
    Zsc="{};}}void Update(){{".format(Zsc[:-1])
    for Index, Dimension in zip(range(len(JsonFile["Personality"])), JsonFile["Personality"]):
        Zsc+="{}=__Facets__.RowSum({})/FACETCOUNT;".format(Dimension, Index)
    print("        Facets:")
    Zsc+="}double Facet(Name Facet){switch(Facet){"
    for Row, Dimension in zip(range(len(JsonFile["Personality"])), JsonFile["Personality"]):
        print("          {}:".format(Dimension))
        for Column, Facet in zip(range(len(JsonFile["Personality"][Dimension])), JsonFile["Personality"][Dimension]):
            print("            {}".format(Facet))
            Zsc+="case '{}': return __Facets__.Get({}, {});".format(Facet, Row, Column)
    FullFile=Zsc+"}return double.NaN;}}"+FullFile
    print("Generating ZScript: Successful")
    return FullFile

def ZComment(FullFile):
    ## Multi-line
    FullFile=re.sub("(?s)\\/\\*.*?\\*\\/", " ", FullFile, flags=re.IGNORECASE)
    ## Single-line
    FullFile=re.sub("\\/\\/+.*", " ", FullFile, flags=re.IGNORECASE)
    return FullFile

def ZStript(FullFile):
    FullFile=ZComment(FullFile)
    # Other points of minimization
    Tokens={"{", "}", "\\(", "\\)", "\\[", "\\]", "=", ";"}
    for Token in Tokens:
        FullFile=re.sub("\\s*"+Token+"\\s*", Token.replace("\\", ""), FullFile, flags=re.IGNORECASE)

    # Whitespace
    FullFile=re.sub("\\s+", " ", FullFile, flags=re.IGNORECASE)
    return FullFile

def ZBuild(Settings, Compress):
    # Build Settings
    ModName=Settings["ModName"]
    # Clean build destination
    print("Cleaning Build Destination: ", end="")
    BuildFolder="dist/"+ModName
    if os.path.exists(BuildFolder):
        shutil.rmtree(BuildFolder)

    # Make build destination and duplicate files
    os.makedirs(BuildFolder)
    copy_tree("src", BuildFolder)
    print("Successful")

    os.chdir("dist/")
    BuildFolder=ModName

    # Compact ZScript
    print("Compacting ZScript")
    StartLump="ZSCRIPT.zsc"
    FullFile=ZRead(BuildFolder, StartLump)
    FullFile=ZComment(FullFile)
    FullFile=ZReplace(BuildFolder, FullFile, Settings["IniFiles"].copy())
    if Compress:
        FullFile=ZStript(FullFile)
    FullFile="version \"{}\"".format(Settings["Version"])+FullFile
    os.remove("ROGZIS/ZSCRIPT.zsc")
    with open(BuildFolder+"/"+StartLump, "w+") as Output:
        Output.write(FullFile)
    shutil.rmtree(BuildFolder+"/ZSCRIPT")
    print("Compacting ZScript: Successful")

    # Compression
    if os.path.isfile(BuildFolder+"/"+ModName+".zip"):
        os.remove(BuildFolder+"/"+ModName+".zip")
    ArchiveName=ModName+".pk3"
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
    Compress=False
    while argv:
        if argv[0]=='-c':
            Compress=True
        argv=argv[1:]
    ZBuild(SETTINGS, Compress)