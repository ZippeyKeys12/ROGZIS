#! /usr/bin/env python
import os, re, shutil
from distutils.dir_util import copy_tree

def ZRead(BuildFolder, LumpName):
    # Replacements
    IncludePattern=re.compile("#include\\s+\"(\\S.+\\S)\"")
    Lines=[]
    with open(BuildFolder+"/"+LumpName) as Input:
        for Line in Input:
            Include=IncludePattern.match(Line)
            if Include:
                print("  Including: "+Include.group(1))
                Lines.extend(ZRead(BuildFolder, Include.group(1)))
            else: Lines.append(Line)
    os.remove(BuildFolder+"/"+LumpName)
    return Lines

def Build(ModName):
    # Clean build destination
    print("Cleaning Build Destination: ", end="")
    BuildFolder="dist/"+ModName
    if os.path.exists(BuildFolder): shutil.rmtree(BuildFolder)

    # Make build destination and duplicate files
    os.makedirs(BuildFolder)
    copy_tree("src", BuildFolder)
    print("Successful")

    os.chdir("dist/")
    BuildFolder=ModName

    #Compact
    print("Compacting ZScript:")
    StartLump="ZSCRIPT.zsc"
    Tokens={"{", "}", "\(", "\)", "\[", "\]", "=", ";"}
    Lines=ZRead(BuildFolder, StartLump)
    OneLiner=""
    with open(BuildFolder+"/"+StartLump, "w+") as Output:
        for Line in Lines:
            Line=re.sub("\/\/.*", " ", Line)
            OneLiner+=Line+" "
        OneLiner=re.sub("\/\\*(\\S|\\s)*\\*\/", " ", OneLiner)
        for Token in Tokens: OneLiner=re.sub("\\s*"+Token+"\\s*", Token.replace("\\", ""), OneLiner)
        Output.write(re.sub("(\\s)+", " ", OneLiner))
    shutil.rmtree(BuildFolder+"/ZSCRIPT")
    print("Compacting ZScript: Successful")
    
    #Compression
    print("Compressing PK3 Archive: ", end="")
    if os.path.isfile(BuildFolder+"/ .zip"): os.remove(BuildFolder+"/ .zip")
    shutil.make_archive("z", "zip", BuildFolder)
    shutil.rmtree(BuildFolder)
    ArchiveName=ModName+".pk3"
    os.remove(ArchiveName)
    os.rename("z.zip", ArchiveName)
    print("Successful")

if __name__ == "__main__":
    Build("ROGZIS")