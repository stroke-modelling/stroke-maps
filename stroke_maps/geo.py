"""
Combine Catchment data with geometry to make GeoDataFrames for plots.

crs reference:
+ EPSG:4326  - longitude / latitude.
+ CRS:84     - same as EPSG:4326.
+ EPSG:27700 - British National Grid (BNG).
"""
import numpy as np
import pandas as pd
import geopandas
import os
from importlib_resources import files

from shapely import LineString  # For creating line geometry.
from pandas.api.types import is_numeric_dtype  # For checking dtype.
from stroke_maps.utils import find_multiindex_column_names


# #####################
# ##### LOAD DATA #####
# #####################

# TO DO

# load gdf from file (csv with multiindex)

# save gdf to file (csv with multiindex)

# #####################
# ##### LOAD DATA #####
# #####################
def import_geojson(region_type: 'str', path_to_file: 'str'=''):
    """
    Import a geojson file as GeoDataFrame.

    The crs (coordinate reference system) is set to British National
    Grid.

    Inputs
    ------
    region_type - str. Lookup name for selecting a geojson file.
                  This should be one of the column names from the
                  various regions files.

    Returns
    -------
    gdf_boundaries - GeoDataFrame. One row per region shape in the
                     file. Expect columns for region name and geometry.
    """
    # Select geojson file based on input region type:
    geojson_file_dict = {
        'LSOA11NM': 'LSOA.geojson',
        'SICBL22NM': 'SICBL.geojson',
        'LHB20NM': 'LHB.geojson'
    }

    if len(path_to_file) == 0:
        # Import region file:
        file_input = geojson_file_dict[region_type]
        # Relative import from package files:
        path_to_file = files('stroke_maps.data').joinpath(file_input)
    else:
        pass
    gdf_boundaries = geopandas.read_file(path_to_file)

    if region_type == 'LSOA11NM':
        index_col = 'LSOA11CD'
        # Only keep these columns.
        geo_cols = ['LSOA11NM', 'BNG_E', 'BNG_N',
                    'LONG', 'LAT', 'GlobalID', 'geometry']
    elif region_type == 'MSOA11NM':
        index_col = 'MSOA11CD'
        # Only keep these columns.
        # geo_cols = ['MSOA11NM', 'BNG_E', 'BNG_N',
        #             'LONG', 'LAT', 'GlobalID', 'geometry']
        geo_cols = list(gdf_boundaries.columns)
        geo_cols.remove('MSOA11CD')
    else:
        index_col = 'region_code'
        # Only keep these columns:
        geo_cols = ['region', 'BNG_E', 'BNG_N',
                    'LONG', 'LAT', 'GlobalID', 'geometry']

        # Find which columns to rename to 'region' and 'region_code'.
        if (region_type.endswith('NM') | region_type.endswith('NMW')):
            region_prefix = region_type.removesuffix('NM')
            region_prefix = region_prefix.removesuffix('NMW')
            region_code = region_prefix + 'CD'
        elif (region_type.endswith('nm') | region_type.endswith('nmw')):
            region_prefix = region_type.removesuffix('NM')
            region_prefix = region_prefix.removesuffix('NMW')
            region_code = region_prefix + 'cd'
        else:
            # This shouldn't happen.
            # TO DO - does this need a proper exception or can
            # we just change the above to if/else? ------------------------------
            region_code = region_type[:-2] + 'CD'

        try:
            # Rename this column:
            gdf_boundaries = gdf_boundaries.rename(columns={
                region_type: 'region',
                region_code: 'region_code'
            })
        except KeyError:
            # That column doesn't exist.
            # Try finding a column that has the same start and end
            # as requested:
            prefix = region_type[:3]
            suffix = region_type[-2:]
            success = False
            for column in gdf_boundaries.columns:
                # Casefold turns all UPPER into lower case.
                match = ((column[:3].casefold() == prefix.casefold()) &
                         (column[-2:].casefold() == suffix.casefold()))
                if match:
                    # Rename this column:
                    col_code = column[:-2] + region_code[-2:]
                    gdf_boundaries = gdf_boundaries.rename(columns={
                        column: 'region',
                        col_code: 'region_code'
                        })
                    success = True
                else:
                    pass
            if success is False:
                pass
                # TO DO - proper error here --------------------------------

    # Set the index:
    gdf_boundaries = gdf_boundaries.set_index(index_col)
    # Only keep geometry data:
    gdf_boundaries = gdf_boundaries[geo_cols]

    # If crs is given in the file, geopandas automatically
    # pulls it through. Convert to National Grid coordinates:
    if gdf_boundaries.crs != 'EPSG:27700':
        gdf_boundaries = gdf_boundaries.to_crs('EPSG:27700')
    return gdf_boundaries


# ########################
# ##### PROCESS DATA #####
# ########################
def load_regions():
    """
    Load region data from file.

    Returns
    -------
    df_regions - pd.DataFrame. Contains regions including SICBL, LHB.
                 Contains region codes for matching, names for
                 displaying prettier names, and invented short codes
                 for labelling regions on a map.
    """
    # Load and parse geometry data
    # Relative import from package files:
    path_to_file = files('stroke_maps.data').joinpath('regions_ew.csv')
    df_regions = pd.read_csv(path_to_file, index_col=[0, 1])

    # Add an extra column level:
    # Everything needs two levels: scenario, property.
    cols_df_regions = [
        df_regions.columns,                 # property
        ['any'] * len(df_regions.columns),  # scenario
    ]
    # New DataFrame with the extra column level:
    df_regions = pd.DataFrame(
        df_regions.values,
        index=df_regions.index,
        columns=cols_df_regions
    )
    # Rename the MultiIndex column names:
    df_regions.columns = df_regions.columns.set_names(['property', 'scenario'])
    # Index column: 'region'.
    # Expected column MultiIndex levels:
    #   - combined: ['scenario', 'property']
    #   - separate: ['{unnamed level}']

    return df_regions


