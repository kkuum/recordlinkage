from __future__ import division

import pandas as pd
import numpy as np

def _fullindex(A, B):

	# merge_col is used to make a full index.
	A_merge = pd.DataFrame({'merge_col':1, A.index.name: A.index.values})
	B_merge = pd.DataFrame({'merge_col':1, B.index.name: B.index.values})

	pairs = A_merge.merge(B_merge, how='inner', on='merge_col').set_index([A.index.name, B.index.name])

	return pairs.index

def _blockindex(A, B, on=None, left_on=None, right_on=None):

	if on:
		left_on, right_on = on, on

	pairs = A[left_on].reset_index().merge(B[right_on].reset_index(), how='inner', left_on=left_on, right_on=right_on).set_index([A.index.name, B.index.name])

	return pairs.index

def _sortedneighbourhood(A, B, column, window=3, sorted_index=None, on=[], left_on=[], right_on=[]):

	factors = np.sort(np.unique(np.append(A[column].values, B[column].values)))
	factors = factors[~np.isnan(factors)] # Remove possible np.nan values. They are not replaced in the next step.
	factors_label = np.arange(len(factors))

	sorted_df_A = pd.DataFrame({column:A[column].replace(factors, factors_label), A.index.name: A.index.values})
	sorted_df_B = pd.DataFrame({column:B[column].replace(factors, factors_label), B.index.name: B.index.values})

	pairs_concat = None

	for w in range(-window, window+1):

		pairs = sorted_df_A.merge(pd.DataFrame({column:sorted_df_B[column]+w, B.index.name: B.index.values}), on=column, how='inner').set_index([A.index.name, B.index.name])

		# Append pairs to existing ones. PANDAS BUG workaround
		pairs_concat = pairs.index if pairs_concat is None else pairs.index.append(pairs_concat)

	return pairs_concat

