import sys
import os
import xlrd
import re
import collections
import csv
import pandas as pd
import numpy as np

from shutil import copyfile
from utils import file_helpers

Coordinate = collections.namedtuple("Coordinate", ["row", "col"])
Range = collections.namedtuple("Range", ["topleft", "rightbottom"])
Cell = collections.namedtuple("Cell", ["coordinate", "cell_obj"])

def is_cell_empty(sheet, coordinate):
	if(sheet.cell(coordinate.row, coordinate.col) == xlrd.empty_cell.value 
			or re.match("^[ \t]*$", str(sheet.cell(coordinate.row, coordinate.col).value))):
		return True
	else:
		return False

def is_in_sheet_range(sheet, coordinate):
	if(coordinate.row >= 0  and coordinate.row < sheet.nrows and coordinate.col >= 0 and coordinate.col < sheet.ncols):
		return True
	else:
		return False

def get_topleft_nonempty_cell(sheet):
	for row_idx in range(0, sheet.nrows):
		row = sheet.row(row_idx)
		for col_idx, cell_obj in enumerate(row):
			if(cell_obj.value != xlrd.empty_cell.value):
				return Cell(coordinate=Coordinate(row=row_idx, col=col_idx),
						cell_obj=sheet.cell(row_idx, col_idx))
	return None

def get_lefttop_nonempty_cell(sheet):
	for col_idx in range(0, sheet.ncols):
		col = sheet.col(col_idx)
		for row_idx, cell_obj in enumerate(col):
			if(cell_obj.value != xlrd.empty_cell.value):
				return Cell(coordinate=Coordinate(row=row_idx, col=col_idx),
						cell_obj=sheet.cell(row_idx, col_idx))
	return None

def get_bottomright_nonempty_cell(sheet):
	for row_idx in range(sheet.nrows-1, 0, -1):
		row = sheet.row(row_idx)
		last_col_idx = 0
		for col_idx, cell_obj in enumerate(row):
			if(not is_cell_empty(sheet, Coordinate(row=row_idx, col=col_idx))):
				last_col_idx = col_idx
		return Cell(coordinate=Coordinate(row=row_idx, col=last_col_idx),
						cell_obj=sheet.cell(row_idx, last_col_idx))
	return None

def get_vconsecutive_nonempty_cells(sheet, top_coordinate, direction="south"):
	cur_row_idx = top_coordinate.row
	cur_col_idx = top_coordinate.col
	col_vals = []
	while sheet.cell(cur_row_idx, cur_col_idx).value != xlrd.empty_cell.value and cur_row_idx <= sheet.nrows:
		if(direction == 'south'):
			col_vals.append(Cell(coordinate=Coordinate(row=cur_row_idx, col=cur_col_idx), cell_obj=sheet.cell(cur_row_idx, cur_col_idx)))
			cur_row_idx += 1
		else:
			col_vals.insert(0, Cell(coordinate=Coordinate(row=cur_row_idx, col=cur_col_idx), cell_obj=sheet.cell(cur_row_idx, cur_col_idx)))
			cur_row_idx -= 1
	return col_vals

def get_hconsecutive_nonempty_cells(sheet, left_coordinate):
	cur_row_idx = left_coordinate.row
	cur_col_idx = left_coordinate.col
	row_vals = []
	while sheet.cell(cur_row_idx, cur_col_idx).value != xlrd.empty_cell.value and cur_col_idx <= sheet.ncols:
		row_vals.append(Cell(coordinate=Coordinate(row=cur_row_idx, col=cur_col_idx), cell_obj=sheet.cell(cur_row_idx, cur_col_idx)))
		cur_col_idx += 1
	return row_vals

def get_match_cells(sheet, cell_range, regex):
	col_vals = []
	for cur_row_idx in range(cell_range.topleft.row, cell_range.rightbottom.row + 1):
		for cur_col_idx in range(cell_range.topleft.col, cell_range.rightbottom.col + 1):
			if(re.match(regex, str(sheet.cell(cur_row_idx, cur_col_idx).value))):
				col_vals.append(Cell(coordinate=Coordinate(row=cur_row_idx, col=cur_col_idx), cell_obj=sheet.cell(cur_row_idx, cur_col_idx)))
	return col_vals

