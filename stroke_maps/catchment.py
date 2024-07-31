"""
Catchment class to find LSOAs nearest given stroke units.

Given a dataframe of stroke units and which services they provide,
this class can find each unit's chosen transfer unit and each unit's
catchment area of LSOAs.
"""
import pandas as pd
from importlib_resources import files
import stroke_maps.load_data as load_data


def find_nearest_unit(df_times):
    """
    Extract unit data from travel time matrix.

    Inputs
    ------
    df_times - pd.DataFrame. Travel time matrix with columns
               and rows already limited as needed.

    Returns
    -------
    df_results - pd.DataFrame. One row per starting point,
                 columns for chosen unit and travel time.
    """
    # Put the results in this dataframe where each row
    # is a different starting point:
    df_results = pd.DataFrame(index=df_times.index)
    # The smallest time in each row:
    df_results['unit_travel_time'] = df_times.min(axis='columns')
    # The name of the column containing the smallest
    # time in each row:
    df_results['unit_postcode'] = df_times.idxmin(axis='columns')
    return df_results


def calculate_transfer_units(
        df_stroke_teams,
        ivt_hospital_names=[],
        mt_hospital_names=[],
        use_northern_ireland=False
        ):
    """
    Find wheel-and-spoke IVT feeder units to each MT unit.

    Inputs
    ------
    df_stroke_teams - pd.DataFrame. Contains info on each unit
                      and the services it provides (IVT, MT, MSU).
                      Expect the following columns:
                      + use_ivt
                      + use_mt
                      + postcode
                      + transfer_unit_postcode

    Returns
    ------
    df_nearest_mt - pd.DataFrame. Each row is a stroke unit.
                    Columns are its postcode, its transfer unit
                    postcode and travel time.
    """
    df_stroke_teams = df_stroke_teams.copy()
    postcode_col = df_stroke_teams.index.name
    df_stroke_teams = df_stroke_teams.reset_index()

    if len(ivt_hospital_names) > 0:
        pass
    else:
        # Pick out the names of hospitals offering IVT:
        mask_ivt = (df_stroke_teams['use_ivt'] == 1)
        ivt_hospital_names = df_stroke_teams[postcode_col][mask_ivt].values

    if len(mt_hospital_names) > 0:
        pass
    else:
        # Pick out the names of hospitals offering MT:
        mask_mt = (df_stroke_teams['use_mt'] == 1)
        mt_hospital_names = df_stroke_teams[postcode_col][mask_mt].values

    # If there's no column for overriding the closest transfer unit,
    # create one now with the default value:
    try:
        df_stroke_teams['transfer_unit_postcode']
    except KeyError:
        df_stroke_teams['transfer_unit_postcode'] = 'nearest'

    # For units that don't offer IVT, set a placeholder value.
    # Don't calculate the transfer units for these.
    # Later the placeholder will be changed to pd.NA.
    mask = df_stroke_teams[postcode_col].isin(ivt_hospital_names)
    df_stroke_teams.loc[~mask, 'transfer_unit_postcode'] = 'none'

    # Firstly, determine MT feeder units based on travel time.
    # Each stroke unit will be assigned the MT unit that it is
    # closest to in travel time.
    # Travel time matrix between hospitals:
    if use_northern_ireland:
        df_time_inter_hospital = load_data.travel_time_matrix_ni_units()
    else:
        df_time_inter_hospital = load_data.travel_time_matrix_units()
    # Reduce columns of inter-hospital time matrix to just MT hospitals:
    df_time_inter_hospital = df_time_inter_hospital[mt_hospital_names]

    # From this reduced dataframe, pick out
    # the smallest time in each row and
    # the MT hospital that it belongs to.
    df_nearest_mt = find_nearest_unit(df_time_inter_hospital)
    df_nearest_mt = df_nearest_mt.rename(columns={
        'unit_travel_time': 'transfer_unit_travel_time',
        'unit_postcode': 'transfer_unit_postcode',
    })

    # Make sure the complete list of stroke teams is included.
    # If there are any units in the input dataframe that weren't
    # in the travel time matrix, then these will be added in now.
    df_nearest_mt = df_nearest_mt.reset_index()
    df_nearest_mt = df_nearest_mt.rename(
        columns={'from_postcode': postcode_col})
    df_nearest_mt = pd.merge(
        df_nearest_mt, df_stroke_teams[postcode_col],
        on=postcode_col, how='right')
    df_nearest_mt = df_nearest_mt.set_index(postcode_col)

    # Update the feeder units list with anything specified
    # by the user.
    df_services_to_update = df_stroke_teams[
        df_stroke_teams['transfer_unit_postcode'] != 'nearest']
    units_to_update = df_services_to_update[postcode_col].values
    transfer_units_to_update = df_services_to_update[
        'transfer_unit_postcode'].values
    for u, unit in enumerate(units_to_update):
        transfer_unit = transfer_units_to_update[u]
        if transfer_unit == 'none':
            # Set values to missing:
            transfer_unit = pd.NA
            mt_time = pd.NA
        else:
            # Find the time to this MT unit.
            mt_time = df_time_inter_hospital.loc[unit][transfer_unit]

        # Update the chosen nearest MT unit name and time.
        df_nearest_mt.at[unit, 'transfer_unit_postcode'] = transfer_unit
        df_nearest_mt.at[unit, 'transfer_unit_travel_time'] = mt_time

    return df_nearest_mt
