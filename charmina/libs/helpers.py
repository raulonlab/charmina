import os
import sys
import importlib.util
import glob
import shutil
import time
from pathlib import Path
from typing import List, Union


class TimeTaken:
    """
    Records the duration of a task in debug mode and prints it to the console.
    """

    def __init__(self, title: str, callback: callable = None):
        self.title = title
        self.callback = callback
        self.start = None

    def __enter__(self):
        self.start = time.time()

    def __exit__(self, exc_type, exc_val, exc_tb):
        diff = time.time() - self.start
        if self.callback:
            self.callback(f"TimeTaken - {self.title}: {diff:.4f} seconds")
        else:
            print(f"TimeTaken - {self.title}: {diff:.4f} seconds")


def get_filtered_directories(
    directory_filter: str | None = None,
    base_path: Path = ".",
) -> List[Path]:

    # if not directory_filter or directory_filter.lower() in str(base_path).lower():
    #     return [base_path]

    if not directory_filter:
        return [base_path]

    # Search for subdirectories matching directory_filter
    filtered_directories = []
    for dirpath, dirs, _ in os.walk(base_path):
        for dir in dirs:
            full_dir_path = Path(dirpath, dir)

            if directory_filter.lower() in str(full_dir_path).lower():
                filtered_directories.append(full_dir_path)

                # skip subdirectories
                dirs.clear()

    return filtered_directories


def copy_files_between_directories(
    glob_search: str, src_dir: Path | str, dst_dir: Path | str
) -> int:
    src_dir = str(src_dir)
    dst_dir = str(dst_dir)

    file_counter = 0
    for src_file in glob.iglob(glob_search, recursive=True, root_dir=src_dir):
        os.makedirs(os.path.join(dst_dir, os.path.dirname(src_file)), exist_ok=True)
        dst_file_path = os.path.join(dst_dir, src_file)
        if not os.path.exists(dst_file_path):
            shutil.copy(os.path.join(src_dir, src_file), dst_file_path)
            file_counter += 1

    return file_counter


# Given a file path, replace the root path with the output root path. Argument paths can be relative or absolute.
def replace_file_path_root(
    file_path: Union[Path, str],
    input_root_path: Union[Path, str],
    output_root_path: Union[Path, str],
) -> str:
    if not file_path:
        return str(file_path)
    elif not output_root_path:
        return str(file_path)

    # Convert to Path objects and make them absolute
    file_path = Path(file_path).resolve()
    input_root_path = Path(input_root_path).resolve()
    output_root_path = Path(output_root_path).resolve()

    try:
        # Get the relative path from the input root path
        relative_path = file_path.relative_to(input_root_path)
        # Combine the output root path with the relative path
        new_path = output_root_path / relative_path
        return str(new_path)
    except ValueError:
        # If file_path is not relative to input_root_path, return the original file_path
        return str(file_path)


# borrowed from: https://stackoverflow.com/a/1051266/656011
def check_for_package(package):
    if package in sys.modules:
        return True
    elif (spec := importlib.util.find_spec(package)) is not None:
        try:
            module = importlib.util.module_from_spec(spec)

            sys.modules[package] = module
            spec.loader.exec_module(module)

            return True
        except ImportError:
            return False
    else:
        return False


def process_memory_limit(limit):
    import resource as rs

    soft, hard = rs.getrlimit(rs.RLIMIT_AS)
    rs.setrlimit(rs.RLIMIT_AS, (limit, hard))


def sanitize_text(text: str) -> str:
    """Normalize special characters in text to ASCII equivalents."""

    if not text:
        return text

    replacements = {
        # Quotation marks
        ord("\u2018"): "'",  # left single quotation mark
        ord("\u2019"): "'",  # right single quotation mark
        ord("\u201c"): '"',  # left double quotation mark
        ord("\u201d"): '"',  # right double quotation mark
        # Ellipsis
        ord("\u2026"): "...",  # ellipsis
        # Dashes
        ord("\u2013"): "-",  # en dash
        ord("\u2014"): "-",  # em dash
        # Additional common replacements can be added here.
    }
    return text.translate(replacements).strip()
