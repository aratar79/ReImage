import io
import sys
import os
import shutil
import argparse
import math
import filetype
import logging
import requests

from datetime import datetime
from tqdm import tqdm
from PIL import Image
from tabulate import tabulate
from dotenv import load_dotenv


class ImageProcessor:
    def __init__(self):
        self.no_processed_files = []
        self.processed_files = []
        self.backup_dir = None
        self.max_file_weight = None
        self.img_width = None
        self.info_mode = False
        self.bkg_remove = False
        self.azure_endpoint = None
        self.azure_key = None

    def set_max_weight(self, weight):
        self.max_file_weight = weight

    def set_img_width(self, width):
        self.img_width = width

    def enable_info_mode(self):
        self.info_mode = True

    def enable_background_removal(self):
        self.bkg_remove = True

    def set_backup_directory(self, path):
        self.backup_dir = os.path.join(path, f"ReImageBKP_{self._get_formatted_date()}")
        os.makedirs(self.backup_dir, exist_ok=True)

    def load_azure_credentials(self):
        load_dotenv()
        self.azure_endpoint = os.getenv("AI_SERVICE_ENDPOINT")
        self.azure_key = os.getenv("AI_SERVICE_KEY")

    def _get_formatted_date(self):
        return datetime.now().strftime("%Y_%m_%d_%H%M")

    def log_unprocessed_file(self, file):
        self.no_processed_files.append(file)

    def log_processed_file(self, file):
        self.processed_files.append(file)

    def process_file(self, file, verbose=False, resize=False, use_ai=True):
        if not os.path.exists(file):
            loggerErr.error(f"The file {file} does not exist.")
            self._print_and_exit(f"The file {file} does not exist.")

        self._backup_file(file)

        if self.info_mode:
            images = [self._get_image_info(file)]
            self._print_image_info(images)
            return

        img = self._open_image(file)
        if img:
            processed = False

            if self.bkg_remove:
                img = self._remove_background(img, file, use_ai)
                processed = True

            if resize:
                img = self._resize_image(img, file)
                processed = True

            if self.max_file_weight is not None:
                img, weight_processed = self._reduce_image_weight(img, file)
                processed = processed or weight_processed

            if processed:
                self._save_processed_image(img, file, processed, verbose)

    def process_folder(self, path, recursive=False, resize=False):
        content = self._get_folder_content(path, recursive)

        self._backup_files(content)
        if self.info_mode:
            images = [self._get_image_info(file) for file in content]
            self._print_image_info(images)
            return

        for file in tqdm(content, ascii=True, desc="Image processing"):
            self.process_file(file, resize=resize)

    def _get_folder_content(self, path, recursive):
        if recursive:
            return [os.path.join(root, file) for root, _, files in os.walk(path) for file in files if
                    os.path.isfile(os.path.join(root, file))]
        else:
            return [os.path.join(path, f) for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]

    def _backup_files(self, files):
        if self.backup_dir:
            loggerApp.info("Start backup....")
            for file in tqdm(files, ascii=True, desc="Create image backup"):
                if filetype.is_image(file):
                    loggerApp.info(f"BKP FILE: {os.path.basename(file)}")
                    backup_path = os.path.join(self.backup_dir, os.path.basename(file))
                    shutil.copy(file, backup_path)

    def _backup_file(self, file):
        if self.backup_dir:
            loggerApp.info(f"BKP FILE: {file}")
            backup_path = os.path.join(self.backup_dir, os.path.basename(file))
            shutil.copy(file, backup_path)

    def _open_image(self, file):
        try:
            return Image.open(file)
        except Exception as e:
            loggerErr.error(f"Error opening file: {file}, ERROR: {e}")
            self.log_unprocessed_file(file)
            return None

    def _resize_image(self, img, file):
        width, height = img.size
        loggerApp.info(f"Resizing image {file} to width: {self.img_width}")
        ratio = max(self.img_width / width, 0 / height)
        new_width = int(width * ratio)
        new_height = int(height * ratio)
        return img.resize((new_width, new_height))

    def _reduce_image_weight(self, img, file):
        weight = os.path.getsize(file) / 1024
        if float(weight) > float(self.max_file_weight):
            loggerApp.info(f"Reducing weight of file {file}")
            scale = math.sqrt(self.max_file_weight / weight)
            new_width, new_height = int(img.width * scale), int(img.height * scale)
            return img.resize((new_width, new_height)), True
        return img, False

    def _save_processed_image(self, img, file, processed, verbose):
        if processed:
            try:
                save_file = file
                if self.bkg_remove and img.mode == "RGBA":
                    save_file = self._get_transparent_save_path(file)

                img.save(save_file)
                new_weight = os.path.getsize(save_file) / 1024
                loggerApp.info(f"File processed and saved: {save_file} | New weight: {new_weight} KB")
                self.log_processed_file(save_file)
                if verbose:
                    print(f"File processed: {save_file} | New weight: {new_weight} KB")
            except Exception as e:
                loggerErr.error(f"Error saving file {file}: {e}")
                self.log_unprocessed_file(file)

    def _remove_background(self, img, file, use_ai=True):
        if not use_ai and img.format == "PNG":
            loggerApp.info(f"Removing background locally for file {file}")
            img = img.convert("RGBA")
            data = img.getdata()

            background_color = (255, 255, 255, 255)

            new_data = []
            for item in data:
                if item[:3] == background_color[:3]:
                    new_data.append((255, 255, 255, 0))
                else:
                    new_data.append(item)

            img.putdata(new_data)
            return img

        try:
            image_byte_array = io.BytesIO()
            img.save(image_byte_array, format=img.format)
            image_byte_array = image_byte_array.getvalue()

            response = requests.post(
                url=f"{self.azure_endpoint}/computervision/imageanalysis:segment?api-version=2023-02-01-preview&mode=backgroundRemoval",
                headers={
                    "Ocp-Apim-Subscription-Key": self.azure_key,
                    "Content-Type": "application/octet-stream"
                },
                data=image_byte_array
            )

            if response.status_code == 200:
                loggerApp.info(f"Background removal using AI successful for file {file}")
                return Image.open(io.BytesIO(response.content)).convert("RGBA")
            else:
                loggerErr.error(
                    f"Background removal using AI failed for file {file} with status code {response.status_code}")
                return img

        except Exception as e:
            loggerErr.error(f"Error removing background for file {file} using AI: {e}")
            return img

    def _get_transparent_save_path(self, file):
        base_name, ext = os.path.splitext(os.path.basename(file))
        return os.path.join(os.path.dirname(file), f"{base_name}_no_bg{ext}")

    def _get_image_info(self, file):
        try:
            if filetype.is_image(file):
                img = Image.open(file)
                width, height = img.size
                ratio = f"{width / height:.2f}"
                orientation = "Horizontal" if width > height else "Vertical" if width < height else "Square"
                return [
                    os.path.basename(file),
                    f"w:{width}, h:{height}",
                    ratio,
                    orientation,
                    img.format,
                    img.info.get("dpi"),
                    img.mode,
                    f"{os.path.getsize(file) / 1024:.2f} KB"
                ]
        except Exception as e:
            loggerErr.error(f"Error retrieving image info for {file}: {e}")
        return None

    def _print_image_info(self, images):
        filtered_images = [i for i in images if i is not None]
        headers = ["File Name", "Dimensions", "Ratio", "Orientation", "Format", "Dpi's", "Mode", "Weight"]
        print(tabulate(filtered_images, headers=headers, showindex="always", tablefmt="simple"))

    def _print_and_exit(self, message):
        loggerErr.error(message)
        print(message)
        sys.exit()


