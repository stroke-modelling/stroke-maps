"""
Calculations for stroke units.
"""
import pandas as pd
import stroke_maps.load_data as load_data


def calculate_transfer_units(df_stroke_teams):
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
    df_stroke_teams = df_stroke_teams.reset_index()

    # Pick out the names of hospitals offering IVT:
    mask_ivt = (df_stroke_teams['use_ivt'] == 1)
    ivt_hospital_names = df_stroke_teams['postcode'][mask_ivt].values

    # Pick out the names of hospitals offering MT:
    mask_mt = (df_stroke_teams['use_mt'] == 1)
    mt_hospital_names = df_stroke_teams['postcode'][mask_mt].values

    # For units that don't offer IVT, set a placeholder value.
    # Don't calculate the transfer units for these.
    # Later the placeholder will be changed to pd.NA.
    mask = df_stroke_teams['postcode'].isin(ivt_hospital_names)
    df_stroke_teams.loc[~mask, 'transfer_unit_postcode'] = 'none'

    # Firstly, determine MT feeder units based on travel time.
    # Each stroke unit will be assigned the MT unit that it is
    # closest to in travel time.
    # Travel time matrix between hospitals:
    df_time_inter_hospital = load_data.travel_time_matrix_units()
    # Reduce columns of inter-hospital time matrix to just MT hospitals:
    df_time_inter_hospital = df_time_inter_hospital[mt_hospital_names]

    # From this reduced dataframe, pick out
    # the smallest time in each row and
    # the MT hospital that it belongs to.
    # Store the results in this DataFrame:
    df_nearest_mt = pd.DataFrame(index=df_time_inter_hospital.index)
    # The smallest time in each row:
    df_nearest_mt['transfer_unit_travel_time'] = (
        df_time_inter_hospital.min(axis='columns'))
    # The name of the column containing the smallest time in each row:
    df_nearest_mt['transfer_unit_postcode'] = (
        df_time_inter_hospital.idxmin(axis='columns'))

    # Make sure the complete list of stroke teams is included.
    # If there are any units in the input dataframe that weren't
    # in the travel time matrix, then these will be added in now.
    df_nearest_mt = df_nearest_mt.reset_index()
    df_nearest_mt = df_nearest_mt.rename(
        columns={'from_postcode': 'postcode'})
    df_nearest_mt = pd.merge(
        df_nearest_mt, df_stroke_teams['postcode'],
        on='postcode', how='right')
    df_nearest_mt = df_nearest_mt.set_index('postcode')

    # Update the feeder units list with anything specified
    # by the user.
    df_services_to_update = df_stroke_teams[
        df_stroke_teams['transfer_unit_postcode'] != 'nearest']
    units_to_update = df_services_to_update['postcode'].values
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
