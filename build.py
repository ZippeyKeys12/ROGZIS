#! /usr/bin/env python
import os, re, shutil
from distutils.dir_util import copy_tree

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
    return Lines

def ZStript(BuildFolder, StartLump):
    # Comments
    Lines=ZRead(BuildFolder, StartLump)
    FullFile="\n".join(Lines)
    ## Multi-line
    FullFile=re.sub("(?s)\\/\\*.*?\\*\\/", " ", FullFile)
    ## Single-line
    FullFile=re.sub("\\/\\/.*", " ", FullFile)

    # Other points of minimization
    Tokens={"{", "}", "\\(", "\\)", "\\[", "\\]", "=", ";"}
    for Token in Tokens:
        FullFile=re.sub("\\s*"+Token+"\\s*", Token.replace("\\", ""), FullFile)

    # Whitespace
    FullFile=re.sub("\\s+", " ", FullFile)
    return FullFile

def ZBuild(ModName, Compress):
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
    print("Compacting ZScript:")
    StartLump="ZSCRIPT.zsc"
    FullFile=ZStript(BuildFolder, StartLump)
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
    ZBuild("ROGZIS", Compress)