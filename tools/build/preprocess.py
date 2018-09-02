import re

from strip import ZStript

ConfigPattern = re.compile('"(.+)"\\s*(\\s|,)\\s*"(.+)"')


def ZPreprocess(FullFile, Data):
    FullFile = ZPConfigBlocks(FullFile)
    Defines = {}
    Macros = {
        "include": ZPInclude,
        "config": ZPConfig,
        "define": ZPDefine,
        "undef": ZPUndef,
        "if": ZPIf,
        "ifn": ZPIfN,
    }
    Pattern = re.compile("#(\\w+)(\\s+(.*))?")
    Call = Pattern.search(FullFile)
    while Call:
        if (
            Call.group(1) == "endif"
            or Call.group(1) == "region"
            or Call.group(1) == "endregion"
        ):
            FullFile = re.sub(Call.group(0), "", FullFile)
        Result = Macros[Call.group(1)](FullFile, Call.group(3), Data, Defines)
        if Result:
            FullFile = re.sub(
                "#" + Call.group(1) + "\\s+" + Result[0], Result[1] + "\n", FullFile
            )
        else:
            FullFile = re.sub(Call.group(0), "", FullFile)
        Call = Pattern.search(FullFile)
    # End
    return FullFile


def ZPConfigBlocks(FullFile):
    # Config Blocks
    Pattern = re.compile("\\[Config\\](\\s*){([^}]*)}", re.DOTALL)
    Call = Pattern.search(FullFile)
    while Call:
        Sections = Call.group(2).split(",")
        Replacement = ""
        for Section in Sections:
            Components = re.sub("\\s+", " ", Section).split(":")
            Replacement += "const {}=#config {};\n".format(
                Components[0].replace('"', ""), Components[1].replace(".", '","')
            )
        FullFile = re.sub(
            "\\[Config\\](\\s*){" + Call.group(2) + "}", Replacement, FullFile
        )
        Call = Pattern.search(FullFile)
    return FullFile


IncludePattern = re.compile('"(.+)"\\s*')


def ZPInclude(FullFile, Args, Data, Defines):
    return (
        Args,
        ZPConfigBlocks(
            ZStript(open(IncludePattern.match(Args.strip()).group(1)).read())
        ),
    )


def ZPConfig(FullFile, Args, Data, Defines):
    Call = ConfigPattern.match(Args.strip())
    return (Call.group(0), Data["CONFIG"][Call.group(1)][Call.group(3)])


def ZPDefine(FullFile, Args, Data, Defines):
    Defines[Args] = True


def ZPUndef(FullFile, Args, Data, Defines):
    if Args in Defines:
        del Defines[Args]


def ZPIf(FullFile, Args, Data, Defines):
    if Args not in Defines:
        FullFile = re.sub("#if\\s+" + Args, "", FullFile)


def ZPIfN(FullFile, Args, Data, Defines):
    return