def make_new_periphery_data(
        df_regions,
        df_units,
        df_lsoa
        ):
    """
    Find units, regions that aren't selected but catch selected LSOA.

    Use the term "periphery unit" for units that were not selected
    but that catch LSOA in regions that contain selected units.
    Use the term "periphery lsoa" for LSOA that are selected and
    lie outside the regions that contain selected units.

    Inputs
    ------
    df_regions - pd.DataFrame. Matches output of load_regions().
    df_units   - pd.DataFrame. Units, services, whether selected for
                 LSOA catchment. Matches output of Catchment.
    df_lsoa    - pd.DataFrame. LSOA names, chosen units...
                 Matches output of Catchment.

    Returns
    -------
    df_regions - pd.DataFrame. Same as input with additional columns
                 for whether region contains any selected unit, any
                 selected LSOA, or any periphery unit.
    df_units   - pd.DataFrame. Same as input with additional column
                 for whether unit catches any LSOA in any region
                 that contains a selected unit.
    """
    # List of scenarios included in the units and LSOA data:
    scenario_list = sorted(list(set(
        df_units.columns.get_level_values('scenario'))))
    try:
        scenario_list.remove('any')
    except ValueError:
        pass
    # Also remove any 'diff' scenarios:
    scenario_list = [s for s in scenario_list if not s.startswith('diff')]

    # Load region info for each LSOA:
    # Relative import from package files:
    path_to_file = files('stroke_maps.data').joinpath('regions_lsoa_ew.csv')
    df_lsoa_regions = pd.read_csv(path_to_file, index_col=[0, 1])
    # Add an extra column level:
    # Everything needs two levels: scenario, property.
    cols_df_lsoa_regions = [
        df_lsoa_regions.columns,                 # property
        ['any'] * len(df_lsoa_regions.columns),  # scenario
    ]
    if 'subtype' in df_lsoa.columns.names:
        cols_df_lsoa_regions.append([''] * len(df_lsoa_regions.columns))
    # New DataFrame with the extra column level:
    df_lsoa_regions = pd.DataFrame(
        df_lsoa_regions.values,
        index=df_lsoa_regions.index,
        columns=cols_df_lsoa_regions
    )
    df_lsoa_regions.columns.names = df_lsoa.columns.names
    # Index column: 'region'.

    # Merge region info into LSOA data:
    df_lsoa = pd.merge(df_lsoa.copy(), df_lsoa_regions,
                       left_index=True, right_index=True, how='left')

    # Reset index for easier column selection:
    df_regions = df_regions.reset_index()

    # Input dataframes should contain multiple scenarios in a
    # MultiIndex column heading. Pick out each one in turn
    # and calculate the periphery units and regions.
    for scenario in scenario_list:
        # Names of selected LSOA:
        col_selected = find_multiindex_column_names(
            df_lsoa, property=['selected'], scenario=[scenario])
        mask = (df_lsoa[col_selected] == 1).values

        df_lsoa_selected = df_lsoa.loc[mask].copy().reset_index()
        col_lsoa_code = find_multiindex_column_names(
            df_lsoa_selected, property=['lsoa_code'])
        lsoa_selected = list(df_lsoa_selected[col_lsoa_code])

        # Names of selected units:
        col_selected = find_multiindex_column_names(
            df_units, property=['selected'], scenario=[scenario])

        units_selected = df_units[
            df_units[col_selected] == 1].index.values
        # Regions containing selected units:
        regions_selected = df_units[
            df_units[col_selected] == 1]['region_code'].values.flatten()

        # Which columns do we want?
        cols = find_multiindex_column_names(
            df_lsoa, scenario=['any', scenario])
        # Subset of only these columns:
        df_lsoa_here = df_lsoa.loc[:, cols].copy()
        # # Drop the 'scenario' level
        df_lsoa_here = df_lsoa_here.droplevel('scenario', axis='columns')

        # Get a dictionary "d" of results:
        d = link_pathway_geography(
            df_lsoa_here,
            df_units,
            units_selected,
            lsoa_selected
            )

        # Add these results to the starting dataframes:
        # Units:
        nlevels = df_units.columns.nlevels
        col_periphery_unit = tuple(['periphery_unit', scenario] +
                                   [''] * (nlevels - 2))

        df_units[col_periphery_unit] = 0
        mask = df_units.index.isin(d['periphery_units'])
        df_units.loc[mask, col_periphery_unit] = 1

        # Regions:
        nlevels = df_regions.columns.nlevels
        col_region_code = find_multiindex_column_names(
            df_regions, property=['region_code'])

        col_unit = tuple(['contains_unit', scenario] + [''] * (nlevels - 2))
        col_punit = tuple(['contains_periphery_unit', scenario] +
                          [''] * (nlevels - 2))
        col_plsoa = tuple(['contains_periphery_lsoa', scenario] +
                          [''] * (nlevels - 2))

        df_regions[col_unit] = 0
        mask = df_regions[col_region_code].isin(regions_selected)
        df_regions.loc[mask, col_unit] = 1

        df_regions[col_plsoa] = 0
        mask = df_regions[col_region_code].isin(d['regions_containing_lsoa'])
        df_regions.loc[mask, col_plsoa] = 1

        df_regions[col_punit] = 0
        mask = df_regions[col_region_code].isin(
            d['regions_with_periphery_units'])
        df_regions.loc[mask, col_punit] = 1

    # Set index back to how it was earlier:
    df_regions = df_regions.set_index(['region', 'region_code'])
    return df_regions, df_units


