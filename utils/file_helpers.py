def remove_leading_slash(str):
	if(str[0] == '/'):
		return str[1:]
	else:
		return str

def remove_trailing_slash(str):
	if(str[(len(str)-1)] == '/'):
		return str[:len(str)-1]
	else:
		return str

def join_path_segment(separator, segment1, segment2):
	return remove_trailing_slash(segment1) + separator + remove_leading_slash(segment2)

def get_filename_from_path(path):
	return path[path.rfind('/'):]