class Pairs(object):
	""" Pairs class is used to make pairs of records to analyse in the comparison step. """	

	def __init__(self, dataframe_A, dataframe_B=None):

		self.A = dataframe_A

		# Linking two datasets
		if dataframe_B is not None:

			self.B = dataframe_B
			self.deduplication = False

			if self.A.index.name == None or self.B.index.name == None:
				raise ValueError('Specify an index name for each file.')

			if self.A.index.name == self.B.index.name:
				raise ValueError('ValueError: Overlapping index names %s.' % self.A.index.name)

			if not self.A.index.is_unique or not self.B.index.is_unique:
				raise ValueError('The given dataframe has not a unique index.')

		# Deduplication of one dataset
		else:
			self.deduplication = True

			if self.A.index.name == None:
				raise ValueError('Specify an index name.')

			if not self.A.index.is_unique:
				raise ValueError('The given dataframe has not a unique index.')

		self.n_pairs = 0

	def index(self, index_func, *args, **kwargs):
		""" Create an index. 

		:return: MultiIndex
		:rtype: pandas.MultiIndex
		"""	

		# If not deduplication, make pairs of records with one record from the first dataset and one of the second dataset
		if not self.deduplication:

			pairs = index_func(self.A, self.B, *args, **kwargs)

		# If deduplication, remove the record pairs that are already included. For example: (a1, a1), (a1, a2), (a2, a1), (a2, a2) results in (a1, a2) or (a2, a1)
		elif self.deduplication:

			B = self.A.copy()
			B.index.name = str(self.A.index.name) + '_'

			pairs = index_func(self.A, B, *args, **kwargs)

			factorize_index_level_values = pd.factorize(
				list(pairs.get_level_values(self.A.index.name)) + list(pairs.get_level_values(B.index.name))
				)[0]

			dedupe_index_boolean = factorize_index_level_values[:len(factorize_index_level_values)/2] < factorize_index_level_values[len(factorize_index_level_values)/2:]

			pairs = pairs[dedupe_index_boolean]

		return pairs

	def block(self, *args, **kwargs):
		"""Return a blocking index. 

		:param columns: A column name or a list of column names. These columns are used to block on. 

		:return: A DataFrame with MultiIndex
		:rtype: standardise.DataFrame
		"""		
		return self.index(_blockindex, *args, **kwargs)

	def full(self, *args, **kwargs):
		"""Return a Full index. In case of linking two dataframes of length N and M, the number of pairs is N*M. In case of deduplicating a dataframe with N records, the number of pairs is N*(N-1)/2. 

		:return: A DataFrame with MultiIndex
		:rtype: standardise.DataFrame
		"""
		return self.index(_fullindex, *args, **kwargs)

	def sortedneighbourhood(self, *args, **kwargs):
		"""Return a Sorted Neighbourhood index.  

		:param column: Specify the column to make a sorted index. 
		:param window: The width of the window, default is 3. 
		:param suffixes: The suffixes to extend the column names with. 
		:param blocking_on: Additional columns to use standard blocking on. 
		:param left_blocking_on: Additional columns in the left dataframe to use standard blocking on. 
		:param right_blocking_on: Additional columns in the right dataframe to use standard blocking on. 

		:return: A DataFrame with MultiIndex
		:rtype: standardise.DataFrame
		"""
		return self.index(_sortedneighbourhood, *args, **kwargs)

	def iterblock(self, *args, **kwargs):
		"""Iterative function that returns a part of a blocking index.

		:param len_block_A: The lenght of a block of records in dataframe A. 
		:param len_block_B: The length of a block of records in dataframe B.
		:param columns: A column name or a list of column names. These columns are used to block on. 

		:return: A DataFrame with MultiIndex
		:rtype: standardise.DataFrame
		"""		
		return self.iterindex(_blockindex, *args, **kwargs)

	def iterfull(self, *args, **kwargs):
		"""Iterative function that returns a part of a full index. 

		:param len_block_A: The lenght of a block of records in dataframe A. 
		:param len_block_B: The length of a block of records in dataframe B.
		:return: A DataFrame with MultiIndex
		:rtype: standardise.DataFrame
		"""
		return self.iterindex(_fullindex, *args, **kwargs)

	def itersortedneighbourhood(self, *args, **kwargs):
		"""Iterative function that returns a records pairs based on a sorted neighbourhood index. The number of iterations can be adjusted to prevent memory problems.  

		:param len_block_A: The lenght of a block of records in dataframe A. 
		:param len_block_B: The length of a block of records in dataframe B.
		:param column: Specify the column to make a sorted index. 
		:param window: The width of the window, default is 3. 
		:param suffixes: The suffixes to extend the column names with. 
		:param blocking_on: Additional columns to use standard blocking on. 
		:param left_blocking_on: Additional columns in the left dataframe to use standard blocking on. 
		:param right_blocking_on: Additional columns in the right dataframe to use standard blocking on. 

		:return: A DataFrame with MultiIndex
		:rtype: standardise.DataFrame
		"""
		return self.iterindex(_sortedneighbourhood, *args, **kwargs)

	def iterindex(self, index_func, len_block_A, len_block_B, *args, **kwargs):
		"""Iterative function that returns records pairs based on a user-defined indexing function. The number of iterations can be adjusted to prevent memory problems.  

		:param index_func: A user defined indexing funtion.
		:param len_block_A: The lenght of a block of records in dataframe A. 
		:param len_block_B: The length of a block of records in dataframe B.

		:return: A DataFrame with MultiIndex
		:rtype: standardise.DataFrame
		"""
		if self.deduplication:
			A = self.A.copy()
			A['dedupe_col'] = A.reset_index().index.values
			B = A.copy()
		else:
			A = self.A
			B = self.B

		if len_block_A is None:
			len_block_A = len(A)
		elif len_block_B is None:
			len_block_B = len(B)
		else:
			pass

		blocks = [(x,y) for x in np.arange(0, len(A), len_block_A) for y in np.arange(0, len(B), len_block_B) ]

		for bl in blocks:

			pairs_subset_class = Pairs(A[bl[0]:(bl[0]+len_block_A)].copy(), B[bl[1]:(bl[1]+len_block_B)].copy(), suffixes=self.suffixes)
			pairs_subset = pairs_subset_class.index(index_func, *args, **kwargs)

			if self.deduplication:
				pairs_subset = pairs_subset[pairs_subset['dedupe_col' + self.suffixes[0]]<pairs_subset['dedupe_col' + self.suffixes[1]]]
				del pairs_subset['dedupe_col' + self.suffixes[0]]
				del pairs_subset['dedupe_col' + self.suffixes[1]]

			yield pairs_subset

	def reduction_ratio(self):
		""" Compute the relative reduction of records pairs as the result of indexing. 

		:return: Value between 0 and 1
		:rtype: float
		"""

		n_full_pairs = (len(self.A)*(len(self.B)-1))/2 if self.deduplication else len(self.A)*len(self.B)

		return 1-self.n_pairs/n_full_pairs

