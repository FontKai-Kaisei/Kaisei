from glyphsLib.cli import main
from fontTools.ttLib import newTable
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
        variant = "W4"
        if "W5" in str(file):
            variant = "W5"
        elif "W7" in str(file):
            variant = "W7"
        elif "W8" in str(file):
            variant = "W8"

        sharedFont = ufoLib2.Font.open(sources / "ufo_shared" / str("FK-Kaisei-shared-"+variant+".ufo"))

        print ("["+fontName+"] Importing shared glyphs")
        for glyph in sharedFont.glyphOrder:
            exportfont.addGlyph(sharedFont[glyph])

        print ("["+fontName+"] Adding feature code") 
        featureSet = sources / "features.fea"
        exportfont.features.text = featureSet.read_text()

        print ("["+fontName+"] Compiling")
        static_ttf = ufo2ft.compileTTF(exportfont)

        print ("["+fontName+"] Adding stub DSIG")
        static_ttf["DSIG"] = newTable("DSIG")     #need that stub dsig
        static_ttf["DSIG"].ulVersion = 1
        static_ttf["DSIG"].usFlag = 0
        static_ttf["DSIG"].usNumSigs = 0
        static_ttf["DSIG"].signatureRecords = []
        static_ttf["head"].flags |= 1 << 3        #sets flag to always round PPEM to integer

        print ("["+fontName+"] Saving")

        os.makedirs("Fonts/ttf/"+name, exist_ok=True)

        outputName = "Fonts/ttf/"+name+"/FK-Kaisei-"+name.capitalize()+"-"+variant+".ttf"
        if name == "haruna":
            outputName = "Fonts/ttf/"+name+"/FK-Kaisei-HarunoUmi-"+variant+".ttf"

        static_ttf.save(outputName)

    shutil.rmtree(str(path))

def execute(name:str, sources:Path):
    print ("Generating "+name+" UFO")
    outputPath = sources / str("ufo_"+name)
    os.makedirs(outputPath, exist_ok=True)
    glyphsName = "FK-Kaisei-"+name.capitalize()+".glyphs"
    if name == "haruno":
        glyphsName = "FK-Kaisei-HarunoUmi.glyphs"
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
        print ("Generating shared UFO")
        os.makedirs("sources/ufo_shared", exist_ok=True)
        if args.shared:
            if os.path.isfile(sources / "FK-Kaisei-Shared.glyphs"):
                main(("glyphs2ufo", str(sources / "FK-Kaisei-Shared.glyphs"), "-m", str(sources / "ufo_shared")))
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

        for font in list(glob.glob("Fonts/ttf/**/*.ttf", recursive=True)):
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
    else:
        print ("No fonts selected for export")