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


def calculate_lsoa_catchment(self):
    """
    Calculate the LSOAs caught by each stroke unit.

    For the 'island' catchment type, nothing exists except the
    selected units and LSOAs in regions (English Integrated Care
    Boards ICBs and Welsh Local Health Boards LHBs) that contain
    selected units.
    For other catchment types, all catchment for all units is
    calculated.

    Stores
    ------
    df_lsoa - pd.DataFrame. Contains one row per LSOA and columns
                for its selected unit and travel time.
    """
    units = self.df_units
    regions_selected = sorted(list(set(units.loc[
        units['selected'] == 1, 'region_code'])))
    units_selected = units.index[units['selected'] == 1].tolist()

    # Teams providing IVT:
    teams_with_services = units[units['use_ivt'] == 1].index.tolist()

    if self.lsoa_catchment_type == 'island':
        # Only use the selected stroke units:
        teams_to_limit = units_selected
        # Find list of selected regions:
        regions_to_limit = regions_selected
    else:
        teams_to_limit = []
        regions_to_limit = []

    # Only keep selected teams that offer IVT:
    teams_to_limit = list(set(teams_with_services + units_selected))

    # For all LSOA:
    df_catchment = self.find_lsoa_catchment(teams_to_limit)

    # Mark selected LSOA:
    df_catchment = self.limit_lsoa_catchment_to_selected_units(
        df_catchment,
        regions_to_limit=regions_to_limit,
        units_to_limit=units_selected,
        limit_to_england=self.limit_to_england,
        limit_to_wales=self.limit_to_wales
        )

    # Set index columns to LSOA names and codes:
    df_catchment = df_catchment.reset_index()
    df_catchment = df_catchment.set_index(['lsoa', 'lsoa_code'])

    self.df_lsoa = df_catchment



def find_lsoa_catchment(
        self,
        teams_to_limit=[]
        ):
    """
    Wrapper to load travel time matrix and pick out LSOA data.

    Inputs
    ------
    teams_to_limit - list. Only keep these units in the travel
                        matrix columns.

    Returns
    -------
    df_catchment - pd.DataFrame. One row per LSOA, columns for
                    chosen unit and travel time.
    """
    # Load travel time matrix:
    # # Relative import from package files:
    path_to_file = files('stroke_maps.data').joinpath(
        'lsoa_travel_time_matrix_calibrated.csv')
    df_time_lsoa_to_units = pd.read_csv(path_to_file, index_col='LSOA')
    # Each column is a postcode of a stroke team and
    # each row is an LSOA name (LSOA11NM).

    # Limit columns to requested units:
    if len(teams_to_limit) > 0:
        df_time_lsoa_to_units = df_time_lsoa_to_units[teams_to_limit]

    # Assign LSOA by catchment area of these stroke units.
    df_catchment = self.find_each_lsoa_chosen_unit(
        df_time_lsoa_to_units)
    return df_catchment

def limit_lsoa_catchment_to_selected_units(
        self,
        df_catchment,
        regions_to_limit=[],
        units_to_limit=[],
        limit_to_england=False,
        limit_to_wales=False
        ):
    """
    Choose which LSOAs are selected using regions and units.

    Optionally limit the LSOAs to only a few regions.
    Optionally limit the LSOAs to only those caught by
    selected units.
    Optionally limit the LSOAs to only those in England or
    only those in Wales.

    Inputs
    ------
    df_catchment     - pd.DataFrame. LSOAs and their chosen units.
    regions_to_limit - list. List of regions to limit to.
    units_to_limit   - list. List of units to limit to.
    limit_to_england - bool. Whether to only keep English LSOA.
    limit_to_wales   - bool. Whether to only keep Welsh LSOA.

    Returns
    -------
    df_catchment - pd.DataFrame. The input dataframe with added
                    columns for LSOA codes and whether the LSOA
                    is selected.
    """
    # Load in all LSOA names, codes, regions...
    # Relative import from package files:
    path_to_file = files('stroke_maps.data').joinpath(
        'regions_lsoa_ew.csv')
    df_lsoa = pd.read_csv(path_to_file)
    # Columns: [lsoa, lsoa_code, region_code, region, region_type,
    #           icb_code, icb, isdn]

    # Keep a copy of the original catchment columns for later:
    cols_df_catchment = df_catchment.columns.tolist()
    # Merge in region information to catchment:
    df_catchment.reset_index(inplace=True)
    df_catchment = pd.merge(
        df_catchment, df_lsoa,
        left_on='LSOA', right_on='lsoa', how='left'
    )
    df_catchment.drop('LSOA', axis='columns', inplace=True)
    df_catchment.set_index('lsoa', inplace=True)

    # Limit rows to LSOA in requested regions:
    if len(regions_to_limit) > 0:
        # Limit the results to only LSOAs in regions
        # containing selected units.
        mask = df_catchment['region_code'].isin(regions_to_limit)
        df_catchment = df_catchment.loc[mask].copy()
    elif len(units_to_limit) > 0:
        # Limit the results to only LSOAs that are caught
        # by selected units.
        mask = df_catchment['unit_postcode'].isin(units_to_limit)
    else:
        mask = [True] * len(df_catchment)

    df_catchment['selected'] = 0
    df_catchment.loc[mask, 'selected'] = 1

    # If requested, remove England or Wales.
    if limit_to_england:
        mask = df_lsoa['region_type'] == 'LHB'
        df_catchment['selected'][mask] = 0
    elif limit_to_wales:
        mask = df_lsoa['region_type'] == 'SICBL'
        df_catchment['selected'][mask] = 0

    # Restore the shortened catchment DataFrame to its starting columns
    # plus the useful regions:
    cols = cols_df_catchment + ['lsoa_code', 'selected']
    # ['region', 'region_code', 'region_type']
    df_catchment = df_catchment[cols]

    return df_catchment
