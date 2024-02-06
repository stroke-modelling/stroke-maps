"""
Combine features from multiple runs.

Welcome to MultiIndex hell. *Doom trumpets*

TO DO - write me --------------------------------------------------------------------
"""
import numpy as np
import pandas as pd
import os
from itertools import combinations

from classes.setup import Setup


class Combine(object):
    """
    Combine files from multiple runs of the pathway.

    class Combine():

    TO DO - write me
    """
    def __init__(self, *initial_data, **kwargs):

        # Overwrite default values
        # (can take named arguments or a dictionary)
        for dictionary in initial_data:
            for key in dictionary:
                setattr(self, key, dictionary[key])

        for key in kwargs:
            setattr(self, key, kwargs[key])

        # If no setup was given, create one now:
        try:
            self.setup
        except AttributeError:
            self.setup = Setup()

    def combine_files(self):
        self.combine_selected_units()
        self.combine_selected_lsoa()
        self.combine_selected_regions()
        self.combine_results_summary_by_lsoa()
        self.combine_results_summary_by_admitting_unit()

    # ##########################
    # ##### SPECIFIC FILES #####
    # ##########################

    def combine_selected_units(self, save_to_file=True):
        """
        Combine selected units.

        Each file input:
        +------+-----+---------------+-----------------+
        | Unit | ... | transfer_unit | transfer_coords |
        +------+-----+---------------+-----------------+
        |    1 | ... |             2 |  -x.xx, yy.yy   |
        |    2 | ... |             2 |  -x.xx, yy.yy   |
        |    3 | ... |             2 |  -x.xx, yy.yy   |
        |  ... | ... |           ... |       ...       |
        |    n | ... |             4 |  -x.xx, yy.yy   |
        +------+-----+---------------+-----------------+

        Resulting DataFrame:
                     +---------------------+---------------------+
                     |     scenario_1      |     scenario_2      |
        +------+-----+-----+---------------+-----+---------------+
        | Unit | ... | Use | transfer unit | Use | transfer unit |
        +------+-----+-----+---------------+-----+---------------+
        |    1 | ... |   1 |             2 |   0 |               |
        |    2 | ... |   1 |             2 |   0 |               |
        |    3 | ... |   1 |             2 |   1 |             4 |
        |  ... | ... | ... |           ... | ... |           ... |
        |    n | ... |   0 |               |   1 |             4 |
        +------+-----+-----+---------------+-----+---------------+
        """
        file_to_merge = self.setup.file_selected_stroke_units

        try:
            df = self._hstack_multiple_dataframes(file_to_merge)
        except FileNotFoundError:
            # TO DO - set up proper error message ----------------------------------
            pass

        # Columns shared between all scenarios:
        # Postcode	Hospital_name	SSNAP name	ICB22NM	Easting	Northing	long	lat
        # TO DO - change these to "any" Index. --------------------------------------------

        if save_to_file:
            output_dir = self.setup.dir_output_all_runs
            output_filename = self.setup.file_combined_selected_stroke_units
            path_to_file = os.path.join(output_dir, output_filename)
            df.to_csv(path_to_file, index=False)

    def combine_selected_lsoa(self, save_to_file=True):
        """
        Combine selected LSOA.

        Each file input:
        +------+-----+
        | LSOA | ... |
        +------+-----+
        |    1 | ... |
        |    2 | ... |
        |    3 | ... |
        |  ... | ... |
        |    n | ... |
        +------+-----+

        Resulting DataFrame:
        +------+-----+------------+------------+
        | LSOA | ... | scenario_1 | scenario_2 |
        +------+-----+------------+------------+
        |    1 | ... |       True |      False |
        |    2 | ... |       True |      False |
        |    3 | ... |       True |       True |
        |  ... | ... |        ... |        ... |
        |    n | ... |      False |       True |
        +------+-----+------------+------------+
        """
        file_to_merge = self.setup.file_selected_lsoas

        try:
            df = self._merge_multiple_dataframes(file_to_merge)
        except FileNotFoundError:
            # TO DO - set up proper error message ----------------------------------
            pass

        if save_to_file:
            output_dir = self.setup.dir_output_all_runs
            output_filename = self.setup.file_combined_selected_lsoas
            path_to_file = os.path.join(output_dir, output_filename)
            df.to_csv(path_to_file, index=False)

    def combine_selected_regions(self, save_to_file=True):
        """
        Combine selected regions.

        Each file input:
        +--------+-----------+----------+
        | Region | has_units | has_lsoa |
        +--------+-----------+----------+
        |      1 |      True |     True |
        |      2 |      True |     True |
        |      3 |     False |     True |
        |    ... |       ... |      ... |
        |      n |     False |     True |
        +--------+-----------+----------+

        Resulting DataFrame:
                 +----------------------+----------------------+
                 |      scenario_1      |      scenario_2      |
        +--------+-----------+----------+-----------+----------+
        | Region | has_units | has_lsoa | has_units | has_lsoa |
        +--------+-----------+----------+-----------+----------+
        |      1 |      True |     True |      True |     True |
        |      2 |      True |     True |     False |     True |
        |      3 |     False |     True |      True |     True |
        |    ... |       ... |      ... |       ... |      ... |
        |      n |     False |     True |     False |     True |
        +--------+-----------+----------+-----------+----------+
        """
        file_to_merge = self.setup.file_selected_regions

        try:
            df = self._hstack_multiple_dataframes(file_to_merge)
        except FileNotFoundError:
            # TO DO - set up proper error message ----------------------------------
            pass

        if save_to_file:
            output_dir = self.setup.dir_output_all_runs
            output_filename = self.setup.file_combined_selected_regions
            path_to_file = os.path.join(output_dir, output_filename)
            df.to_csv(path_to_file, index=False)

    def combine_results_summary_by_lsoa(self, save_to_file=True):
        """
        Group by LSOA summary.

        Each file input:
        +------+-------------+-------------+
        |      |   time_1    |    shift_1  |
        +------+------+------+------+------+
        | LSOA | mean |  std | mean |  std |
        +------+------+------+------+------+
        |    1 | x.xx | x.xx | y.yy | y.yy |
        |    2 | x.xx | x.xx | y.yy | y.yy |
        |    3 | x.xx | x.xx | y.yy | y.yy |
        |  ... |  ... |  ... |  ... |  ... |
        |    n | x.xx | x.xx | y.yy | y.yy |
        +------+------+------+------+------+

        Resulting DataFrame:
        +------+------+------+------+------+------+------+
        |      |  scenario_1 |  scenario_2 |    diff     |
        +------+------+------+------+------+------+------+
        |      |    shift    |    shift    |    shift    |
        +------+------+------+------+------+------+------+
        | LSOA | mean |  std | mean |  std | mean |  std |
        +------+------+------+------+------+------+------+
        |    1 | x.xx | x.xx | y.yy | y.yy | z.zz | z.zz |
        |    2 | x.xx | x.xx | y.yy | y.yy | z.zz | z.zz |
        |    3 | x.xx | x.xx | y.yy | y.yy | z.zz | z.zz |
        |  ... |  ... |  ... |  ... |  ... |  ... |  ... |
        |    n | x.xx | x.xx | y.yy | y.yy | z.zz | z.zz |
        +------+------+------+------+------+------+------+
        """
        file_to_merge = self.setup.file_results_summary_by_lsoa

        try:
            data = self._hstack_multiple_dataframes(
                file_to_merge, csv_header=[0, 1])
        except FileNotFoundError:
            # TO DO - set up proper error message ----------------------------------
            pass

        # col_to_group = data.columns[0]
        cols_to_keep = ['utility_shift', 'mRS shift', 'mRS 0-2']
        # Same LSOA appearing in multiple files will currently have
        # multiple mostly-empty rows in the "data" DataFrame.
        # Group matching rows:
        # df = self._group_data(data, col_to_group, cols_to_keep)

        # Create new columns of this diff that:
        df = self._diff_data(data, cols_to_keep)

        if save_to_file:
            output_dir = self.setup.dir_output_all_runs
            output_filename = self.setup.file_combined_results_summary_by_lsoa
            path_to_file = os.path.join(output_dir, output_filename)
            df.to_csv(path_to_file, index=False)

    def combine_results_summary_by_admitting_unit(self, save_to_file=True):
        """
        Group by admitting unit summary.

        Each file input:
        +------+-------------+-------------+
        |      |   time_1    |    shift_1  |
        +------+------+------+------+------+
        | Unit | mean |  std | mean |  std |
        +------+------+------+------+------+
        |    1 | x.xx | x.xx | y.yy | y.yy |
        |    2 | x.xx | x.xx | y.yy | y.yy |
        |    3 | x.xx | x.xx | y.yy | y.yy |
        |  ... |  ... |  ... |  ... |  ... |
        |    n | x.xx | x.xx | y.yy | y.yy |
        +------+------+------+------+------+

        Resulting DataFrame:
        +------+------+------+------+------+------+------+
        |  any |  scenario_1 |  scenario_2 |    diff     |
        +------+------+------+------+------+------+------+
        |      |    shift    |    shift    |    shift    |
        +------+------+------+------+------+------+------+
        | Unit | mean |  std | mean |  std | mean |  std |
        +------+------+------+------+------+------+------+
        |    1 | x.xx | x.xx | y.yy | y.yy | z.zz | z.zz |
        |    2 | x.xx | x.xx | y.yy | y.yy | z.zz | z.zz |
        |    3 | x.xx | x.xx | y.yy | y.yy | z.zz | z.zz |
        |  ... |  ... |  ... |  ... |  ... |  ... |  ... |
        |    n | x.xx | x.xx | y.yy | y.yy | z.zz | z.zz |
        +------+------+------+------+------+------+------+
        """
        file_to_merge = self.setup.file_results_summary_by_admitting_unit

        try:
            data = self._hstack_multiple_dataframes(
                file_to_merge, csv_header=[0, 1])
        except FileNotFoundError:
            # TO DO - set up proper error message ----------------------------------
            pass

        # col_to_group = data.columns[0]
        cols_to_keep = ['utility_shift', 'mRS shift', 'mRS 0-2']
        # Same LSOA appearing in multiple files will currently have
        # multiple mostly-empty rows in the "data" DataFrame.
        # Group matching rows:
        # df = self._group_data(data, col_to_group, cols_to_keep)

        # Create new columns of this diff that:
        df = self._diff_data(data, cols_to_keep)

        if save_to_file:
            output_dir = self.setup.dir_output_all_runs
            output_filename = (
                self.setup.file_combined_results_summary_by_admitting_unit)
            path_to_file = os.path.join(output_dir, output_filename)
            df.to_csv(path_to_file, index=False)

    # ############################
    # ##### HELPER FUNCTIONS #####
    # ############################
    def _diff_data(self, df, cols_to_diff):
        """
        C
        """
        # Combine data into this DataFrame:

        # Change to select top level of multiindex:
        scenario_name_list = sorted(list(set(
            df.columns.get_level_values(0).to_list())))
        # Drop 'any' scenario:
        scenario_name_list.remove('any')
        # For scenarios [A, B, C], get a list of pairs
        # [[A, B], [A, C], [B, C]].
        scenario_name_pairs = list(combinations(scenario_name_list, 2))

        for c in cols_to_diff:
            # Take the difference between each pair of scenarios:
            for pair in scenario_name_pairs:
                p0 = pair[0]
                p1 = pair[1]
                diff_col_name = f'diff_{p0}_minus_{p1}'

                data0 = df[p0][c]
                data1 = df[p1][c]
                try:
                    for col in data0.columns:
                        if col in ['mean', 'median']:
                            # Take the difference between averages.
                            data_diff = data0[col] - data1[col]
                        elif col in ['std']:
                            # Propagate errors for std.
                            # Convert pandas NA to numpy NaN.
                            d0 = data0[col].copy().pow(2.0)
                            d1 = data1[col].copy().pow(2.0)
                            d2 = d0.add(d1, fill_value=0)
                            data_diff = d2.pow(0.5)
                            # data_diff = np.sqrt(np.nansum(
                            #     [data0[col]**2.0,  data1[col]**2.0]))
                        else:
                            # Don't know what to do with the rest yet. ----------------------
                            # TO DO
                            data_diff = ['help'] * len(df)
                        df[diff_col_name, c, col] = data_diff
                except AttributeError:
                    # No more nested column index levels.
                    data_diff = data0 - data1
                    df[diff_col_name, c] = data_diff
                    # TO DO - what about std herE? ---------------------------------
        return df

    def _hstack_multiple_dataframes(self, file_to_merge, csv_header=None):
        """
        # Combine multiple DataFrames from different scenarios into here.
        # Stacks all DataFrames one on top of the other with no other
        # change in columns.

        Each file input:
        +--------+-----------+----------+
        | Region | has_units | has_lsoa |
        +--------+-----------+----------+
        |      1 |      True |     True |
        |      2 |      True |     True |
        |      3 |     False |     True |
        |    ... |       ... |      ... |
        |      n |     False |     True |
        +--------+-----------+----------+

        Resulting DataFrame:
                 +----------------------+----------------------+
                 |      scenario_1      |      scenario_2      |
        +--------+-----------+----------+-----------+----------+
        | Region | has_units | has_lsoa | has_units | has_lsoa |
        +--------+-----------+----------+-----------+----------+
        |      1 |      True |     True |      True |     True |
        |      2 |      True |     True |     False |     True |
        |      3 |     False |     True |      True |     True |
        |    ... |       ... |      ... |       ... |      ... |
        |      n |     False |     True |     False |     True |
        +--------+-----------+----------+-----------+----------+
        """
        # data = pd.DataFrame()

        dfs_to_merge = {}

        for d, dir_output in enumerate(self.setup.list_dir_output):
            file_input = file_to_merge
            path_to_file = os.path.join(dir_output, file_input)

            if csv_header is None:
                df = pd.read_csv(path_to_file)
            else:
                # Specify header to import as a multiindex DataFrame.
                df = pd.read_csv(path_to_file, header=csv_header)

            if len(dfs_to_merge.items()) < 1:
                shared_col_name = df.columns[0]
                # dfs_to_merge['any'] = df[shared_col_name]

            # Create a name for this scenario:
            scenario_name = os.path.split(dir_output)[-1]

            # Set the index:
            df = df.set_index(df.columns[0])

            dfs_to_merge[scenario_name] = df

        # Can't concat without index columns.
        data = pd.concat(
            dfs_to_merge.values(),
            axis='columns',
            keys=dfs_to_merge.keys()  # Names for extra index row
            )

        # Copy index information to its own column with 'any' scenario:
        if isinstance(shared_col_name, str):
            any_col = ('any', shared_col_name)
        else:
            any_col = ('any', *shared_col_name)
        data[any_col] = data.index
        # data = data.reset_index()
        # Move 'any' index to the far left:
        cols = list(np.unique(data.columns.get_level_values(0).to_list()))
        cols.remove('any')
        cols = ['any'] + cols
        data = data[cols]

        # Sort rows by contents of 'any' column:
        data = data.sort_values(any_col)

        # # TO DO - only want the following lines for columns that should be bool ---------------
        # # Replace missing values with 0 in the region columns:
        # data = data.fillna(value=0)

        # Did have dtype float/str from missing values, now want int:
        data = data.convert_dtypes()

        return data

    def _merge_multiple_dataframes(self, file_to_merge, merge_col='LSOA11CD'):
        # Combine multiple DataFrames from different scenarios into here.
        # Stacks all DataFrames one on top of the other with no other
        # change in columns.
        data = pd.DataFrame(columns=[merge_col])
        scenario_cols_list = []
        scenario_series_list = []

        for d, dir_output in enumerate(self.setup.list_dir_output):
            file_input = file_to_merge
            path_to_file = os.path.join(dir_output, file_input)

            df = pd.read_csv(path_to_file)

            # Create a name for this scenario:
            scenario_name = os.path.split(dir_output)[-1]
            scenario_series = pd.Series(
                [1]*len(df),
                index=df[merge_col],
                name=scenario_name
            )

            scenario_cols_list.append(scenario_name)
            scenario_series_list.append(scenario_series)
            # Add all new LSOAs to the bottom of the existing DataFrame
            # and remove any duplicate rows.
            data = pd.concat([data, df], axis=0).drop_duplicates()
        # Merge in the Series data:
        for s in scenario_series_list:
            data = pd.merge(
                data, s.reset_index(),
                left_on=merge_col, right_on=merge_col, how='left'
                )
        # Replace missing values with 0 in the scenario columns:
        data = data.fillna(
            value=dict(zip(scenario_cols_list,
                           [0]*len(scenario_cols_list))))
        data = data.convert_dtypes()
        # Sort rows:
        data = data.sort_values(merge_col)
        return data