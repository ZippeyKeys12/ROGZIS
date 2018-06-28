import re


def ZGenerate(FullFile, Data):
    # ZScript Generation
    print("Generating ZScript")

    # Defaults
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

    # Upgrades
    print("  Upgrades:")

    # Marine Armor
    print("    Marine:")
    MAUpgrades = []
    for MAUpgrade in Data["DATABASE"].execute("SELECT * FROM MarineArmorUpgrades"):
        ClassName = "ZMAU_{}".format(MAUpgrade[0])
        MAUpgrades.append(ClassName)
        print("      {}".format(ClassName))
        if MAUpgrade[2] == None:
            MAUpgrade[2] = 0
        Zsc = """
            class ZMAU_{0[0]}:ZArmorUpgrade{{
                override
                ZUpgrade Init(){{
                    Priority={0[1]};
                    Strain={0[2]};
                    return super.Init();
                }}
            }}
        """.format(MAUpgrade)
        FullFile = Zsc+FullFile
    print("    Inserting Marine Upgrades:", end=" ")
    FullFile = FullFile.replace("$ZMAUpgrades", str(MAUpgrades)[1:-1])
    print("Successful")

    # AI
    print("  AI:")

    # Emotion
    print("    Emotion:")

    # Personality
    print("      Personality:")
    Personality = list(Data["DATABASE"].execute(
        "SELECT * FROM FiveFactorPersonality"))
    Info = {
        "Dims": len(Personality),
        "RDims": range(len(Personality)),
        "Facets": len(Personality[0])-1
    }
    Zsc = """
        class ZPersonality{{
            const DIMENSIONS={};
            const FACETS={};
            ZMatrix __Facets__;
    """.format(Info["Dims"], Info["Facets"])
    print("        Dimensions:")
    Zsc += "private double"
    for Dimension in Personality:
        print("          {}".format(Dimension[0]))
        Zsc += " {},".format(Dimension[0])
    Zsc = Zsc[:-1]+";"+("double,"*Info["Dims"])[:-1]+" Summary(){return"
    for Dimension in Personality:
        Zsc += " {},".format(Dimension[0])
    Zsc = Zsc[:-1]+";}void Update(){"
    for Dimension in zip(Info["RDims"], Personality):
        Zsc += "{0[1][0]}=__Facets__.Row({0[0]}).AAMean();".format(Dimension)
    print("        Facets:")
    Zsc += "}double Facet(Name Facet){switch(Facet){"
    for Row, Dimension in zip(Info["RDims"], Personality):
        print("          {}:".format(Dimension[0]))
        for Column, Facet in zip(range(Info["Facets"]), Personality[Row][1:]):
            print("            {}".format(Facet))
            Zsc += "case '{}': return __Facets__.Get({}, {});".format(
                Facet, Row, Column)
    FullFile = Zsc+"}return double.NaN;}}"+FullFile

    # Mood
    print("      Mood:")

    # Templates
    # TODO: C-style preprocessing
    print("  Generics:")

    # Dictionary
    print("    ZDictionary")
    Template = open("ZSCRIPT/TEMPLATE/DICTIONARY.zsc").read()
    Pattern = re.compile("Map\\s*<\\s*(\\w+)\\s*,\\s*(\\w+)\\s*>")
    Call = Pattern.search(FullFile)
    while Call:
        print("      "+Call.group(1))
        FullFile += Template.replace("@KeyType", Call.group(1)
                                     ).replace("@ValType", Call.group(2))
        FullFile = re.sub("Map\\s*<\\s*"+Call.group(1)+"\\s*,\\s*"+Call.group(2)+"\\s*>",
                          "ZDictionary_"+Call.group(1)+"_"+Call.group(2), FullFile, flags=re.IGNORECASE)
        Call = Pattern.search(FullFile)

    # End
    return FullFile