def link_pathway_geography(
        df_lsoa,
        df_units,
        units_selected,
        lsoa_selected
        ):
    """
    Find regions, units, LSOA that aren't selected but are nearby.

    Find:
    + regions containing selected LSOA
    + regions containing selected units
    + LSOA in regions containing selected units
    + stroke units catching those LSOA (periphery units)
    + regions containing periphery units

    Inputs
    ------
    df_lsoa        - pd.DataFrame. Matches output from Catchment.
    df_units       - pd.DataFrame. Matches output from Catchment.
    units_selected - list. Postcodes of selected units.
    lsoa_selected  - list. LSOA codes of selected LSOA.

    Returns
    -------
    to_return - dict. Contains a list of postcodes of periphery units,
                a list of region codes containing selected LSOA, and
                a list of region codes containing periphery units.
    """
    # Mask for selected LSOA:
    df_lsoa = df_lsoa.copy().reset_index()
    col_lsoa_code = find_multiindex_column_names(
        df_lsoa, property=['lsoa_code'])
    mask_lsoa_selected = (
        df_lsoa.copy().reset_index()[col_lsoa_code].isin(lsoa_selected).values)
    # Find list of regions containing LSOA caught by selected units.
    col_region_code = find_multiindex_column_names(
        df_lsoa, property=['region_code'])
    regions_containing_lsoa = sorted(list(set(
        df_lsoa.loc[mask_lsoa_selected, col_region_code])))

    # Reset index for easier access to values:
    df_units = df_units.copy()
    df_units = df_units.reset_index()
    # Which columns do we want?
    cols = find_multiindex_column_names(df_units, property=['postcode', 'region_code'])
    # Subset of only these columns:
    df_units = df_units.loc[:, cols].copy()
    # Drop the 'scenario' level:
    # df_units = df_units.droplevel('scenario', axis='columns')

    col_unit = find_multiindex_column_names(df_units, property=['postcode'])
    mask_units_selected = df_units[col_unit].isin(units_selected)

    # Find list of regions containing selected units:
    col_region_code = find_multiindex_column_names(
        df_units, property=['region_code'])
    regions_containing_units = list(
        df_units.loc[mask_units_selected, col_region_code])

    # Mask for LSOA in regions containing selected units:
    col_region_code = find_multiindex_column_names(
        df_lsoa, property=['region_code'])
    mask_lsoa_in_regions_containing_units = (
        df_lsoa[col_region_code].isin(regions_containing_units))
    # Find list of periphery units:
    col_unit_postcode = find_multiindex_column_names(
        df_lsoa, property=['unit_postcode'])
    periphery_units = sorted(list(set(
        df_lsoa.loc[mask_lsoa_in_regions_containing_units,
                    col_unit_postcode])))

    # Mask for regions containing periphery units:
    col_unit = find_multiindex_column_names(df_units, property=['postcode'])
    mask_regions_periphery_units = (
        df_units[col_unit].isin(periphery_units))
    # Find list of periphery regions:
    col_region_code = find_multiindex_column_names(
        df_units, property=['region_code'])
    regions_with_periphery_units = list(
        df_units.loc[mask_regions_periphery_units, col_region_code])

    to_return = {
        'periphery_units': periphery_units,
        'regions_containing_lsoa': regions_containing_lsoa,
        'regions_with_periphery_units': regions_with_periphery_units
    }
    return to_return


def check_scenario_level(
        df,
        scenario_name='scenario'
        ):
    """
    Ensure DataFrame contains a column level named 'scenario'.

    Inputs
    ------
    df - pd.DataFrame. Check this for a MultiIndex column heading
         with a level named 'scenario'.
    scenario_name - str. If the 'scenario' level has to be made here,
         name the scenario this string.

    Returns
    -------
    df - pd.DataFrame. Same as the input with a 'scenario' column level.
    """
    if df is None:
        # Nothing to do here.
        return df
    else:
        pass

    # Check if 'scenario' column level exists:
    levels = df.columns.names
    if 'scenario' in levels:
        # Nothing to do here.
        return df
    else:
        if len(levels) == 1:
            # Only 'property' exists.
            # Add columns for 'scenario' below it:
            df_cols = [df.columns, [scenario_name] * len(df.columns)]
            if levels[0] is None:
                levels = ['property', 'scenario']
            else:
                levels = [levels[0]] + ['scenario']
        else:
            # Assume that a 'property' level exists and will go above
            # 'scenario', and anything else will go below it.
            df_cols_property = df.columns.get_level_values('property')
            df_cols_other = [df.columns.get_level_values(lev)
                             for lev in levels[1:]]
            df_cols = [
                df_cols_property,
                [scenario_name] * len(df.columns),
                *df_cols_other
                ]
            levels = [levels[0]] + ['scenario'] + levels[1:]

        df = pd.DataFrame(
            df.values,
            index=df.index,
            columns=df_cols
        )
        df.columns.names = levels
        return df


