"""
Catchment class to find LSOAs nearest given stroke units.

Given a dataframe of stroke units and which services they provide,
this class can find each unit's chosen transfer unit and each unit's
catchment area of LSOAs.
"""
import pandas as pd
from importlib_resources import files


def find_each_lsoa_chosen_unit(df_time_lsoa_to_units):
    """
    Extract LSOA unit data from LSOA-unit travel matrix.

    Inputs
    ------
    df_time_lsoa_to_units - pd.DataFrame. Travel time matrix
                            with columns already limited as needed.

    Returns
    -------
    df_results - pd.DataFrame. One row per LSOA, columns for
                    chosen unit and travel time.
    """
    # Put the results in this dataframe where each row
    # is a different LSOA:
    df_results = pd.DataFrame(index=df_time_lsoa_to_units.index)
    # The smallest time in each row:
    df_results['unit_travel_time'] = (
        df_time_lsoa_to_units.min(axis='columns'))
    # The name of the column containing the smallest
    # time in each row:
    df_results['unit_postcode'] = (
        df_time_lsoa_to_units.idxmin(axis='columns'))
    return df_results
