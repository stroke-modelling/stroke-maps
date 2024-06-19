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
import stroke_maps.load_data


def make_geometry_transfer_units(df_transfer):
    """
    Create GeoDataFrames of new geometry and existing DataFrames.

    Inputs
    ------
    df_transfer - pd.DataFrame. Unit info.

    Returns
    -------
    gdf_transfer - GeoDataFrame. Unit info and geometry.
    """
    # Load in the stroke unit coordinates:
    gdf_units = stroke_maps.load_data.stroke_unit_coordinates()

    # Make dataframe of just the starting units and their coordinates:
    gdf_start_units = pd.merge(
        pd.Series(df_transfer.index), gdf_units,
        left_on='postcode', right_index=True, how='left'
    )

    # Make dataframe of just the end units and their coordinates:
    end_postcodes = pd.Series(
        df_transfer['transfer_unit_postcode'].values,
        name='transfer_unit_postcode'
        )
    gdf_end_units = pd.merge(
        end_postcodes, gdf_units,
        left_on='transfer_unit_postcode', right_index=True, how='left'
    ).drop_duplicates()

    # Merge the coordinates of the start and end units
    # into the transfer dataframe:
    df_transfer_coords = df_transfer.reset_index().copy()
    # Merge in the start unit coordinates:
    df_transfer_coords = pd.merge(
        df_transfer_coords, gdf_start_units[['postcode', 'BNG_E', 'BNG_N']],
        on='postcode', how='left'
    )
    # Merge in the end unit coordinates:
    df_transfer_coords = pd.merge(
        df_transfer_coords,
        gdf_end_units[['transfer_unit_postcode', 'BNG_E', 'BNG_N']],
        on='transfer_unit_postcode', how='left', suffixes=[None, '_transfer']
    )

    # Make a column of coordinates [x, y]:
    xy = df_transfer_coords[['BNG_E', 'BNG_N']]
    df_transfer_coords['coords_start'] = xy.values.tolist()
    xy_mt = df_transfer_coords[['BNG_E_transfer', 'BNG_N_transfer']]
    df_transfer_coords['coords_end'] = xy_mt.values.tolist()

    # Convert to geometry (line).
    gdf_transfer = create_lines_from_coords(
        df_transfer_coords,
        ['coords_start', 'coords_end'],
        'coords_start_end',
        'geometry'
        )
    return gdf_transfer


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