# ########################
# ##### COMBINE DATA #####
# ########################
def main(
        df_lsoa,
        df_units,
        df_regions=None,
        df_transfer=None,
        ):
    """
    Create GeoDataFrames by loading geometry and matching inputs.

    Inputs
    ------
    df_lsoa     - pd.DataFrame. LSOA data from Catchment.
    df_units    - pd.DataFrame. Units data from Catchment.
    df_regions  - pd.DataFrame. Regions data from load_regions.
    df_transfer - pd.DataFrame. Transfer data from Catchment.

    Returns
    -------
    gdf_boundaries_regions   - GeoDataFrame for df_regions.
    gdf_points_units         - GeoDataFrame for df_units.
    gdf_lines_transfer       - GeoDataFrame for df_transfer.
    gdf_boundaries_lsoa      - GeoDataFrame for df_lsoa.
    gdf_boundaries_catchment - GeoDataFrame for df_lsoa where LSOA
                               are grouped by catchment unit.
    """
    if df_regions is None:
        df_regions = load_regions()

    # Check whether the input DataFrames have a 'scenario' column level.
    # If not, add one now with a placeholder scenario name.
    df_lsoa = check_scenario_level(df_lsoa)
    df_units = check_scenario_level(df_units)
    df_regions = check_scenario_level(df_regions)
    df_transfer = check_scenario_level(df_transfer)

    df_regions = load_regions()
    df_regions, df_units = make_new_periphery_data(
        df_regions, df_units, df_lsoa)

    gdf_boundaries_regions = _load_geometry_regions(df_regions)
    gdf_points_units = _load_geometry_stroke_units(df_units)
    if df_transfer is None:
        gdf_lines_transfer = pd.DataFrame()  # Leave blank.
    else:
        gdf_lines_transfer = _load_geometry_transfer_units(df_transfer)
    gdf_boundaries_lsoa = _load_geometry_lsoa(df_lsoa)

    # Merge many LSOA into one big blob of catchment area.
    gdf_boundaries_catchment = _load_geometry_catchment(
        gdf_boundaries_lsoa, df_transfer)
    # Label periphery units in catchment data:
    scenario_list = sorted(list(set(
        gdf_boundaries_catchment['selected'
                                 ].columns.get_level_values('scenario'))))
    for scenario in scenario_list:
        gdf_boundaries_catchment[('periphery_unit', scenario)] = 0
        mask_units = df_units[('periphery_unit', scenario)] == 1
        units = df_units.loc[mask_units].index.values
        mask = gdf_boundaries_catchment['unit'].isin(units)
        gdf_boundaries_catchment.loc[mask.values,
                                     ('periphery_unit', scenario)] = 1

    # Only keep separate LSOA that have been selected.
    df_select = gdf_boundaries_lsoa.xs(
        'selected', axis='columns', level='property', drop_level=False)
    mask = (df_select == 1).any(axis='columns')
    gdf_boundaries_lsoa = gdf_boundaries_lsoa.loc[mask].copy()

    # Make columns in regions and transfer that can be used for any
    # scenario created in the LSOA data using diff.
    # e.g. 'diff_drip-and-ship_minus_mothership' scenario wasn't
    # run directly in the pathway and so its regions and units info
    # doesn't exist yet.
    scenario_list = sorted(list(set(
        gdf_boundaries_lsoa.columns.get_level_values('scenario'))))
    scenario_list.remove('any')
    for scenario in scenario_list:
        if 'diff' in scenario:
            # Add any other columns that these expect.
            gdf_boundaries_regions = create_combo_cols(
                gdf_boundaries_regions, scenario)
            gdf_points_units = create_combo_cols(
                gdf_points_units, scenario)
        else:
            # The data for non-diff scenarios should already exist.
            pass

    # For each gdf, reset the index so that the index columns
    # appear in a saved .geojson and label the new index column.
    def make_new_index(gdf):
        gdf = gdf.reset_index()
        gdf.index.name = 'id'
        return gdf

    gdf_boundaries_regions = make_new_index(gdf_boundaries_regions)
    gdf_points_units = make_new_index(gdf_points_units)
    gdf_lines_transfer = make_new_index(gdf_lines_transfer)
    gdf_boundaries_lsoa = make_new_index(gdf_boundaries_lsoa)
    # gdf_boundaries_catchment = make_new_index(gdf_boundaries_catchment)

    # Replace any blank scenarios with "any":
    gdf_boundaries_regions = fill_blank_level(gdf_boundaries_regions)
    gdf_points_units = fill_blank_level(gdf_points_units)
    gdf_lines_transfer = fill_blank_level(gdf_lines_transfer)
    gdf_boundaries_lsoa = fill_blank_level(gdf_boundaries_lsoa)
    gdf_boundaries_catchment = fill_blank_level(gdf_boundaries_catchment)

    # Replace any blank subtypes with "":
    gdf_boundaries_regions = fill_blank_level(
        gdf_boundaries_regions, level='subtype', fill_value='')
    gdf_points_units = fill_blank_level(
        gdf_points_units, level='subtype', fill_value='')
    gdf_lines_transfer = fill_blank_level(
        gdf_lines_transfer, level='subtype', fill_value='')
    gdf_boundaries_lsoa = fill_blank_level(
        gdf_boundaries_lsoa, level='subtype', fill_value='')
    gdf_boundaries_catchment = fill_blank_level(
        gdf_boundaries_catchment, level='subtype', fill_value='')

    # Sort units by short code:
    col_short_code = find_multiindex_column_names(
        gdf_points_units, property=['short_code'])
    gdf_points_units = gdf_points_units.sort_values(col_short_code)

    # Set geometry columns in case names were reset there:
    def set_geometry(gdf):
        try:
            gdf.columns.get_level_values('property')
        except KeyError:
            # Nothing to do here.
            return gdf

        col_geometry = find_multiindex_column_names(
            gdf, property=['geometry'])
        # Set geometry column:
        gdf = gdf.set_geometry(col_geometry)
        return gdf
    gdf_boundaries_regions = set_geometry(gdf_boundaries_regions)
    gdf_points_units = set_geometry(gdf_points_units)
    gdf_lines_transfer = set_geometry(gdf_lines_transfer)
    gdf_boundaries_lsoa = set_geometry(gdf_boundaries_lsoa)
    gdf_boundaries_catchment = set_geometry(gdf_boundaries_catchment)

    to_return = (
        gdf_boundaries_regions,
        gdf_points_units,
        gdf_lines_transfer,
        gdf_boundaries_lsoa,
        gdf_boundaries_catchment
    )

    return to_return


def _load_geometry_regions(df_regions):
    """
    Create GeoDataFrame of geometry and existing DataFrame.

    Inputs
    ------
    df_regions - pd.DataFrame. Region info.

    Returns
    gdf_regions - GeoDataFrame. Region info and geometry.
    """
    # All region polygons:
    gdf_list = []
    gdf_boundaries_regions_e = import_geojson('SICBL22NM')
    gdf_list.append(gdf_boundaries_regions_e)
    gdf_boundaries_regions_w = import_geojson('LHB20NM')
    gdf_list.append(gdf_boundaries_regions_w)
    # Combine:
    gdf_boundaries_regions = pd.concat(gdf_list, axis='rows')

    # Index column: 'region'.
    # Always has only one unnamed column index level.

    # Drop columns that appear in both DataFrames:
    gdf_boundaries_regions = gdf_boundaries_regions.drop(
        'region', axis='columns'
    )

    # ----- Prepare separate data -----
    # Set up column level info for the merged DataFrame.
    # Everything needs two levels: scenario, property.
    # Geometry:
    cols_gdf_boundaries_regions = [
        gdf_boundaries_regions.columns,                 # property
        ['any'] * len(gdf_boundaries_regions.columns),  # scenario
    ]
    # Final data:
    col_level_names = ['property', 'scenario']
    col_geometry = ('geometry', 'any')

    # Geometry:
    gdf_boundaries_regions = pd.DataFrame(
        gdf_boundaries_regions.values,
        index=gdf_boundaries_regions.index,
        columns=cols_gdf_boundaries_regions
    )

    # ----- Create final data -----
    # Merge together the DataFrames.
    gdf_boundaries_regions = pd.merge(
        gdf_boundaries_regions, df_regions,
        left_index=True, right_index=True, how='right'
    )

    # Name the column levels:
    gdf_boundaries_regions.columns = (
        gdf_boundaries_regions.columns.set_names(col_level_names))

    # Sort the results by scenario:
    gdf_boundaries_regions = gdf_boundaries_regions.sort_index(
        axis='columns', level='scenario')

    # Convert to GeoDataFrame:
    gdf_boundaries_regions = geopandas.GeoDataFrame(
        gdf_boundaries_regions,
        geometry=col_geometry
        )

    return gdf_boundaries_regions


