import sys
import os
import argparse
import re

from google.cloud import storage

"""
EXAMPLE HOW TO RUN
---------------------
python .\gcs_selective_upload.py --root ./<root-folder> --match-regex "^(.)+/subfolder1/(.)+/(.)+/subfolder2/(.)+.html" --gcs <gcs-bucket-name>

"""

# current version
VERSION = '0.0.1'

def upload_blob(bucket_name, source_file_name, destination_blob_name):
	"""Uploads a file to the bucket."""
	storage_client = storage.Client()
	bucket = storage_client.get_bucket(bucket_name)
	blob = bucket.blob(destination_blob_name)

	print("Uploading...")
	blob.upload_from_filename(source_file_name)
	print('Uploaded to {}.'.format(destination_blob_name))

def main():
	# command line
	parser = argparse.ArgumentParser(
		description=('Directory walker to iterate directories, subdirectories, and files. (c) 2018 Aditya Satrya.'),
		prog='{0}'.format(os.path.basename(sys.argv[0])))
	parser.add_argument('--version', action='version',
					version='%(prog)s v.' + VERSION)
	parser.add_argument('--root', metavar="ROOT DIR", dest='root', default=".",
					help=("The root directory to begin the iteration. Default: current directory"))
	parser.add_argument('--match-regex', metavar="Match Regex", dest='match_regex', default="(.)+",
					help=("Regex to match the full path of the files. Default: '(.)+'"))
	parser.add_argument('--gcs', metavar="GCS", dest='gcs_bucket_name', default=None,
					help=("upload to Google Cloud Storage.  Default - not uploading "
							"to GCS"))
	args = parser.parse_args()

	# main code
	rootDir = args.root
	matchRegex = args.match_regex.decode('string_escape')
	for dirName, subdirList, fileList in os.walk(rootDir):
		for fname in fileList:
			fullPathFileName = os.path.join(dirName, fname).replace("\\", "/")
			if(re.match(matchRegex, fullPathFileName)):
				print("Read {}".format(fullPathFileName))
				if args.gcs_bucket_name is not None:
					upload_blob(args.gcs_bucket_name, fullPathFileName, fullPathFileName.replace("../", ""))

if __name__ == '__main__':
	sys.exit(main())