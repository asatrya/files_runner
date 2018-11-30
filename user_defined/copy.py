from shutil import copyfile
from utils import file_helpers

"""Simply copy source file to target directory"""

def process_file(source_file, target_dir):
	target_file = file_helpers.join_path_segment("/", target_dir, source_file[source_file.rfind('/'):])
	copyfile(source_file, target_file)
	print("\tCopied to {}".format(target_file))

	return target_file