def _load_geometry_stroke_units(df_units):
    """
    Create GeoDataFrame of geometry and existing DataFrame.

    Inputs
    ------
    df_units - pd.DataFrame. Unit info.

    Returns
    -------
    gdf_units - GeoDataFrame. Unit info and geometry.
    """
    # Selected stroke units names, services, and regions.
    # Index column: Postcode.
    # Expected column MultiIndex levels:
    #   - combined: ['scenario', 'property']
    #   - separate: ['{unnamed level}']

    # Load and parse geometry data
    # Relative import from package files:
    path_to_file = files('stroke_maps.data').joinpath(
        'unit_postcodes_coords.csv')
    df_coords = pd.read_csv(path_to_file, index_col='postcode')
    # Index: postcode.
    # Columns: BNG_E, BNG_N, Longitude, Latitude.
    # Add another column level to the coordinates.
    headers = df_units.columns.names
    cols_df_coords = [
        df_coords.columns,                 # property
        ['any'] * len(df_coords.columns),  # scenario
    ]
    if 'subtype' in headers:
        cols_df_coords.append([''] * len(df_coords.columns))
    df_coords = pd.DataFrame(
        df_coords.values,
        index=df_coords.index,
        columns=cols_df_coords
    )
    df_coords.columns.names = headers
    # Merge:
    df_units = pd.merge(
        df_units, df_coords,
        left_index=True, right_index=True,
        how='left')

    x_col = 'BNG_E'
    y_col = 'BNG_N'
    coords_col = 'geometry'

    # Convert to geometry (point):
    # Create coordinates:
    # Current setup means sometimes these columns have different names.
    # TO DO - fix that please! ---------------------------------------------------
    # Extra .values.reshape are to remove the column headings.
    x = df_units[x_col].values.reshape(len(df_units))
    y = df_units[y_col].values.reshape(len(df_units))
    crs = 'EPSG:27700'  # by definition for easting/northing.

    # Convert each pair of coordinates to a Point(x, y).
    df_units[coords_col] = geopandas.points_from_xy(x, y)

    # Convert to GeoDataFrame:
    gdf_units = geopandas.GeoDataFrame(
        df_units, geometry=coords_col, crs=crs)

    return gdf_units


def _load_geometry_transfer_units(df_transfer):
    """
    Create GeoDataFrames of new geometry and existing DataFrames.

    Inputs
    ------
    df_transfer - pd.DataFrame. Unit info.

    Returns
    -------
    gdf_transfer - GeoDataFrame. Unit info and geometry.
    """
    # Selected stroke units names, coordinates, and services.
    # Index column: ['postcode', 'name_nearest_mt']
    # Expected column MultiIndex levels:
    #   - combined: ['scenario', 'property']
    #   - separate: ['{unnamed level}']

    # Load and parse geometry data
    # Relative import from package files:
    path_to_file = files('stroke_maps.data').joinpath(
        'unit_postcodes_coords.csv')
    df_coords = pd.read_csv(path_to_file)
    # Columns: postcode, BNG_E, BNG_N, Longitude, Latitude.

    # From the loaded file:
    x_col = 'BNG_E'
    y_col = 'BNG_N'
    x_col_mt = 'BNG_E_mt'
    y_col_mt = 'BNG_N_mt'
    # To be created here:
    col_unit = 'unit_coords'
    col_tran = 'transfer_coords'
    col_line_coords = ('line_coords', 'any')
    col_line_geometry = ('geometry', 'any')

    # DataFrame of just the arrival and transfer units:
    df_arrival_transfer = df_transfer.index.to_frame(index=False)
    # If there are multiple column levels, only keep the lowest.
    if 'scenario' in df_arrival_transfer.columns.names:
        df_arrival_transfer = (
            df_arrival_transfer.droplevel('scenario', axis='columns'))
    # Index: {generic numbers}
    # Columns: 'from_postcode', 'name_nearest_mt'

    # Merge in the arrival unit coordinates:
    m1 = pd.merge(
        df_arrival_transfer, df_coords,
        left_on='postcode', right_on='postcode',
        how='left'
        )
    m2 = pd.merge(
        m1, df_coords,
        left_on='transfer_unit_postcode', right_on='postcode',
        how='left', suffixes=(None, '_mt')
        )
    df_arrival_transfer = m2.drop(['postcode_mt'], axis='columns')
    # Set the index columns to match the main DataFrame's:
    df_arrival_transfer = df_arrival_transfer.set_index(
        ['postcode', 'transfer_unit_postcode'])
    # Index: 'postcode', 'name_nearest_mt'
    # Columns: BNG_E, BNG_N, Longitude, Latitude,
    #          BNG_E_mt, BNG_N_mt, Longitude_mt, Latitude_mt

    # Add another column level to the coordinates.
    headers = df_transfer.columns.names
    cols_df_arrival_transfer = [
        df_arrival_transfer.columns,                 # property
        ['any'] * len(df_arrival_transfer.columns),  # scenario
    ]
    if 'subtype' in headers:
        cols_df_arrival_transfer.append([''] * len(df_arrival_transfer.columns))
    df_arrival_transfer = pd.DataFrame(
        df_arrival_transfer.values,
        index=df_arrival_transfer.index,
        columns=cols_df_arrival_transfer
    )
    df_arrival_transfer.columns.names = headers

    # Merge this into the main DataFrame:
    df_transfer = pd.merge(
        df_transfer, df_arrival_transfer,
        left_index=True, right_index=True, how='left')

    # Make a column of coordinates [x, y]:
    xy = df_transfer[[x_col, y_col]]
    df_transfer[col_unit] = xy.values.tolist()

    xy_mt = df_transfer[[x_col_mt, y_col_mt]]
    df_transfer[col_tran] = xy_mt.values.tolist()

    # Convert to geometry (line).
    gdf_transfer = create_lines_from_coords(
        df_transfer,
        [col_unit, col_tran],
        col_line_coords,
        col_line_geometry
        )

    return gdf_transfer


