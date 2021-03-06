import sys
import os
import shutil
import argparse
import math
from turtle import back
import filetype
import logging

from datetime import datetime
from tqdm import tqdm
from PIL import Image
from PIL import UnidentifiedImageError
from tabulate import tabulate

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


def global_info(info):
    global INFO
    INFO = info


def process_only_file(file, verbose=False):
    if not os.path.exists(file):
        loggerErr.error("The file {file} does not exist.")
        loggerErr.error(f"Process finished.")
        print(f"\nThe file {file} does not exist.")
        print(f"Process finished.")
        sys.exit()
    if BACKUP:
        loggerApp.info("Start backup....")
        loggerApp.info(f"BKP FILE: {file}")
        shutil.copy(file, BACKUP + "/" + file)
    if INFO:
        images = []
        images.append(get_info_image(file))
        print_info_image(images)
        return
    process_file(file, verbose)


def process_folder(path):
    content = [f for f in os.listdir(path) if os.path.isfile(f)]
    if BACKUP:
        loggerApp.info("Start backup....")
        for file in tqdm(content, ascii=True, desc="Create image backup"):
            if filetype.is_image(path + "/" + file):
                loggerApp.info(f"BKP FILE: {file}")
                shutil.copy(
                    path + "/" + file,
                    BACKUP + "/" + path + "/" + file,
                )
    if INFO:
        path = os.path.abspath(path)
        folder_content = [f for f in os.listdir(path)]
        images = [get_info_image(f"{path}/{i}") for i in folder_content]
        print_info_image(images)
        return

    for file in tqdm(content, ascii=True, desc="Image processing"):
        process_file(file, False)


def process_folder_recursive(path):
    images = []
    if BACKUP:
        loggerApp.info("Start backup....")
        for name_folder, sub_forders, files in tqdm(
            os.walk(path, topdown=False), ascii=True, desc="Create image backup"
        ):
            backup_folder = os.path.split(BACKUP)[-1]
            loggerApp.info(f"BKP FOLDER: {name_folder}")
            if name_folder != None and backup_folder in name_folder:
                continue
            os.makedirs(BACKUP + "/" + name_folder, exist_ok=True)
            for file in files:
                if filetype.is_image(name_folder + "/" + file):
                    loggerApp.info(f"BKP FILE: {file}")
                    shutil.copy(
                        name_folder + "/" + file,
                        BACKUP + "/" + name_folder + "/" + file,
                    )
    if INFO:
        path = os.path.abspath(path)
        for name_folder, sub_forders, files in os.walk(path, topdown=False):
            for file in files:
                file_path = f"{name_folder}/{file}"
                images.append(get_info_image(file_path))
        print_info_image(images)
        return

    for name_folder, sub_forders, files in tqdm(
        os.walk(path, topdown=False), ascii=True, desc="Image processing"
    ):
        if BACKUP:
            backup_folder = os.path.split(BACKUP)[-1]
            if name_folder != None and backup_folder in name_folder:
                continue
            for file in files:
                process_file(name_folder + "/" + file, False)
        else:
            if name_folder != None:
                for file in files:
                    process_file(name_folder + "/" + file, False)


def process_file(file, verbose=False):
    try:
        processed = False
        weight = float("{0:.2f}".format(os.path.getsize(file) / 1024))
        loggerApp.info(
            f"File to process: {file}, is an image: {filetype.is_image(file)}, File weight: {weight} Kb, Maximum weight allowed: {MAX_FILE_WEIGHT}"
        )
        if weight > MAX_FILE_WEIGHT and filetype.is_image(file):
            loggerApp.info(f"The file fulfils the conditions")
            img = Image.open(file)
            img = img.convert("RGB")
            width, height = img.size
            scale = float("{0:.2f}".format(math.sqrt(MAX_FILE_WEIGHT / weight)))
            new_width = int(width * scale)
            new_height = int(height * scale)
            img = img.resize((new_width, new_height))
            processed = True
        else:
            loggerApp.info(
                f"The file does not meet the conditions, either it is not an image or it is too large."
            )
            global_no_processed_files(file)

    except Exception as e:
        loggerErr.error(
            f"File to process: {file}, is an image: filetype.is_image(file), File weight: {weight} Kb, Maximum weight allowed: {MAX_FILE_WEIGHT}"
        )
        loggerErr.error(f"The file has not been processed, an error has occurred.")
        loggerErr.error(f"ERROR: {e}")
        global_no_processed_files(file)
        pass

    finally:
        if processed:
            try:
                img.save(file)
                new_weight = float("{0:.2f}".format(os.path.getsize(file) / 1024))
                loggerApp.info(
                    f"Original weight: {weight} KB, after ReImage: {new_weight} KB"
                )
                loggerApp.info(f"file saved and processed")
                global_processed_files(file)
                if verbose:
                    print(
                        f"Original weight: {weight} KB, after ReImage: {new_weight} KB"
                    )
            except Exception as e:
                loggerErr.error(
                    f"The file {file} has not been saved, an error has occurred."
                )
                loggerErr.error(f"ERROR: {e}")


