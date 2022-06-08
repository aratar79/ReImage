import sys
import os
import shutil
import argparse
import math
import filetype

from datetime import datetime
from tqdm import tqdm
from PIL import Image
from PIL import UnidentifiedImageError

global no_processed_files
global processed_files
global format_date


def global_max_weight(weightFile):
    global MAX_FILE_WEIGHT
    MAX_FILE_WEIGHT = weightFile


def global_no_processed_files(file):
    no_processed_files.append(file)


def global_processed_files(file):
    processed_files.append(file)


def global_backup(path):
    global BACKUP
    BACKUP = path + "/ReImageBKP_" + format_date
    os.makedirs(BACKUP, exist_ok=True)


def process_only_file(file, verbose=False):
    if not os.path.exists(file):
        print(f"\nThe file {file} does not exist.")
        print(f"Process finished.")
        sys.exit()
    if BACKUP:
        shutil.copy(file, BACKUP + "/" + file)
    process_file(file, verbose)


def process_folder(path):
    content = [f for f in os.listdir(path) if os.path.isfile(f)]
    if BACKUP:
        for file in tqdm(content, ascii=True, desc="Create image backup"):
            if filetype.is_image(path + "/" + file):
                shutil.copy(
                    path + "/" + file,
                    BACKUP + "/" + path + "/" + file,
                )

    for file in tqdm(content, ascii=True, desc="Image processing"):
        process_file(file, False)


def process_folder_recursive(path):
    if BACKUP:
        for name_folder, sub_forders, files in tqdm(
            os.walk(path, topdown=False), ascii=True, desc="Create image backup"
        ):
            backup_folder = os.path.split(BACKUP)[-1]
            if name_folder != None and backup_folder in name_folder:
                continue
            os.makedirs(BACKUP + "/" + name_folder, exist_ok=True)
            for file in files:
                if filetype.is_image(name_folder + "/" + file):
                    shutil.copy(
                        name_folder + "/" + file,
                        BACKUP + "/" + name_folder + "/" + file,
                    )

    for name_folder, sub_forders, files in tqdm(
        os.walk(path, topdown=False), ascii=True, desc="Image processing"
    ):
        backup_folder = os.path.split(BACKUP)[-1]
        if name_folder != None and backup_folder in name_folder:
            continue
        for file in files:
            process_file(name_folder + "/" + file, False)


def process_file(file, verbose=False):
    try:
        processed = False
        weight = float("{0:.2f}".format(os.path.getsize(file) / 1024))
        #print(file)
        #print(weight)
        #print(MAX_FILE_WEIGHT)
        #print(filetype.is_image(file))
        if weight > MAX_FILE_WEIGHT and filetype.is_image(file):
            img = Image.open(file)
            img = img.convert('RGB')
            width, height = img.size
            scale = float("{0:.2f}".format(math.sqrt(MAX_FILE_WEIGHT / weight)))
            new_width = int(width * scale)
            new_height = int(height * scale)
            img = img.resize((new_width, new_height))
            processed = True
        else:
            #print("No aplica por tamanio o formato")
            global_no_processed_files(file)

    except Exception as e:
        #print(e)
        global_no_processed_files(file)
        pass

    finally:
        if processed:
            img.save(file)
            global_processed_files(file)
            if verbose:
                new_weight = float("{0:.2f}".format(os.path.getsize(file) / 1024))
                print(f"Original weight: {weight} KB, after ReImage: {new_weight} KB")


def main(argv):
    try:
        parser = argv
        parser.add_argument(
            "-cw",
            "--change-max-weight",
            help="Reduces an image up to a maximum weight in Kbytes.",
            type=int,
            default=0,
            metavar=("MAXWEIGHT"),
        )
        parser.add_argument("-f", "--file", help="Name of the file to be processed.")
        parser.add_argument(
            "-a", "--all", help="Processes all files in the folder", metavar=("PATH")
        )
        parser.add_argument(
            "-bkp",
            "--backup",
            help="Creates a copy of the original files in a given destination",
            metavar=("BACKUP PATH"),
        )
        parser.add_argument(
            "-R",
            "--recursive",
            help="Processes all files recursively in the folder and subfolders",
            action="store_true",
        )

        arguments = parser.parse_args()

        if arguments.change_max_weight:

            global_max_weight(float(arguments.change_max_weight))

            if arguments.backup:
                global_backup(arguments.backup)
            else:
                global BACKUP
                BACKUP = False

            if arguments.file:
                process_only_file(arguments.file, True)
            elif arguments.all and arguments.file is None:
                if arguments.recursive:
                    process_folder_recursive(arguments.all)
                else:
                    process_folder(arguments.all)
            else:
                print("Error in flag and arguments combination")
                parser.print_help()
        else:
            print("Error in flag and arguments combination")
            parser.print_help()

        print("\n")
        for nopfile in no_processed_files:
            print("Not processed file: " + nopfile)

        print(f"\n\nTotal number of files NOT processed: {len(no_processed_files)}")
        print(f"Total number of files processed: {len(processed_files)}")

    except Exception as e:
        pass
        # print("some error: ", str(e))
        # name_file = os.path.splitext(file)[0]
        # extension_file = os.path.splitext(file)[1]


if __name__ == "__main__":
    no_processed_files = []
    processed_files = []
    now = datetime.now()
    format_date = now.strftime("%Y_%m_%d_%H%M")
    main(
        argparse.ArgumentParser(
            description="Program to reduces an image up to a maximum weight in Kbytes."
        )
    )