def _load_geometry_lsoa(df_lsoa):
    """
    Create GeoDataFrames of new geometry and existing DataFrames.

    Inputs
    ------
    df_lsoa - pd.DataFrame. LSOA info.

    Returns
    -------
    gdf_boundaries_lsoa - GeoDataFrame. LSOA info and geometry.
    """

    # All LSOA shapes:
    gdf_boundaries_lsoa = import_geojson('LSOA11NM')
    # Index column: LSOA11CD.
    # Always has only one unnamed column index level.
    gdf_boundaries_lsoa = gdf_boundaries_lsoa.reset_index()
    gdf_boundaries_lsoa = gdf_boundaries_lsoa.rename(
        columns={'LSOA11NM': 'lsoa', 'LSOA11CD': 'lsoa_code'})
    gdf_boundaries_lsoa = gdf_boundaries_lsoa.set_index(['lsoa', 'lsoa_code'])

    # ----- Prepare separate data -----
    # Set up column level info for the merged DataFrame.
    # Everything needs at least two levels: scenario and property.
    # Sometimes also a 'subtype' level.
    # Add another column level to the coordinates.
    col_level_names = df_lsoa.columns.names
    cols_gdf_boundaries_lsoa = [
        gdf_boundaries_lsoa.columns,                 # property
        ['any'] * len(gdf_boundaries_lsoa.columns),  # scenario
    ]
    if 'subtype' in col_level_names:
        cols_gdf_boundaries_lsoa.append([''] * len(gdf_boundaries_lsoa.columns))

    # Make all data to be combined have the same column levels.
    # Geometry:
    gdf_boundaries_lsoa = pd.DataFrame(
        gdf_boundaries_lsoa.values,
        index=gdf_boundaries_lsoa.index,
        columns=cols_gdf_boundaries_lsoa
    )

    # ----- Create final data -----
    # Merge together all of the DataFrames.
    gdf_boundaries_lsoa = pd.merge(
        gdf_boundaries_lsoa, df_lsoa,
        left_index=True, right_index=True, how='right'
    )
    # Name the column levels:
    gdf_boundaries_lsoa.columns = (
        gdf_boundaries_lsoa.columns.set_names(col_level_names))

    # Sort the results by scenario:
    gdf_boundaries_lsoa = gdf_boundaries_lsoa.sort_index(
        axis='columns', level='scenario')

    # Convert to GeoDataFrame:
    # Set geometry:
    col_geometry = find_multiindex_column_names(
        gdf_boundaries_lsoa, property=['geometry'])
    geo_series = gdf_boundaries_lsoa[col_geometry].values.flatten()
    gdf_boundaries_lsoa = geopandas.GeoDataFrame(
        gdf_boundaries_lsoa,
        geometry=geo_series
        )

    return gdf_boundaries_lsoa


def _load_geometry_catchment(
        gdf_boundaries_lsoa,
        df_transfer=None
        ):
    """
    Create GeoDataFrames of LSOA grouped by unit catchment area.

    Inputs
    ------
    gdf_boundaries_lsoa - GeoDataFrame. LSOA info including units.
    df_transfer - pd.DataFrame. Transfer unit info. Used in colour
                  selection to make units with the same transfer
                  unit share a colour.

    Returns
    -------
    gdf_boundaries_catchment - GeoDataFrame. Catchment area
                               info and geometry.
    """
    # List of scenarios included in the LSOA data:
    scenario_list = sorted(list(set(
        gdf_boundaries_lsoa.columns.get_level_values('scenario'))))
    scenario_list.remove('any')

    # Store resulting polygons in here:
    dfs_to_merge = {}

    # For each scenario:
    for scenario in scenario_list:
        if scenario.startswith('diff'):
            pass
        else:
            col_to_dissolve = find_multiindex_column_names(
                gdf_boundaries_lsoa,
                property=['unit_postcode'], scenario=[scenario])
            col_geometry = find_multiindex_column_names(
                gdf_boundaries_lsoa, property=['geometry'])
            col_selected = find_multiindex_column_names(
                gdf_boundaries_lsoa,
                property=['selected'], scenario=[scenario])

            # Which ones are selected?
            mask = gdf_boundaries_lsoa[[col_selected]] == 1
            selected_units = gdf_boundaries_lsoa.loc[
                mask.values, [col_to_dissolve]]

            selected_units = list(set(list(selected_units.values.flatten())))

            df = _combine_lsoa_into_catchment_shapes(
                gdf_boundaries_lsoa,
                col_to_dissolve=col_to_dissolve,
                col_geometry=col_geometry,
                col_after_dissolve='unit'
                )
            df['selected'] = 0
            mask = df.index.isin(selected_units)
            df.loc[mask, 'selected'] = 1
            # Which ones are used in this scenario?
            df['use'] = 1

            # Set index column:
            df = df.reset_index()

            # Assign colours:
            df = assign_colours_to_regions(df, col_col='colour_ind')

            if df_transfer is None:
                pass
            else:
                df_transfer_here = df_transfer.copy().reset_index()
                # Only keep this scenario:
                # TO DO - update these column names? ----------------------------------------------
                df_transfer_here = df_transfer_here[
                    [('postcode', ''), ('transfer_unit_postcode', ''),
                     ('selected', scenario)]]
                # Drop the 'scenario' level
                df_transfer_here = df_transfer_here.droplevel(
                    'scenario', axis='columns')
                # Only keep used postcodes:
                mask = ~df_transfer_here['selected'].isna()  # == 1
                df_transfer_here = df_transfer_here.loc[mask].copy()
                # Add the transfer unit postcodes to the main df.
                df = pd.merge(
                    df, df_transfer_here[
                        ['postcode', 'transfer_unit_postcode']],
                    left_on='unit', right_on='postcode', how='left'
                )
                df = df.drop('postcode', axis='columns')
                # Group shapes by transfer unit and then assign colours
                # to the groups.
                # Only run this on selected rows of df.
                col_to_dissolve = 'transfer_unit_postcode'
                col_geometry = 'geometry'
                df_feeders = _combine_lsoa_into_catchment_shapes(
                    df[df['use'] == 1].copy(),
                    col_to_dissolve=col_to_dissolve,
                    col_geometry=col_geometry,
                    col_after_dissolve='transfer_unit_postcode'
                    )
                df_feeders = df_feeders.reset_index()
                # Assign colours:
                df_feeders = assign_colours_to_regions(
                    df_feeders, col_col='transfer_colour_ind',
                    col_units='transfer_unit_postcode'
                    )
                # Link these colours back to the original dataframe:
                df = pd.merge(
                    df, df_feeders[
                        ['transfer_unit_postcode', 'transfer_colour_ind']],
                    on='transfer_unit_postcode', how='left'
                )

            df = df.set_index(['unit', 'geometry'])

            # Store in the main list:
            dfs_to_merge[scenario] = df

    # Can't concat without index columns.
    gdf_boundaries_catchment = pd.concat(
        dfs_to_merge.values(),
        axis='columns',
        keys=dfs_to_merge.keys(),  # Names for extra index row
        )
    # The combo dataframe contains only columns for scenario / property,
    # so switch them round to property / scenario:
    gdf_boundaries_catchment.columns = (
        gdf_boundaries_catchment.columns.swaplevel(0, 1))
    # Rename index so it can be made into a normal column:
    gdf_boundaries_catchment = gdf_boundaries_catchment.rename(
        index={gdf_boundaries_catchment.index.name: (col_to_dissolve)})
    gdf_boundaries_catchment = gdf_boundaries_catchment.reset_index()
    # Give the new, useless index a name.
    gdf_boundaries_catchment.index.name = 'id'

    col_level_names = ['property', 'scenario']
    # Name the column levels:
    gdf_boundaries_catchment.columns = (
        gdf_boundaries_catchment.columns.set_names(col_level_names))

    # Set geometry column:
    gdf_boundaries_catchment = gdf_boundaries_catchment.set_geometry(
        'geometry')

    return gdf_boundaries_catchment


