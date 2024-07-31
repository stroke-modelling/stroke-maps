"""
Combine Catchment data with geometry to make GeoDataFrames for plots.

crs reference:
+ EPSG:4326  - longitude / latitude.
+ CRS:84     - same as EPSG:4326.
+ EPSG:27700 - British National Grid (BNG).
"""
import pandas as pd
import geopandas
from shapely.geometry import Polygon  # For extent box.
from shapely import LineString  # For creating line geometry.

import stroke_maps.load_data


def make_geometry_transfer_units(df_transfer, use_northern_ireland=False):
    """
    Create GeoDataFrames of new geometry and existing DataFrames.

    Inputs
    ------
    df_transfer - pd.DataFrame. Unit info. Should have index
                  named 'postcode' containing stroke units and
                  a column 'transfer_unit_postcode' containing
                  their transfer units.

    Returns
    -------
    gdf_transfer - GeoDataFrame. Unit info and geometry.
    """
    # Load in the stroke unit coordinates:
    if use_northern_ireland:
        gdf_units = stroke_maps.load_data.stroke_unit_coordinates_ni()
        easting_col = 'easting'
        northing_col = 'northing'
    else:
        gdf_units = stroke_maps.load_data.stroke_unit_coordinates()
        easting_col = 'BNG_E'
        northing_col = 'BNG_N'

    # Pick out the column name for postcodes:
    postcode_col = df_transfer.index.name

    # Make dataframe of just the starting units and their coordinates:
    gdf_start_units = pd.merge(
        pd.Series(df_transfer.index), gdf_units,
        left_on=postcode_col, right_index=True, how='left'
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
        df_transfer_coords,
        gdf_start_units[[postcode_col, easting_col, northing_col]],
        on=postcode_col, how='left'
    )
    # Merge in the end unit coordinates:
    df_transfer_coords = pd.merge(
        df_transfer_coords,
        gdf_end_units[['transfer_unit_postcode', easting_col, northing_col]],
        on='transfer_unit_postcode', how='left', suffixes=[None, '_transfer']
    )

    # Make a column of coordinates [x, y]:
    xy = df_transfer_coords[[easting_col, northing_col]]
    df_transfer_coords['coords_start'] = xy.values.tolist()
    xy_mt = df_transfer_coords[[f'{easting_col}_transfer',
                                f'{northing_col}_transfer']]
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


def combine_regions(
        gdf,
        col_to_dissolve,
        ):
    """
    Wrapper for geopandas dissolve.

    Example use: blob together LSOA geometry that shares a catchment unit.

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
    # Drop columns that won't make sense after dissolve:
    gdf = gdf[[col_to_dissolve, 'geometry']]
    gdf = gdf.dissolve(by=col_to_dissolve)
    return gdf


def filter_gdf_by_columns(gdf, col_names):
    """
    Only take selected columns and rows where any value is 1.

    Use this to only keep certain parts of the GeoDataFrame,
    e.g. selected units.

    Inputs
    ------
    gdf - GeoDataFrame. To be filtered.
    col_names = list. Column names to keep.

    Returns
    -------
    gdf_reduced - GeoDataFrame. The requested subset of values.
    """
    # Which columns do we want?
    cols = gdf.columns.get_level_values('property').isin(col_names)
    # Subset of only these columns:
    gdf_selected = gdf.loc[:, cols]
    # Mask rows where any of these columns equal 1:
    mask = (gdf_selected == 1).any(axis='columns')
    # Only keep those rows:
    gdf_reduced = gdf.copy()[mask]
    return gdf_reduced


def get_selected_area_extent(
        gdf_selected,
        leeway=10000,
        ):
    """
    What is the spatial extent of everything in this GeoDataFrame?

    Inputs
    ------
    gdf_selected - GeoDataFrame.
    leeway       - float. Padding space around the edge of
                   the plots from the outermost thing of
                   interest. Units to match gdf units.

    Returns
    -------
    box        - polygon. The box we'll crop gdfs to.
    map_extent - list. [minx, maxx, miny, maxy] axis coordinates.
    """
    minx, miny, maxx, maxy = gdf_selected.geometry.total_bounds
    # Give this some leeway:
    minx -= leeway
    miny -= leeway
    maxx += leeway
    maxy += leeway
    map_extent = [minx, maxx, miny, maxy]
    # Turn the points into a box:
    box = Polygon((
        (minx, miny),
        (minx, maxy),
        (maxx, maxy),
        (maxx, miny),
        (minx, miny),
    ))
    return box, map_extent


def keep_only_geometry_in_box(gdf, box):
    """
    Keep only rows of this gdf that intersect the box.

    If a region is partly in and partly outside the box,
    it will be included in the output gdf.

    Inputs
    ------
    gdf - GeoDataFrame.
    box - polygon.

    Returns
    -------
    gdf - GeoDataFrame. Input data reduced to only rows that
          intersect the box.
    """
    mask = gdf.geometry.intersects(box)
    gdf = gdf[mask]
    return gdf


def restrict_geometry_edges_to_box(gdf, box):
    """
    Clip polygons to the given box.

    Inputs
    ------
    gdf - GeoDataFrame.
    box - polygon.

    Returns
    -------
    gdf - GeoDataFrame. Same as the input gdf but cropped so nothing
          outside the box exists.
    """
    gdf.geometry = gdf.geometry.intersection(box)
    return gdf


def _assign_label_coords_to_regions(gdf, col_point_label):
    """
    Assign coordinates for labels of region short codes.

    Inputs
    ------
    gdf             - GeoDataFrame.
    col_point_label - name of the column to place coords in.

    Returns
    -------
    gdf - GeoDataFrame. Same as input but with added coordinates.
    """
    # Get coordinates for where to plot each label:
    point_label = ([poly.representative_point() for
                    poly in gdf.geometry])
    gdf[col_point_label] = point_label
    return gdf
