import os
from glob import glob
from argparse import ArgumentParser, Namespace
import pathlib
import logging
from typing import List, Tuple
from shutil import copy2, move
from decord import VideoReader, cpu
from tqdm import tqdm
import pandas as pd
import csv


SUB_FOLDERS = ["train", "test", "val"]
REPLACEMENT_FOLDER_NAME = "replacement"
ANNOTATIONS_FOLDER_NAME = "annotations"


def rename(args: Namespace):
  logging.info("renaming files")
  new_list = list()
  new_list.extend(SUB_FOLDERS)
  new_list.append(REPLACEMENT_FOLDER_NAME)
  for subfolder in new_list:
    files = glob(
        os.path.join(
            args.folder,
            subfolder,
            "**",
            "*.mp4"),
        recursive=True)

    for i, f in enumerate(tqdm(files)):
      path = pathlib.PosixPath(f).absolute()
      id = path.stem[0:11]
      new_name = os.path.join(str(path.parent), id + path.suffix)
      logging.debug(f"Renamed {f} to {new_name}")
      if args.dry_run:
        continue

      # --------------dangerous operations below, be careful---------------

      path.rename(new_name)
    logging.info(f"Renamed {len(files)} files in {subfolder}")


def copy_replacement(args: Namespace):
  logging.info("copying replacements")
  file_path_list = list()
  for subfolder in SUB_FOLDERS:
    files = glob(
        os.path.join(
            args.folder,
            subfolder,
            "**",
            "*.mp4"),
        recursive=True)
    file_path_list.extend(files)
  file_id_list = [pathlib.PosixPath(f).stem[0:11] for f in file_path_list]

  replace_dict = dict()
  replacement_list = glob(
      os.path.join(
          args.folder,
          REPLACEMENT_FOLDER_NAME,
          "**",
          "*.mp4"),
      recursive=True, include_hidden=False)
  for f in replacement_list:
    id = pathlib.PosixPath(f).stem[0:11]
    replace_dict[id] = f

  len_ = len(file_id_list)
  for id, path in tqdm(zip(file_id_list, file_path_list), total=len_):
    if id in replace_dict.keys() and not args.dry_run:
      copy2(replace_dict[id], path)

  logging.info("done copying replacements")


def check_corrupt_and_missing(args: Namespace):
  logging.info("check for still corrupted files after replacement")
  for subfolder in SUB_FOLDERS:
    df_orig = pd.read_csv(os.path.join(args.folder, ANNOTATIONS_FOLDER_NAME, f"{subfolder}.csv"), sep=",")
    file_ids = df_orig.youtube_id.to_list()
    corrupted_list = []
    logging.info(f"checking in {subfolder}")
    for i, id in enumerate(tqdm(file_ids)):
      file_path = pathlib.PosixPath(os.path.join(args.folder, subfolder, f"{id}.mp4"))
      if args.verbose:
        logging.debug("opened file: {}".format(id))
      if not file_path.exists():
        logging.warning(f"Video {id} not found")
        corrupted_list.append(i)
        continue
      try:
        video = VideoReader(str(file_path.absolute()), num_threads=1, ctx=cpu(0))
        test_frames = video.get_batch([0, 1, 2])
        if test_frames is None or len(test_frames) == 0:
          logging.warning("zero len file: {}".format(id))
          corrupted_list.append(i)
      except Exception as e:
        logging.warning("Corrupted file: {} with error {}".format(id, str(e)))
        corrupted_list.append(i)
    if len(corrupted_list) == 0:
      continue

    # write uncorrupted annotations
    df_orig.drop(index=corrupted_list, inplace=True)
    df_orig.reset_index()
    logging.info(f"removed {len(corrupted_list)} files from {subfolder}")

    with open(os.path.join(args.folder, ANNOTATIONS_FOLDER_NAME, f"{subfolder}_cleaned.csv"), mode="w") as f:
      df_orig.to_csv(f, sep=",", index=False, quoting=csv.QUOTE_NONNUMERIC)


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
      "--check-corrupt",
      action="store_true",
      help="Check for corrupted files")
  parser.add_argument(
      "-r",
      "--rename",
      action="store_true",
      help="Rename files")
  parser.add_argument("--run", action="store_true")

  args = parser.parse_args()

  logging.basicConfig(
      filename="sanitizer.log",
      filemode="w",
      level=logging.DEBUG if args.verbose else logging.INFO)
  if args.dry_run:
    logging.info("Dry run mode enabled")

  if args.rename:
    rename(args)

  if args.check_corrupt:
    logging.info("Replacing for corrupted files")
    check_corrupt_and_missing(args)

  if args.run:
    rename(args)
    copy_replacement(args)
    check_corrupt_and_missing(args)

  # corrupted_list = ["-7kbO0v4hag"]
  # orig_annotation_path = os.path.join(
  #     args.folder, ANNOTATIONS_FOLDER_NAME, f"train.csv")
  # df_orig = pd.read_csv(orig_annotation_path, sep=",")
  # print(df_orig.youtube_id.to_list())