def _combine_lsoa_into_catchment_shapes(
        gdf,
        col_to_dissolve,
        col_geometry='geometry',
        col_after_dissolve='dissolve'
        ):
    """
    Blob together LSOA geometry that shares a catchment unit.

    Inputs
    ------
    gdf                - GeoDataFrame. With geometry to be blobbed.
    col_to_dissolve    - str / tuple. Column name to blob.
    col_geometry       - str / tuple. Column name for geometry.
    col_after_dissolve - str / tuple. Column name for final data.

    Returns
    -------
    gdf2 - GeoDataFrame. With blobbed geometry.
    """
    # Copy to avoid pandas shenanigans.
    gdf = gdf.copy()
    # Assuming that index contains stuff to be dissolved,
    # it doesn't make sense to keep it afterwards.
    # Make it a normal column so it can be neglected.
    gdf = gdf.reset_index()
    # Make a fresh dataframe with no column multiindex:
    gdf2 = pd.DataFrame(
        gdf[[col_to_dissolve, col_geometry]].values,
        columns=[col_after_dissolve, 'geometry']
    )
    gdf2 = geopandas.GeoDataFrame(gdf2, geometry='geometry')
    gdf2 = gdf2.dissolve(by=col_after_dissolve)
    return gdf2


# ############################
# ##### HELPER FUNCTIONS #####
# ############################
def create_lines_from_coords(
        df,
        cols_with_coords,
        col_coord,
        col_geom
        ):
    """
    Convert DataFrame with coords to GeoDataFrame with LineString.

    Initially group coordinates from multiple columns into one:
    +--------+--------+       +------------------+
    |  col1  |  col2  |       |   line_coords    |
    +--------+--------+  -->  +------------------+
    | [a, b] | [c, d] |       | [[a, b], [c, d]] |
    +--------+--------+       +------------------+
    And convert the single column into shapely.LineString objects
    with associated crs. Then convert the input DataFrame into
    a GeoDataFrame with the new Line objects.

    Inputs
    ------
    df               - pd.DataFrame. Contains some coordinates.
    cols_with_coords - list. List of column names in df that contain
                       coordinates for making lines.
    col_coord        - str / tuple. Resulting column containing
                       coordinates.
    col_geom         - str / tuple. Resulting column containing
                       geometry.

    Returns
    -------
    gdf - GeoDataFrame. The input df with the new Line
          geometry objects and converted to a GeoDataFrame.
    """
    # Combine multiple columns of coordinates into a single column
    # with a list of lists of coordinates:
    df[col_coord] = df[cols_with_coords].values.tolist()

    # Drop any duplicates:
    df = df.drop_duplicates(col_coord)

    # Convert line coords to LineString objects:
    df[col_geom] = [LineString(coords) for coords in df[col_coord].values]

    # Convert to GeoDataFrame:
    gdf = geopandas.GeoDataFrame(df, geometry=col_geom)  # crs="EPSG:4326"
    # if isinstance(col_geom, tuple):
    #     gdf['geometry']
    # TO DO - implement CRS explicitly ---------------------------------------------
    return gdf


def create_combo_cols(gdf, scenario):
    """
    Combine columns from two scenarios to make data for diff columns.

    When dataframe doesn't have the diff_this_minus_that columns,
    use this function to create that data and prevent KeyError later.

    TO DO - currently the combo column takes the max of both.
    This is good for stroke units (yes in drip and ship vs no in mothership)
    but bad for regions catching LSOA (outcome diff is NaN when not in both,
    so the regions contain no info).
    Allow selection of min and max. (Or anything else?)

    Inputs
    ------
    gdf      - GeoDataFrame. With data from multiple scenarios.
    scenario - str. The diff scenario name,
               diff_scenario1_minus_scenario2.

    Returns
    -------
    gdf - GeoDataFrame. The input data with added diff columns.
    """
    # Find out what diff what:
    scen_bits = scenario.split('_')
    # Assume scenario = diff_scenario1_minus_scenario2:
    scen1 = scen_bits[1]
    scen2 = scen_bits[3]

    cols_to_combine = gdf.xs(scen1, axis='columns', level='scenario',
                             drop_level=False).columns.to_list()

    # Which column levels exist?
    col_level_names = gdf.columns.names
    # Where is scenario?
    i_scen = col_level_names.index('scenario')

    for col in cols_to_combine:
        numerical_bool = is_numeric_dtype(gdf[col])
        if numerical_bool:
            scen_col = list(col)
            scen_col[i_scen] = scenario
            scen_col = tuple(scen_col)

            scen1_col = list(col)
            scen1_col[i_scen] = scen1
            scen1_col = tuple(scen1_col)

            scen2_col = list(col)
            scen2_col[i_scen] = scen2
            scen2_col = tuple(scen2_col)

            try:
                gdf[scen_col] = gdf[[scen1_col, scen2_col]].max(axis='columns')
            except KeyError:
                # Drop the subtype:
                # scen_col = scen_col[:-1]
                scen1_col = scen1_col[:-1]
                scen2_col = scen2_col[:-1]
                gdf_here = gdf.copy()
                gdf_here.columns = gdf_here.columns.droplevel('subtype')
                gdf[scen_col] = gdf_here[[scen1_col, scen2_col]
                                         ].max(axis='columns')
        else:
            # Don't combine non-numerical columns.
            pass
    return gdf


