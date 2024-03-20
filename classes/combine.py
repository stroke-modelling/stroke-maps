"""
Combine features from multiple runs.

Welcome to MultiIndex hell. *Doom trumpets*

TO DO - write me --------------------------------------------------------------------

self.combine_selected_units()
self.combine_selected_transfer()
self.combine_selected_lsoa()
self.combine_results_summary_by_lsoa()
self.combine_results_summary_by_admitting_unit()
"""
import numpy as np
import pandas as pd
import os
from itertools import combinations


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

    # ####################
    # ##### WRAPPERS #####
    # ####################
    def combine_inputs_and_results(
            self, df_input, df_results, col_input, col_results, how='left'):
        """
        Wrapper for pd.merge().

        Expect df_input to have only one unnamed column level.
        Expect df_results to have column levels named
        'property' and 'subtype'.
        """
        # Target column heading level names:
        headers = df_results.columns.names

        # Create column levels for the input dataframe.
        # Create the correct total number of column names and leave
        # them blank.
        df_input_cols = [[''] * len(df_input.columns)] * len(headers)

        if isinstance(df_input.columns, pd.MultiIndex):
            # Already have multiple column levels.
            # Check names...
            if np.any(np.array(df_input.columns.names) == None):
                # Can't check the column header names.
                err = ''.join([
                    'Please set the column header names of df_input ',
                    'with `df_input.columns.names = headers`.'
                    ])
                raise KeyError(err) from None
            else:
                for header in np.array(df_input.columns.names):
                    # Find where this column level needs to be
                    # to match df_results.
                    ind = headers.index(header)
                    # Update the new column array with column names from
                    # the input dataframe.
                    df_input_cols[ind] = df_input.columns

        # Set up a new input DataFrame with the required column levels.
        df_input = pd.DataFrame(
            df_input.values,
            index=df_input.index,
            columns=df_input_cols
            )
        df_input_cols.columns.names = headers

        # Now that the column header levels match, merge:
        df = pd.merge(df_input, df_results,
                      left_on=col_input, right_on=col_results, how=how)
        return df

    def combine_selected_units(
            self, dict_scenario_df_to_merge):
        """
        Combine selected units.

        Each file input:
        +------+-------------+-------------+
        |      |   time_1    |    shift_1  |    property
        +------+------+------+------+------+
        | Unit | mean |  std | mean |  std |    subtype
        +------+------+------+------+------+
        |    1 | x.xx | x.xx | y.yy | y.yy |
        |    2 | x.xx | x.xx | y.yy | y.yy |
        |    3 | x.xx | x.xx | y.yy | y.yy |
        |  ... |  ... |  ... |  ... |  ... |
        |    n | x.xx | x.xx | y.yy | y.yy |
        +------+------+------+------+------+

        Resulting DataFrame:
        +------+------+------+------+------+------+------+
        |  any |  scenario_1 |  scenario_2 |    diff     |    scenario
        +------+------+------+------+------+------+------+
        |      |    shift    |    shift    |    shift    |    property
        +------+------+------+------+------+------+------+
        | Unit | mean |  std | mean |  std | mean |  std |    subtype
        +------+------+------+------+------+------+------+
        |    1 | x.xx | x.xx | y.yy | y.yy | z.zz | z.zz |
        |    2 | x.xx | x.xx | y.yy | y.yy | z.zz | z.zz |
        |    3 | x.xx | x.xx | y.yy | y.yy | z.zz | z.zz |
        |  ... |  ... |  ... |  ... |  ... |  ... |  ... |
        |    n | x.xx | x.xx | y.yy | y.yy | z.zz | z.zz |
        +------+------+------+------+------+------+------+
        """
        df = self._hstack_multiple_dataframes(
            dict_scenario_df_to_merge,
            cols_for_scenario=[
                'use_ivt',
                'use_mt',
                'use_msu',
                'selected',
                'transfer_unit_postcode',
            ])

        # col_to_group = data.columns[0]
        cols_to_keep = ['utility_shift', 'mRS shift', 'mRS 0-2']
        # Same LSOA appearing in multiple files will currently have
        # multiple mostly-empty rows in the "data" DataFrame.
        # Group matching rows:
        # df = self._group_data(data, col_to_group, cols_to_keep)

        # Create new columns of this diff that:
        df = self._diff_data(df, cols_to_keep)

        # Rename the MultiIndex column names:
        headers = ['scenario', 'property']
        if len(dict_scenario_df_to_merge.values()[0].columns.names) == 3:
            headers.append('subtype')
        df.columns = df.columns.set_names(headers)

        # Put 'property' above 'scenario':
        df = df.swaplevel('scenario', 'property', axis='columns')

        return df

    def combine_selected_transfer(
            self, dict_scenario_df_to_merge):
        """
        Combine selected units.

        Each file input:
        +------+-----+---------------+-----------------+
        | Unit | ... | transfer_unit | transfer_coords |    property
        +------+-----+---------------+-----------------+
        |    1 | ... |             2 |  -x.xx, yy.yy   |
        |    2 | ... |             2 |  -x.xx, yy.yy   |
        |    3 | ... |             2 |  -x.xx, yy.yy   |
        |  ... | ... |           ... |       ...       |
        |    n | ... |             4 |  -x.xx, yy.yy   |
        +------+-----+---------------+-----------------+

        Resulting DataFrame:
                               +------------+------------+
                               | scenario_1 | scenario_2 |    scenario
        +------+---------------+------------+------------+
        | Unit | transfer_unit |        Use |        Use |    property
        +------+---------------+------------+------------+
        |    1 |             1 |          1 |          0 |
        |    2 |             1 |          1 |          0 |
        |    3 |             1 |          1 |          1 |
        |  ... |           ... |        ... |        ... |
        |    1 |             9 |          0 |          1 |
        +------+---------------+------------+------------+
        """
        # Merge the separate files based on combo of unit and
        # transfer unit, two indexes.
        df = self._hstack_multiple_dataframes(
            dict_scenario_df_to_merge,
            # add_use_column=True,
            cols_for_scenario=['selected', ],
            extra_cols_for_index=['transfer_unit_postcode']
            )

        # Rename the MultiIndex column names:
        df.columns = df.columns.set_names(['scenario', 'property'])

        # Put 'property' above 'scenario':
        df = df.swaplevel('scenario', 'property', axis='columns')

        return df

    def combine_selected_lsoa(
            self, dict_scenario_df_to_merge):
        """
        Combine selected LSOA.

        Each file input:
        +------+-------------+-------------+
        |      |   time_1    |    shift_1  |    property
        +------+------+------+------+------+
        | LSOA | mean |  std | mean |  std |    subtype
        +------+------+------+------+------+
        |    1 | x.xx | x.xx | y.yy | y.yy |
        |    2 | x.xx | x.xx | y.yy | y.yy |
        |    3 | x.xx | x.xx | y.yy | y.yy |
        |  ... |  ... |  ... |  ... |  ... |
        |    n | x.xx | x.xx | y.yy | y.yy |
        +------+------+------+------+------+

        Resulting DataFrame:
        +------+------+------+------+------+------+------+
        |      |  scenario_1 |  scenario_2 |    diff     |    scenario
        +------+------+------+------+------+------+------+
        |      |    shift    |    shift    |    shift    |    property
        +------+------+------+------+------+------+------+
        | LSOA | mean |  std | mean |  std | mean |  std |    subtype
        +------+------+------+------+------+------+------+
        |    1 | x.xx | x.xx | y.yy | y.yy | z.zz | z.zz |
        |    2 | x.xx | x.xx | y.yy | y.yy | z.zz | z.zz |
        |    3 | x.xx | x.xx | y.yy | y.yy | z.zz | z.zz |
        |  ... |  ... |  ... |  ... |  ... |  ... |  ... |
        |    n | x.xx | x.xx | y.yy | y.yy | z.zz | z.zz |
        +------+------+------+------+------+------+------+
        """
        df = self._hstack_multiple_dataframes(
            dict_scenario_df_to_merge,
            cols_for_scenario=':'
            )

        # col_to_group = data.columns[0]
        cols_to_keep = ['utility_shift', 'mRS shift', 'mRS 0-2']
        # Same LSOA appearing in multiple files will currently have
        # multiple mostly-empty rows in the "data" DataFrame.
        # Group matching rows:
        # df = self._group_data(data, col_to_group, cols_to_keep)

        # Create new columns of this diff that:
        df = self._diff_data(df, cols_to_keep)

        # Rename the MultiIndex column names:
        headers = ['scenario', 'property']
        if len(dict_scenario_df_to_merge.values()[0].columns.names) == 3:
            headers.append('subtype')
        df.columns = df.columns.set_names(headers)

        # Put 'property' above 'scenario':
        df = df.swaplevel('scenario', 'property', axis='columns')

        return df

    # #####################
    # ##### COMBINING #####
    # #####################
    def _diff_data(self, df, cols_to_diff):
        """
        C
        """
        # Combine data into this DataFrame:

        # Change to select top level of multiindex:
        scenario_name_list = sorted(list(set(
            df.columns.get_level_values(0).to_list())))
        try:
            # Drop 'any' scenario:
            scenario_name_list.remove('any')
        except ValueError:
            # no 'any' scenario here.
            pass

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

    def _hstack_multiple_dataframes(
            self,
            dict_scenario_df_to_merge,
            add_use_column=False,
            cols_for_scenario=[],
            extra_cols_for_index=[]
            ):
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
        dfs_to_merge = {}

        for scenario_name, df in dict_scenario_df_to_merge.items():
            if len(extra_cols_for_index) > 0:
                iname = list(df.index.names)
                df = df.reset_index()
                df = df.set_index(iname + extra_cols_for_index)

            if len(dfs_to_merge.items()) < 1:
                shared_col_name = df.index.name

            if isinstance(cols_for_scenario, str):
                # Use all columns.
                pass
            else:
                split_bool = ((len(cols_for_scenario) != (len(df.columns))))
                split_for_any = True if split_bool else False
                if split_for_any:
                    # Find the names of these columns in this df.
                    # (so can specify one level of multiindex only).

                    scenario_cols = [self.find_multiindex_col(
                        df.columns, col) for col in cols_for_scenario]

                    if len(dfs_to_merge.items()) < 1:
                        # First time around this loop.
                        # Split off these columns from this scenario.
                        df_any = df.copy().drop(
                            cols_for_scenario, axis='columns')
                        dfs_to_merge['any'] = df_any
                    else:
                        pass

                    # Remove columns for "any" scenario:
                    df = df[scenario_cols]

            if add_use_column:
                shared_col_is_list = ((type(shared_col_name) == list) |
                                      (type(shared_col_name) == tuple))
                # TO DO ^ make this more generic.
                if shared_col_is_list:
                    use_col = tuple([b for b in shared_col_name[:-1]] + ['Use'])
                else:
                    use_col = 'Use'
                # Make a new column named use_col and set all values to 1:
                # (use "assign" to avoid annoying warning, value set on
                # copy of slice)
                df = df.assign(**{use_col: 1})
            else:
                pass

            dfs_to_merge[scenario_name] = df

        # Can't concat without index columns.
        data = pd.concat(
            dfs_to_merge.values(),
            axis='columns',
            keys=dfs_to_merge.keys()  # Names for extra index row
            )

        try:
            # Move 'any' index to the far left:
            cols = list(np.unique(data.columns.get_level_values(0).to_list()))
            cols.remove('any')
            cols = ['any'] + cols
            data = data[cols]
        except ValueError:
            # No 'any' columns yet.
            pass

        # Sort rows by contents of index:
        data = data.sort_index()

        # Did have dtype float/str from missing values, now want int
        # if possible:
        data = data.convert_dtypes()

        return data

    def _merge_multiple_dataframes(self, dict_scenario_df_to_merge, merge_col='lsoa_code'):
        # Combine multiple DataFrames from different scenarios into here.
        # Stacks all DataFrames one on top of the other with no other
        # change in columns.
        data = pd.DataFrame(columns=[merge_col])
        scenario_cols_list = []
        scenario_series_list = []

        for scenario_name, df in dict_scenario_df_to_merge.items():
            # Create a name for this scenario:
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


    def find_multiindex_col(self, columns, target):
        """
        MOVE ME - currently copied directly from Map()
        """
        if (type(columns[0]) == list) | (type(columns[0]) == tuple):
            # Convert all columns tuples into an ndarray:
            all_cols = np.array([[n for n in c] for c in columns])
        else:
            # No MultiIndex.
            all_cols = columns.values
        # Find where the grid matches the target string:
        inds = np.where(all_cols == target)
        # If more than one column, select the first.
        ind = inds[0][0]
        # Components of column containing the target:
        bits = all_cols[ind]
        bits_is_list = (type(columns[0]) == list) | (type(columns[0]) == tuple)
        # TO DO - make this generic arraylike ^
        # Convert to tuple for MultiIndex or str for single level.
        final_col = list((tuple(bits), )) if bits_is_list else bits
        return final_col