def info_folder_recursive(path):
    pass


def print_info_image(images):
    filterded_images = [i for i in images if not i == None]
    header_info = [
        "idx",
        "File Name",
        "Size",
        "Ratio",
        "Orientation",
        "Format",
        "Dpi's",
        "Mode",
        "Weight",
    ]
    print("\n")
    print(
        tabulate(
            filterded_images, headers=header_info, showindex="always", tablefmt="simple"
        )
    )
    print("\n")


def get_info_image(file):
    result = []
    try:
        if filetype.is_image(file):
            image = Image.open(file)
            # get width and height
            width, height = image.size
            # get image ratio
            ratio = ""
            rt = width / height
            rt = float("{0:.2f}".format(rt))
            if rt == 1:
                ratio = "1:1"
            elif rt == 1.33:
                ratio = "4:3"
            elif rt == 1.50:
                ratio = "3:2"
            else:
                ratio = "Don't know"
            # get image orientation
            orientation = ""
            if width > height:
                orientation = "Horizontal"
            if width < height:
                orientation = "Vertical"
            if width == height:
                orientation = "Equals"
            # get image format
            formt = image.format
            # get image mode
            mode = image.mode
            # get image dpi's
            dpi = image.info.get("dpi")
            # get image Weight
            weight = float("{0:.2f}".format(os.path.getsize(file) / 1024))

            result.append(os.path.split(file)[-1])
            result.append({f"w:{width}", f"h:{height}"})
            result.append(ratio)
            result.append(orientation)
            result.append(formt)
            result.append(dpi)
            result.append(mode)
            result.append(f"{weight} KB")

            return result

    except Exception as e:
        loggerErr.error(
            f"Checking the image information: {file} an error has occurred."
        )
        loggerErr.error(f"ERROR: {e}")


def setup_logger(name, log_file, level=logging.INFO):
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    handler = logging.FileHandler(log_file)
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)

    return logger


def logger_config():
    try:
        global loggerApp
        global loggerErr
        global loggerNoProcess

        loggerApp = setup_logger("info_logger", "reimage.info.log")
        loggerErr = setup_logger("error_logger", "reimage.error.log", logging.ERROR)
        loggerNoProcess = setup_logger(
            "noprocess_logger", "reimage.noprocess.log", logging.WARNING
        )

    except Exception as e:
        print(
            "Error creating the log files, possibly you do not have permissions and will not be able to continue the process. "
            + "Raise the permissions of your terminal or contact your system administrator."
        )


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
        parser.add_argument(
            "-i",
            "--info",
            help="Returns information related to the image(s)",
            action="store_true",
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

        loggerApp.info("Run process...")

        if arguments.backup:
            pathname = os.path.abspath(arguments.backup)
            loggerApp.info(f"Backup enabled on the path: {pathname}")
            global_backup(arguments.backup)
        else:
            global BACKUP
            BACKUP = False

        if arguments.change_max_weight:

            global_max_weight(float(arguments.change_max_weight))

            if arguments.file:
                loggerApp.info(f"Start the process for a single file")
                process_only_file(arguments.file, True)
            elif arguments.all and arguments.file is None:
                if arguments.recursive:
                    loggerApp.info(
                        f"Start the recursive process, all the files and directories"
                    )
                    process_folder_recursive(arguments.all)
                else:
                    loggerApp.info(f"Start the process for all files in the directory")
                    process_folder(arguments.all)
            else:
                print("Error in flag and arguments combination")
                parser.print_help()
        elif arguments.info:
            global_info(True)
            if arguments.file:
                process_only_file(arguments.file)
            if arguments.all:
                if arguments.recursive:
                    process_folder_recursive(arguments.all)
                else:
                    process_folder(arguments.all)
        else:
            print("Error in flag and arguments combination")
            parser.print_help()

        print("\n")
        if not INFO:
            for nopfile in no_processed_files:
                loggerNoProcess.warning(f"Not processed file: {nopfile}")

            loggerApp.info(
                f"\n\nTotal number of files NOT processed: {len(no_processed_files)}"
            )
            loggerApp.info(f"Total number of files processed: {len(processed_files)}")
            print(f"\nTotal number of files NOT processed: {len(no_processed_files)}")
            print(f"Total number of files processed: {len(processed_files)}")

    except Exception as e:
        loggerErr.error(f"Some error has occurred, process terminated")
        loggerErr.error(f"ERROR: {e}")


if __name__ == "__main__":
    logger_config()
    global_info(False)
    no_processed_files = []
    processed_files = []
    now = datetime.now()
    format_date = now.strftime("%Y_%m_%d_%H%M")
    main(
        argparse.ArgumentParser(
            description="Program to reduces an image up to a maximum weight in Kbytes."
        )
    )