def fill_blank_level(
        gdf,
        level='scenario',
        fill_value='any'
        ):
    """
    Fill empty column MultiIndex level headings with some string.

    Inputs
    ------
    gdf        - GeoDataFrame. Expect to have MultiIndex columns.
    level      - str. The column level name to check.
    fill_value - str. What to fill empty entries with.

    Returns
    -------
    gdf - GeoDataFrame. The input data with any empty column names
          filled.
    """
    # Get level names:
    level_names = gdf.columns.names

    try:
        scenario_list = list(set(gdf.columns.get_level_values(level)))
    except KeyError:
        # Nothing to do here.
        return gdf

    scenarios_to_update = [
        scenario for scenario in scenario_list if
        ((scenario == '') | (scenario.startswith('Unnamed')))
        ]

    # Which column levels exist?
    col_level_names = gdf.columns.names
    # Where is scenario?
    i_scen = col_level_names.index(level)

    new_columns = []
    for scen_col in gdf.columns:
        if scen_col[i_scen] in scenarios_to_update:
            scen_col = list(scen_col)
            scen_col[i_scen] = fill_value
            scen_col = tuple(scen_col)
        else:
            # Don't update the column name.
            pass

        # Only store the level part:
        new_columns.append(scen_col)

    gdf.columns = pd.MultiIndex.from_tuples(new_columns)
    gdf.columns = gdf.columns.set_names(level_names)

    return gdf


# ###################
# ##### COLOURS #####
# ###################
def assign_colours_to_regions(
        gdf,
        col_col,
        col_units='unit'
        ):
    """
    Assign colours to boundaries so neighbours have different colours.

    This assigns an integer to each boundary. These integers can be
    used later with a list of colours to sample the list.

    Inputs
    ------
    gdf       - GeoDataFrame. Contains geometry to assign colours to.
    col_col   - str / tuple. Name of the column to contain the
                colour index results.
    col_units - str / tuple. Name of the column that contains
                unit postcodes for labelling the catchment areas.

    Returns
    -------
    gdf - GeoDataFrame. The input data with added colour index column.
    """
    gdf = find_neighbours_for_regions(gdf, col_units)
    gdf = gdf.sort_values('total_neighbours', ascending=False)

    def fill_colour_grid(n_colours=4):
        colours = range(n_colours)

        neighbour_list = gdf[col_units].tolist()

        neighbour_grid = np.full((len(gdf), len(gdf)), False)
        for row, neighbour_list_here in enumerate(gdf['neighbour_list']):
            for n in neighbour_list_here:
                col = neighbour_list.index(n)
                neighbour_grid[row, col] = True
                neighbour_grid[col, row] = True

        # Make a grid. One column per colour, one row per region.
        colour_grid = np.full((len(gdf), len(colours)), True)
        # To index row x: colour_grid[x, :]
        # To index col x: colour_grid[:, x]

        for row, region in enumerate(neighbour_list):
            # Which colours can this be?
            colours_here = colour_grid[row, :]

            # Pick the first available colour.
            ind_to_pick = np.where(colours_here == True)[0][0]

            # Update its neighbours' colour information.
            rows_neighbours = np.where(neighbour_grid[row, :] == True)[0]
            # Only keep these rows when we haven't checked them yet:
            rows_neighbours = [r for r in rows_neighbours if r > row]
            colour_grid[rows_neighbours, ind_to_pick] = False

            # Update its own colour information.
            colour_grid[row, :] = False
            colour_grid[row, ind_to_pick] = True
        return colour_grid

    # Use way more colours than will be needed.
    n_colours = len(gdf)
    colour_grid = fill_colour_grid(n_colours)

    # Use the bool colour grid to assign colours:
    colours = range(n_colours)
    colour_arr = np.full(len(gdf), colours[0], dtype=object)
    for i, colour in enumerate(colours):
        colour_arr[np.where(colour_grid[:, i] == True)] = colour

    # Add to the DataFrame:
    gdf[col_col] = colour_arr

    # If the 'random' column was created, delete it:
    try:
        gdf = gdf.drop('random', axis='columns')
    except KeyError:
        # Nothing to delete.
        pass

    return gdf


def find_neighbours_for_regions(df, col_units='unit'):
    """
    Find which boundaries border each other.

    Inputs
    ------
    df        - GeoDataFrame. Contains geometry to be compared.
    col_units - str / tuple. The name of the column with unit postcodes
                that are used to label the neighbouring regions.

    Returns
    -------
    df - GeoDataFrame. The input data with added columns for which
         regions border each row of data and how many neighbours
         there are.
    """

    dict_neighbours = {}

    for index, row in df.iterrows():
        unit_here = row[col_units]
        geometry_here = row['geometry']
        # Does this intersect any other polygon in the list?
        intersect = df['geometry'].intersects(geometry_here)
        # Get the unit names of those it intersects:
        units_intersect = df.loc[(intersect == 1), col_units].values.tolist()
        # Remove itself from the list:
        units_intersect.remove(unit_here)
        # Store unit list in dict:
        dict_neighbours[unit_here] = units_intersect

    # Convert dict to Series:
    series_n = pd.Series(dict_neighbours, name='neighbour_list')
    series_n.index = series_n.index.set_names(col_units)
    series_n = series_n.reset_index()
    # Merge into the main dataframe:
    df = pd.merge(df, series_n, on=col_units)

    # Record the number of neighbours:
    df['total_neighbours'] = df['neighbour_list'].str.len()
    return df
