"""
Draw some maps using GeoDataFrames from the Catchment data.

crs reference:
+ EPSG:4326  - longitude / latitude.
+ CRS:84     - same as EPSG:4326.
+ EPSG:27700 - British National Grid (BNG).
"""
import matplotlib.pyplot as plt
import pandas as pd
from shapely.geometry import Polygon  # For extent box.
import geopandas
import numpy as np
from pandas.api.types import is_numeric_dtype  # For checking dtype.

import stroke_maps.plot_functions as maps  # for plotting.


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
