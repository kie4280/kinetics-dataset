import os
from glob import glob
from argparse import ArgumentParser, Namespace
import pathlib
import logging
from typing import List, Tuple
from shutil import copy2


SUB_FOLDERS = ["train", "test", "val"]
CORRUPT_FOLDER_NAME = "replacement"


def _get_corrupt(args: Namespace) -> Tuple[str, List[str]]:
  # check for corrupt files and replace them from the replacement folder
  files = glob(
      os.path.join(
          args.folder,
          CORRUPT_FOLDER_NAME,
          "**",
          "*.mp4"),
      recursive=True)
  if len(files) == 0:
    return "", []

  filenames = [pathlib.PosixPath(f).stem[0:11] for f in files]
  return pathlib.PosixPath(files[0]).absolute().parent, filenames


def shorten_filename(args: Namespace, subfolder: str):
  if args.check_corruption:
    corrupted_root_folder, corrupted_id = _get_corrupt(args)
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
    if args.check_corruption and id in corrupted_id:
      replacement_file = f"{corrupted_root_folder}/{id}.mp4"
      logging.debug(f"copying {replacement_file} to {new_name}")
    else:
      logging.debug(f"Renamed {f} to {new_name}")
    if args.dry_run:
      continue

    # --------------dangerous operations below, be careful---------------

    if args.check_corruption and id in corrupted_id:
      replacement_file = f"{corrupted_root_folder}/{id}.mp4"
      os.remove(f)
      copy2(replacement_file, new_name)
    else:
      path.rename(new_name)
  logging.info(f"Renamed {len(files)} files in {subfolder}")


def sanitize(args: Namespace):
  for s in SUB_FOLDERS:
    shorten_filename(args, s)
    if args.check_corruption:
      _get_corrupt(args)


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
      "-c",
      "--check_corruption",
      action="store_true",
      help="Check for corrupted files")
  args = parser.parse_args()
  logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO)
  if args.dry_run:
    logging.info("Dry run mode enabled")
  sanitize(args)
