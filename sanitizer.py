import os
from glob import glob
from argparse import ArgumentParser, Namespace
import pathlib
import logging
from typing import List, Tuple
from shutil import copy2, move
from decord import VideoReader, cpu
from tqdm import tqdm


SUB_FOLDERS = ["train", "test", "val"]
REPLACEMENT_FOLDER_NAME = "replacement"
CORRUPT_FOLDER_NAME = "corrupted_videos"


def rename(args: Namespace):
  for subfolder in SUB_FOLDERS:
    files = glob(
        os.path.join(
            args.folder,
            subfolder,
            "**",
            "*.mp4"),
        recursive=True)

    for i, f in enumerate(files):
      path = pathlib.PosixPath(f).absolute()
      id = path.stem[0:11]
      new_name = os.path.join(str(path.parent), id + path.suffix)
      logging.debug(f"Renamed {f} to {new_name}")
      if args.dry_run:
        continue

      # --------------dangerous operations below, be careful---------------

      path.rename(new_name)
    logging.info(f"Renamed {len(files)} files in {subfolder}")


def _get_corrupt_list(args: Namespace) -> Tuple[str, List[str]]:
  # check for corrupt files and replace them from the replacement folder
  files = glob(
      os.path.join(
          args.folder,
          REPLACEMENT_FOLDER_NAME,
          "**",
          "*.mp4"),
      recursive=True)
  if len(files) == 0:
    return "", []

  filenames = [pathlib.PosixPath(f).stem[0:11] for f in files]
  return pathlib.PosixPath(files[0]).absolute().parent, filenames


def replace_corrupt(args: Namespace):
  os.system("rm .??*")
  corrupted_root_folder, corrupted_id = _get_corrupt_list(args)
  for s in SUB_FOLDERS:

    files = glob(
        os.path.join(
            args.folder,
            s,
            "**",
            "*.mp4"),
        recursive=True)

    for i, f in enumerate(files):
      path = pathlib.PosixPath(f).absolute()
      id = path.stem[0:11]
      if id not in corrupted_id:
        continue
      logging.debug(f"Replace file: {f}")
      if args.dry_run:
        continue
      copy2(os.path.join(corrupted_root_folder, f"{id}.mp4"), f)


def test_corrupt(args: Namespace):
  corrupted_list = []
  for s in SUB_FOLDERS:
    files = glob(
        os.path.join(
            args.folder,
            s,
            "**",
            "*.mp4"),
        recursive=True)
    for f in tqdm(files):
      file_obj = pathlib.PosixPath(f)
      if args.verbose:
        logging.debug("opened file: {}".format(f))
      try:
        video = VideoReader(f, num_threads=1, ctx=cpu(0))

        if video.get_batch([0, 1, 2]) is None:
          logging.info("Corrupted file: {}".format(f))
          os.makedirs(os.path.join(CORRUPT_FOLDER_NAME, s), exist_ok=True)
          move(f, os.path.join(CORRUPT_FOLDER_NAME, s, file_obj.name))
          corrupted_list.append(f)
      except Exception as e:
        logging.info("Corrupted file: {}".format(f))
        corrupted_list.append(f)
        os.makedirs(os.path.join(CORRUPT_FOLDER_NAME, s), exist_ok=True)
        move(f, os.path.join(CORRUPT_FOLDER_NAME, s, file_obj.name))
        logging.info(e)

  with open("corrupted_files.txt", "w") as f:
    f.write("\n".join(corrupted_list))


if __name__ == "__main__":
  parser = ArgumentParser()
  parser.add_argument(
      "folder",
      type=str,
      help="Root of the folder to sanitize")
  parser.add_argument(
      "-n", "--dry-run",
      action="store_true",
      help="Don't actually rename files, just print what would be done.")
  parser.add_argument(
      "-v",
      "--verbose",
      action="store_true",
      help="Verbosity level")
  parser.add_argument(
      "-t",
      "--test-corrupt",
      action="store_true",
      help="Check for corrupted files")
  parser.add_argument(
      "-c",
      "--replace-corrupt",
      action="store_true",
      help="Replace corrupted files")
  parser.add_argument(
      "-r",
      "--rename",
      action="store_true",
      help="Rename files")

  args = parser.parse_args()

  logging.basicConfig(
      filename="sanitizer.log",
      level=logging.DEBUG if args.verbose else logging.INFO)
  if args.dry_run:
    logging.info("Dry run mode enabled")

  if args.rename:
    rename(args)

  if args.replace_corrupt:
    logging.info("Replacing for corrupted files")
    replace_corrupt(args)

  if args.test_corrupt:
    test_corrupt(args)
