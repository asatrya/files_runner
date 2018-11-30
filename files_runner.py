import sys
import os
import argparse
import re

from user_defined import *
from utils import file_helpers
from utils import gcs_helpers
from google.cloud import storage

"""
EXAMPLE HOW TO RUN
---------------------
python .\gcs_selective_upload.py --source ./<source-folder> --match-regex "^(.)+/subfolder1/(.)+/(.)+/subfolder2/(.)+.html" --gcs <gcs-bucket-name>

"""

# current version
VERSION = '0.0.2'

def main():
	# parameter
	parser = argparse.ArgumentParser(
		description=('Directory walker to iterate directories, subdirectories, and files. (c) 2018 Aditya Satrya.'),
		prog='{0}'.format(os.path.basename(sys.argv[0])))
	parser.add_argument('--version', action='version',
					version='%(prog)s v.' + VERSION)
	parser.add_argument('--source', metavar="source DIR", dest='source', default="./source",
					help=("The source directory to begin the iteration. Default: current directory"))
	parser.add_argument('--temp-dir', metavar="TEMP DIR", dest='temp_dir', default="./temp",
					help=("Temporary directory to copy or download the files. Default: current directory"))
	parser.add_argument('--output-dir', metavar="OUTPUT DIR", dest='output_dir', default="./output",
					help=("Output  directory to copy or download the files. Default: current directory"))
	parser.add_argument('--match-regex', metavar="Match Regex", dest='match_regex', default="(.)+",
					help=("Regex to match the full path of the files. Default: '(.)+'"))
	parser.add_argument('--gcs-upload-bucket', metavar="GCS UPLOAD BUCKET", dest='gcs_upload_bucket', default=None,
					help=("Google Cloud Storage bucket name where the files will be uploaded to.  Default - not uploading to GCS"))
	parser.add_argument('--process', metavar="PROCESS", dest='process', default='copy',
					help=("User defined file process. Defined as a .py file name with 'process_file' function in it. Default: copy"))
	args = parser.parse_args()

	# main code
	sourceDir = file_helpers.remove_trailing_slash(args.source.replace("\\", "/"))
	tempDir = file_helpers.remove_trailing_slash(args.temp_dir.replace("\\", "/"))
	outputDir = file_helpers.remove_trailing_slash(args.output_dir.replace("\\", "/"))
	matchRegex = args.match_regex.decode('string_escape')

	# source is on GCS
	if(re.match("^gs://(.+)", sourceDir)):
		sourceDirSegment = sourceDir.replace("gs://", "").split("/")
		bucket_name = sourceDirSegment[0]

		# remove "gs://<bucket-name>/" or "gs://<bucket-name>" in the beginning
		prefix = sourceDir.replace("gs://" + bucket_name + "/", "").replace("gs://" + bucket_name, "")

		bucket = storage.Client().get_bucket(bucket_name)
		for blob in bucket.list_blobs(prefix=prefix):
			
			blob.name = blob.name.replace("\\", "/")

			# only process files that match to the regex
			if(re.match(matchRegex, blob.name)):

				print("Read {}".format(blob.name))

				# download to TEMP DIRECTORY
				tempFileFullPath = file_helpers.join_path_segment("/", tempDir, blob.name.replace(prefix, ""))
				tempDirFullPath = tempFileFullPath[:tempFileFullPath.rfind('/')]
				if not os.path.exists(tempDirFullPath):
					os.makedirs(tempDirFullPath)
				
				gcs_helpers.download_blob(bucket_name, blob.name, tempFileFullPath)

				# process and write to output directory
				outputFileFullPath = file_helpers.join_path_segment("/", outputDir, blob.name.replace(prefix, ""))
				outputDirFullPath = outputFileFullPath[:outputFileFullPath.rfind('/')]
				if not os.path.exists(outputDirFullPath):
					os.makedirs(outputDirFullPath)
				
				process_output_file = eval('{}.process_file("{}", "{}")'.format(args.process, tempFileFullPath, outputDirFullPath))
				print("\tWritten to {}".format(process_output_file))

				# next: upload to GCS
				if(args.gcs_upload_bucket is not None):
					blob_name = file_helpers.remove_leading_slash(process_output_file.replace("//", "/").replace(outputDir, ""))
					gcs_helpers.upload_blob(args.gcs_upload_bucket, process_output_file, blob_name)

	# source is on filesystem
	else:
		for dirName, subdirList, fileList in os.walk(sourceDir):
			for fname in fileList:
				fullPathFileName = os.path.join(dirName, fname).replace("\\", "/")
				
				# only process files that match to the regex
				if(re.match(matchRegex, fullPathFileName)):

					print("Read {}".format(fullPathFileName))

					# process and write to output directory
					outputFileFullPath = file_helpers.join_path_segment("/", outputDir, fullPathFileName.replace(sourceDir, ""))
					outputDirFullPath = outputFileFullPath[:outputFileFullPath.rfind('/')]
					if not os.path.exists(outputDirFullPath):
						os.makedirs(outputDirFullPath)
						
					process_output_file = eval('{}.process_file("{}", "{}")'.format(args.process, fullPathFileName, outputDirFullPath))
					print("\tWrite to {}".format(process_output_file))

					# next: upload to GCS

if __name__ == '__main__':
	sys.exit(main())