def get_range_cells(sheet, cell_range):
	return get_match_cells(sheet, cell_range, "")

def get_row_width(sheet, left_coordinate):
	width = 0
	candidate_width = 0
	for cur_col_idx in range(left_coordinate.col, sheet.ncols):
		candidate_width += 1
		if(not is_cell_empty(sheet, Coordinate(row=left_coordinate.row, col=cur_col_idx))):
			width = candidate_width
	return width

def hmove(coordinate, steps):
	return Coordinate(row=coordinate.row, col=coordinate.col + steps)

def vmove(coordinate, steps):
	return Coordinate(row=coordinate.row + steps, col=coordinate.col)

def find_first_nonempty_cell_from(sheet, coordinate, direction):
	while is_cell_empty(sheet, coordinate) and is_in_sheet_range(sheet, coordinate):
		if(direction == 'north'):
			coordinate = vmove(coordinate, -1)
		elif(direction == 'south'):
			coordinate = vmove(coordinate, 1)
		elif(direction == 'west'):
			coordinate = hmove(coordinate, -1)
		elif(direction == 'east'):
			coordinate = hmove(coordinate, 1)
	if(is_cell_empty(sheet, coordinate)):
		return None
	else:
		return Cell(coordinate, sheet.cell(coordinate.row, coordinate.col))

def build_matrix(sheet, cell_range):
	rows = []
	for row_idx in range(cell_range.topleft.row, cell_range.rightbottom.row + 1):
		cols = []
		for col_idx in range(cell_range.topleft.col, cell_range.rightbottom.col + 1):
			cols.append(sheet.cell(row_idx, col_idx).value)
		rows.append(cols)
	return rows

def pd_convert_first_row_as_header(df):
	new_header = df.iloc[0]
	df = df[1:]
	df.columns = new_header
	return df