def setup_logger(name, log_file, level=logging.INFO):
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    handler = logging.FileHandler(log_file)
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)

    return logger


def logger_config():
    global loggerApp, loggerErr, loggerNoProcess
    loggerApp = setup_logger("info_logger", "reimage.info.log")
    loggerErr = setup_logger("error_logger", "reimage.error.log", logging.ERROR)
    loggerNoProcess = setup_logger("noprocess_logger", "reimage.noprocess.log", logging.WARNING)


def main():
    parser = argparse.ArgumentParser(description="Program to reduce image size or change image properties.")
    parser.add_argument("-cw", "--change-max-weight", help="Reduce image size to a maximum weight in KB.", type=int)
    parser.add_argument("-i", "--info", help="Show image information.", action="store_true")
    parser.add_argument("-f", "--file", help="File to process.")
    parser.add_argument("-a", "--all", help="Process all files in the specified directory.", metavar="PATH")
    parser.add_argument("-bkp", "--backup", help="Backup original files to specified directory.", metavar="BACKUP_PATH")
    parser.add_argument("-R", "--recursive", help="Process files recursively in directories.", action="store_true")
    parser.add_argument("-r", "--resize", help="Resize images to a specified width.", type=int, metavar="WIDTH")
    parser.add_argument("-rb", "--remove-background", help="Remove background from images.", action="store_true")
    parser.add_argument("-noai", "--no-ai", help="Remove background without using AI for PNG files.", action="store_true")

    args = parser.parse_args()
    processor = ImageProcessor()

    if args.backup:
        processor.set_backup_directory(args.backup)

    if args.change_max_weight:
        processor.set_max_weight(args.change_max_weight)

    if args.resize:
        processor.set_img_width(args.resize)

    if args.info:
        processor.enable_info_mode()

    if args.remove_background:
        processor.enable_background_removal()

    processor.load_azure_credentials()

    if args.file:
        processor.process_file(args.file, resize=args.resize is not None, use_ai=not args.no_ai)
    elif args.all:
        processor.process_folder(args.all, recursive=args.recursive, resize=args.resize is not None)
    else:
        parser.print_help()

    if not processor.info_mode:
        print(f"\nTotal files not processed: {len(processor.no_processed_files)}")
        print(f"Total files processed: {len(processor.processed_files)}")


if __name__ == "__main__":
    logger_config()
    main()

