import os

from shutil import copyfile
from utils import file_helpers

"""Simply copy source file to target directory"""

def process_file(process_counter, args_tuple, source_file, target_dir):
	if not os.path.exists(target_dir):
		os.makedirs(target_dir)
	target_file = file_helpers.join_path_segment("/", target_dir, source_file[source_file.rfind('/'):])
	copyfile(source_file, target_file)
	print("\tCopied to {}".format(target_file))

	return target_file