def process_file(process_counter, args_tuple, source_file, target_dir):
	if not os.path.exists(target_dir):
		os.makedirs(target_dir)

	# [BEGIN]
	workbook = xlrd.open_workbook(source_file, on_demand = True)
	try:
		sheet_model_da = workbook.sheet_by_name("Model DA")
	except xlrd.XLRDError as e:
		if(workbook.nsheets >= 2):
			sheet_model_da = workbook.sheet_by_index(1)
		else:
			sheet_model_da = workbook.sheet_by_index(0)

	# --------------------------------------------------------------------------------------------
	# TOP LEFTs
	# --------------------------------------------------------------------------------------------
	lefttop = get_lefttop_nonempty_cell(sheet_model_da)
	leftmost_col_idx = lefttop.coordinate.col
	first_col_range = Range(
			topleft=Coordinate(row=0, col=leftmost_col_idx), 
			rightbottom=Coordinate(row=sheet_model_da.nrows-1, col=leftmost_col_idx))
	# table I
	table_i_topleft_cells = get_match_cells(sheet_model_da, first_col_range, "^[ \t]*I[ \t]*\.[ \t]*$")
	# table II
	table_ii_topleft_cells = get_match_cells(sheet_model_da, first_col_range, "^[ \t]*II[ \t]*\.[ \t]*$")
	# table III
	table_iii_topleft_cells = get_match_cells(sheet_model_da, first_col_range, "^[ \t]*III[ \t]*\.[ \t]*$")
	# table partai
	table_partai_topleft_cells = get_match_cells(sheet_model_da, first_col_range, "^[ \t]*[Nn][Oo](.*)[Uu][Rr][Uu][Tt][ \t]*$")

	# --------------------------------------------------------------------------------------------
	# BOTTOM RIGHTs
	# --------------------------------------------------------------------------------------------
	table_i_widths = [None] * len(table_i_topleft_cells)
	table_ii_widths = [None] * len(table_ii_topleft_cells)
	table_iii_widths = [None] * len(table_iii_topleft_cells)
	table_partai_widths = [None] * len(table_partai_topleft_cells)
	table_i_bottomright_coordinates = [None] * len(table_i_topleft_cells)
	table_ii_bottomright_coordinates = [None] * len(table_ii_topleft_cells)
	table_iii_bottomright_coordinates = [None] * len(table_iii_topleft_cells)
	table_partai_bottomright_coordinates = [None] * len(table_partai_topleft_cells)

	for collection_idx in range(0, len(table_i_topleft_cells)):
		# table I
		table_i_widths[collection_idx] = get_row_width(sheet_model_da, table_i_topleft_cells[collection_idx].coordinate)
		table_i_bottomright_coordinates[collection_idx] = hmove(vmove(table_ii_topleft_cells[collection_idx].coordinate, -2), table_i_widths[collection_idx] - 1)
		# table II
		table_ii_widths[collection_idx] = get_row_width(sheet_model_da, table_ii_topleft_cells[collection_idx].coordinate)
		table_ii_bottomright_coordinates[collection_idx] = hmove(vmove(table_iii_topleft_cells[collection_idx].coordinate, -1), table_ii_widths[collection_idx] - 1)
		# table III
		table_iii_widths[collection_idx] = get_row_width(sheet_model_da, table_iii_topleft_cells[collection_idx].coordinate)
		table_iii_bottomright_coordinates[collection_idx] = hmove(vmove(table_partai_topleft_cells[collection_idx].coordinate, -1), table_iii_widths[collection_idx] - 1)
		# table partai
		table_partai_widths[collection_idx] = get_row_width(sheet_model_da, table_partai_topleft_cells[collection_idx].coordinate)
		if(collection_idx + 1 <= len(table_i_topleft_cells) - 1):
			table_partai_bottomright_coordinates[collection_idx] = hmove(vmove(table_i_topleft_cells[collection_idx+1].coordinate, -2), table_partai_widths[collection_idx] - 1)
		else:
			table_partai_bottomright_coordinates[collection_idx] = get_bottomright_nonempty_cell(sheet_model_da).coordinate

	# --------------------------------------------------------------------------------------------
	# RANGEs
	# --------------------------------------------------------------------------------------------
	table_i_ranges = [None] * len(table_i_topleft_cells)
	table_ii_ranges = [None] * len(table_ii_topleft_cells)
	table_iii_ranges = [None] * len(table_iii_topleft_cells)
	table_partai_ranges = [None] * len(table_partai_topleft_cells)

	for collection_idx in range(0, len(table_i_topleft_cells)):
		# table I
		table_i_ranges[collection_idx] = Range(topleft=table_i_topleft_cells[collection_idx].coordinate, rightbottom=table_i_bottomright_coordinates[collection_idx])
		# table II
		table_ii_ranges[collection_idx] = Range(topleft=table_ii_topleft_cells[collection_idx].coordinate, rightbottom=table_ii_bottomright_coordinates[collection_idx])
		# table III
		table_iii_ranges[collection_idx] = Range(topleft=table_iii_topleft_cells[collection_idx].coordinate, rightbottom=table_iii_bottomright_coordinates[collection_idx])
		# table partai
		table_partai_ranges[collection_idx] = Range(topleft=table_partai_topleft_cells[collection_idx].coordinate, rightbottom=table_partai_bottomright_coordinates[collection_idx])

		# print "[{}] table_i; range={}".format(collection_idx, table_i_ranges[collection_idx])
		# print "[{}] table_ii; range={}".format(collection_idx, table_ii_ranges[collection_idx])
		# print "[{}] table_iii; range={}".format(collection_idx, table_iii_ranges[collection_idx])
		# print "[{}] table_partai; range={}".format(collection_idx, table_partai_ranges[collection_idx])

	# --------------------------------------------------------------------------------------------
	# LIST KECAMATAN
	# --------------------------------------------------------------------------------------------
	if(len(table_i_topleft_cells) > 0):
		topleft = find_first_nonempty_cell_from(sheet_model_da, vmove(hmove(table_i_topleft_cells[0].coordinate, 1), -2), "north")
		kecamatan_list = get_vconsecutive_nonempty_cells(sheet_model_da, topleft.coordinate, "north")
	else:
		kecamatan_list = []

	# --------------------------------------------------------------------------------------------
	# TABLEs / DATAFRAMEs
	# --------------------------------------------------------------------------------------------
	table_i_df = [None] * len(table_i_topleft_cells)
	table_ii_df = [None] * len(table_ii_topleft_cells)
	table_iii_df = [None] * len(table_iii_topleft_cells)
	table_partai_df = [None] * len(table_partai_topleft_cells)

	table_i_appended = pd.DataFrame()
	for kecamatan_idx in range(0, len(kecamatan_list)):
		if(kecamatan_idx > len(table_i_topleft_cells) - 1):
			continue

		# table I 
		df = table_i_df[kecamatan_idx]
		df = pd.DataFrame.from_records(build_matrix(sheet_model_da, table_i_ranges[kecamatan_idx])) \
				.replace("^[ \t]*$", np.nan, regex=True) \
				.dropna(how='all', axis='index') \
				.fillna(method='ffill') \
				.fillna('x')
		df = pd_convert_first_row_as_header(df)
		df = df.loc[df['Data Pemilih dan Pengguna Hak Pilih'].str.contains('[ ]*5\.[ ]+', na=False, regex=True)] \
				.loc[df['x'].str.contains('JML', na=False)] \
				.set_index(df.columns[1]) \
				.drop(['x', df.columns[0], df.columns[len(df.columns)-1]], axis=1) \
				.transpose() \
				.rename_axis('kelurahan')
		df.columns = ['jumlah_pemilih', 'jumlah_pengguna_hak_pilih']
		df['kecamatan'] = kecamatan_list[kecamatan_idx].cell_obj.value
		df['file'] = source_file
		df = df[['file', 'kecamatan', 'jumlah_pemilih', 'jumlah_pengguna_hak_pilih']]
		table_i_appended = table_i_appended.append(df)
		table_i_df[kecamatan_idx] = df
		
		# table II
		table_ii_df[kecamatan_idx] = pd.DataFrame.from_records(build_matrix(sheet_model_da, table_ii_ranges[kecamatan_idx])).replace("^[ \t]*$", np.nan, regex=True).dropna(how='all', axis='index').fillna(method='ffill')
		# table III
		table_iii_df[kecamatan_idx] = pd.DataFrame.from_records(build_matrix(sheet_model_da, table_iii_ranges[kecamatan_idx])).replace("^[ \t]*$", np.nan, regex=True).dropna(how='all', axis='index').fillna(method='ffill')
		# table partai
		table_partai_df[kecamatan_idx] = pd.DataFrame.from_records(build_matrix(sheet_model_da, table_partai_ranges[kecamatan_idx])).replace("^[ \t]*$", np.nan, regex=True).dropna(how='any', axis='index').fillna(method='ffill')

	if not os.path.exists(target_dir):
		os.makedirs(target_dir)
	
	table_i_csv_filename = source_file[source_file.rfind('/'):]+".table_i.csv"
	table_i_appended.to_csv(file_helpers.join_path_segment("/", target_dir, table_i_csv_filename))
	print "\tSaved CSV to {}".format(file_helpers.join_path_segment("/", target_dir, table_i_csv_filename))

	# [END]

	target_file = file_helpers.join_path_segment("/", args_tuple.output_dir, "data_quality.csv")
	print "\tSaved CSV to {}".format(target_file)

	if(process_counter == 0):
		open_file_mode = 'wb'
	else:
		open_file_mode = 'ab'

	with open(target_file, open_file_mode) as csvfile:
		filewriter = csv.writer(csvfile)
		if(process_counter == 0):
			filewriter.writerow(['File', 'Jumlah Sheet', 'Jumlah Kecamatan', 'Jumlah Table I', 'Jumlah Table II', 'Jumlah Table III', 'Jumlah Table Partai'])
		filewriter.writerow([source_file, workbook.nsheets, len(kecamatan_list), len(table_i_topleft_cells), len(table_ii_topleft_cells), len(table_iii_topleft_cells), len(table_partai_topleft_cells)])

	return target_file

if __name__ == '__main__':
	# sys.exit(process_file('../../dataset-pemilu2014/Kalimantan/KALTIM/Perolehan Suara DPR RI/Kutai Kertanegara.xlsx', './output'))
	exit()