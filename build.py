from glyphsLib.cli import main
from fontTools.ttLib import newTable, TTFont
import shutil
import subprocess
import multiprocessing
import multiprocessing.pool
from pathlib import Path
import glob
import argparse
import ufo2ft
import ufoLib2
import os

def fontExport(name: str, sources:Path, path:Path):
    for file in list(path.glob("*.ufo")):

        fontName = str(file).split("/")[2].split('.')[0]

        print ("["+fontName+"] Processing")
        exportfont = ufoLib2.Font.open(file)
        variant = "Regular"
        if "Medium" in str(file):
            variant = "Medium"
        elif "ExtraBold" in str(file):
            variant = "ExtraBold"
        elif "Bold" in str(file):
            variant = "Bold"

        if name == "tokumin" and variant == "Regular": # To align with Google's standards we must shift the Medium to be a Regular, so have to make sure the right Kanji are added. 
            sharedFont = ufoLib2.Font.open(sources / "ufo_shared" / str("Kaisei-shared-Medium.ufo"))
        else:
            sharedFont = ufoLib2.Font.open(sources / "ufo_shared" / str("Kaisei-shared-"+variant+".ufo"))

        print ("["+fontName+"] Importing shared glyphs")
        for glyph in sharedFont.glyphOrder:
            exportfont.addGlyph(sharedFont[glyph])

        print ("["+fontName+"] Adding feature code") 
        featureSet = sources / "features.fea"
        exportfont.features.text = featureSet.read_text()

        print ("["+fontName+"] Compiling")
        static_ttf = ufo2ft.compileTTF(exportfont)

        if name == "haruno":
            static_ttf["name"].addMultilingualName({'ja':'解星-春の海'}, static_ttf, nameID = 1, windows=True, mac=False)
        elif name == "tokumin":
            static_ttf["name"].addMultilingualName({'ja':'解星-特ミン'}, static_ttf, nameID = 1, windows=True, mac=False)
        elif name == "opti":
            static_ttf["name"].addMultilingualName({'ja':'解星-オプティ'}, static_ttf, nameID = 1, windows=True, mac=False)
        elif name == "decol":
            static_ttf["name"].addMultilingualName({'ja':'解星-デコール'}, static_ttf, nameID = 1, windows=True, mac=False)

        if "Medium" in str(file):
            static_ttf["OS/2"].usWeightClass = 500
        elif "ExtraBold" in str(file):
            static_ttf["OS/2"].usWeightClass = 800
        elif "Bold" in str(file):
            static_ttf["OS/2"].usWeightClass = 700

        print ("["+fontName+"] Adding stub DSIG")
        static_ttf["DSIG"] = newTable("DSIG")     #need that stub dsig
        static_ttf["DSIG"].ulVersion = 1
        static_ttf["DSIG"].usFlag = 0
        static_ttf["DSIG"].usNumSigs = 0
        static_ttf["DSIG"].signatureRecords = []
        static_ttf["head"].flags |= 1 << 3        #sets flag to always round PPEM to integer

        print ("["+fontName+"] Merging BASE")
        static_ttf["BASE"] = newTable("BASE")
        base = TTFont()
        if variant == "Medium" or variant == "Regular":
            base.importXML(sources / "BASE_regular.ttx")
        else:
            base.importXML(sources / str("BASE_"+variant.lower()+".ttx"))

        static_ttf["BASE"] = base["BASE"]

        print ("["+fontName+"] Saving")

        os.makedirs("fonts/ttf/"+name, exist_ok=True)

        outputName = "fonts/ttf/"+name+"/Kaisei"+name.capitalize()+"-"+variant+".ttf"
        if name == "haruno":
            outputName = "fonts/ttf/"+name+"/KaiseiHarunoUmi-"+variant+".ttf"

        static_ttf.save(outputName)

    shutil.rmtree(str(path))

def execute(name:str, sources:Path):
    print ("Generating "+name+" UFO")
    outputPath = sources / str("ufo_"+name)
    os.makedirs(outputPath, exist_ok=True)
    glyphsName = "Kaisei-"+name.capitalize()+".glyphs"
    if name == "haruno":
        glyphsName = "Kaisei-HarunoUmi.glyphs"
    main(("glyphs2ufo", str(sources / glyphsName), "-m", str(outputPath)))
    fontExport(name, sources, outputPath)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="build FontKai fonts")
    parser.add_argument("-D", "--decol", action="store_true", dest="decol", help="Export the Decol font")
    parser.add_argument("-H", "--haruno", action="store_true", dest="haruno", help="Export the HarunoUmi font")
    parser.add_argument("-O", "--opti", action="store_true", dest="opti", help="Export the Opti font")
    parser.add_argument("-T", "--tokumin", action="store_true", dest="tokumin", help="Export the Tokumin font")
    parser.add_argument("-A", "--all", action="store_true", dest="all", help="Export all fonts")
    parser.add_argument("-S", "--shared", action="store_true", dest="shared", help="Regenerate the shared source")

    args = parser.parse_args()
    sources = Path("sources")

    if args.all:
        args.decol = True
        args.haruno = True
        args.opti = True
        args.tokumin = True

    if args.decol or args.haruno or args.opti or args.tokumin:
        os.makedirs("sources/ufo_shared", exist_ok=True)
        if args.shared:
            print ("Generating shared UFO")
            if os.path.isfile(sources / "Kaisei-Shared.glyphs"):
                main(("glyphs2ufo", str(sources / "Kaisei-Shared.glyphs"), "-m", str(sources / "ufo_shared")))
            else:
                print ("Cannot locate the 'shared' Glyphs file. Please confirm the file is unzipped.")

        pool = multiprocessing.pool.Pool(processes=multiprocessing.cpu_count())
        processes = []

        if args.decol:
            processes.append(
                pool.apply_async(
                    execute,
                    ("decol", sources)
                )
            )
        
        if args.haruno:
            processes.append(
                pool.apply_async(
                    execute,
                    ("haruno",sources)
                )
            )
        
        if args.opti:
            processes.append(
                pool.apply_async(
                    execute,
                    ("opti",sources)
                )
            )
        
        if args.tokumin:
            processes.append(
                pool.apply_async(
                    execute,
                    ("tokumin",sources)
                )
            )
            
        pool.close()
        pool.join()
        for process in processes:
            process.get()
        del processes, pool

        hintingSet = []

        if args.all:
            hintingSet = "decol", "haruno", "opti", "tokumin"
        else:
            if args.decol:
                hintingSet.append("decol")
            if args.haruno:
                hintingSet.append("haruno")
            if args.opti:
                hintingSet.append("opti")
            if args.tokumin:
                hintingSet.append("tokumin")

        if len(hintingSet) > 0:
            for item in hintingSet:

                for font in list(glob.glob("fonts/ttf/"+item+"/*.ttf")):
                    print ("["+font+"] Autohinting")
                    if "hinted" not in str(font):
                        subprocess.check_call(
                                [
                                    "ttfautohint",
                                    "--stem-width",
                                    "nsn",
                                    str(font),
                                    str(font).split(".")[0]+"-hinted.ttf",
                                ]
                            )
                        shutil.move(str(font).split(".")[0]+"-hinted.ttf", str(font))
                print ("Done!")

    elif args.shared:
        if os.path.isfile(sources / "Kaisei-Shared.glyphs"):
            main(("glyphs2ufo", str(sources / "Kaisei-Shared.glyphs"), "-m", str(sources / "ufo_shared")))
        else:
            print ("Cannot locate the 'shared' Glyphs file. Please confirm the file is unzipped.")
    else:
        print ("No fonts selected for export")