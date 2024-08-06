"""
Functions to import package data.

Most of the data files included in stroke-maps are useful
in many other places, so these functions provide a quick way
to get at the data.
"""
import pandas as pd
import geopandas as gpd
from importlib_resources import files


# ################################
# ##### STROKE UNIT SERVICES #####
# ################################

def ni_stroke_unit_services():
    """
    Import data with Northern Irish units and ivt/mt services.
    """
    # Relative import from package files:
    path_to_file = files('stroke_maps').joinpath('data_ni').joinpath(
        'hospitals.csv')
    df = pd.read_csv(path_to_file, index_col='Postcode')
    return df


# #########################
# ##### REGION LOOKUP #####
# #########################

def stroke_unit_region_lookup():
    """
    Import data linking stroke units to geographical regions.
    """
    # Relative import from package files:
    path_to_file = files('stroke_maps').joinpath('data').joinpath(
        'stroke_units_regions.csv')
    df = pd.read_csv(path_to_file, index_col='postcode')
    return df


def lsoa_region_lookup():
    """
    Import data linking LSOA to geographical regions.

    This file contains only LSOA to SICBL (England) and LHB (Wales).
    To link those to other regions, import the region lookup file
    using the function region_lookup().
    """
    # Relative import from package files:
    path_to_file = files('stroke_maps').joinpath('data').joinpath(
        'regions_lsoa_ew.csv')
    df = pd.read_csv(path_to_file, index_col=['lsoa', 'lsoa_code'])
    return df


def region_lookup():
    """
    Import data linking geographical regions.

    The index is a multiindex of region (SICBL/LHB) name and code.
    """
    # Relative import from package files:
    path_to_file = files('stroke_maps').joinpath('data').joinpath(
        'regions_ew.csv')
    df = pd.read_csv(path_to_file, index_col=['region', 'region_code'])
    return df


def ambulance_lsoa_lookup():
    """
    Import data linking LSOA to ambulance service catchment areas.

    The index is LSOA code. The columns are LSOA name, ambulance
    catchment in 2021, and ambulance catchment in 2022.
    """
    # Relative import from package files:
    path_to_file = files('stroke_maps').joinpath('data').joinpath(
        'lsoa_ambo_lookup.csv')
    df = pd.read_csv(path_to_file, index_col='LSOA11CD')
    return df


def ambulance_ccg15_lookup():
    """
    Import data linking CCG in 2015 to ambulance service.

    The index is CCG 2015 name and the column is ambulance
    catchment in 2021.
    """
    # Relative import from package files:
    path_to_file = files('stroke_maps').joinpath('data').joinpath(
        'ccg15_amb.csv')
    df = pd.read_csv(path_to_file, index_col='ccg15nm').squeeze()
    # squeeze() to convert from dataframe to series.
    return df


def ambulance_name_lookup():
    """
    Import data linking ambulance service codes with names.

    The index is ambulance code used in the other ambo files here
    and the column is the fuller name of the service.
    """
    # Relative import from package files:
    path_to_file = files('stroke_maps').joinpath('data').joinpath(
        'ambulance_service_names.csv')
    df = pd.read_csv(path_to_file, index_col='ambulance_service').squeeze()
    # squeeze() to convert from dataframe to series.
    return df


# ########################
# ##### TRAVEL TIMES #####
# ########################

def travel_time_matrix_lsoa():
    """
    Import travel time matrix for each LSOA to each stroke unit.

    Each column is a postcode of a stroke team and
    each row is an LSOA name (LSOA11NM).
    """
    # Relative import from package files:
    path_to_file = files('stroke_maps').joinpath('data').joinpath(
        'lsoa_travel_time_matrix_calibrated.csv')
    df = pd.read_csv(path_to_file, index_col='LSOA')
    return df


def travel_time_matrix_units():
    """
    Import travel time matrix for each stroke unit to each other.

    Each row index is a postcode of a stroke team and
    each column name is a stroke team.
    """
    # Relative import from package files:
    path_to_file = files('stroke_maps').joinpath('data').joinpath(
        'inter_hospital_time_calibrated.csv')
    df = pd.read_csv(path_to_file, index_col='from_postcode')
    return df


def travel_time_matrix_ni_areas():
    """
    Import travel time matrix for Northern Ireland areas to units.

    Each column is a postcode of a stroke team and
    each row is a 2011 Small Area name (SA).
    """
    # Relative import from package files:
    path_to_file = files('stroke_maps').joinpath('data_ni').joinpath(
        'travel_matrix.csv')
    df = pd.read_csv(path_to_file, index_col='from_postcode')
    return df


def travel_time_matrix_ni_units():
    """
    Import travel time matrix between Northern Ireland stroke units.

    Each row index is a postcode of a stroke team and
    each column name is a stroke team.
    """
    # Relative import from package files:
    path_to_file = files('stroke_maps').joinpath('data_ni').joinpath(
        'inter_hospital_time.csv')
    df = pd.read_csv(path_to_file, index_col='from_postcode')
    return df


# ############################
# ##### UNIT COORDINATES #####
# ############################

def stroke_unit_coordinates():
    """
    Import stroke unit coordinates.

    Index: postcode.
    Columns: BNG_E, BNG_N, Longitude, Latitude.
    """
    # Relative import from package files:
    path_to_file = files('stroke_maps').joinpath('data').joinpath(
        'unit_postcodes_coords.csv')
    df = pd.read_csv(path_to_file, index_col='postcode')

    # Convert lists of coordinates to geometry points.
    # Use the British National Grid coordinates:
    x_col = 'BNG_E'  # Easting
    y_col = 'BNG_N'  # Northing
    # Which has this coordinates reference system by definition:
    crs = 'EPSG:27700'
    # And store the results in a column called 'geometry':
    coords_col = 'geometry'

    # Pick out lists of the coordinates:
    # Extra .values.reshape are to remove the column headings.
    x = df[x_col].values.reshape(len(df))
    y = df[y_col].values.reshape(len(df))

    # Convert each pair of coordinates to a Point(x, y).
    df[coords_col] = gpd.points_from_xy(x, y)

    # Convert to GeoDataFrame:
    gdf_units = gpd.GeoDataFrame(df, geometry=coords_col, crs=crs)

    return gdf_units


def stroke_unit_coordinates_ni():
    """
    Import Northern Ireland stroke unit coordinates.

    Index: postcode.
    Columns: BNG_E, BNG_N, Longitude, Latitude.
    """
    # Relative import from package files:
    path_to_file = files('stroke_maps').joinpath('data_ni').joinpath(
        'hospital_coords.csv')
    df = pd.read_csv(path_to_file, index_col='Postcode')

    # Convert lists of coordinates to geometry points.
    # Use the Irish Grid coordinates:
    x_col = 'easting'
    y_col = 'northing'
    # Which has this coordinates reference system by definition:
    crs = 'EPSG:29902'
    # And store the results in a column called 'geometry':
    coords_col = 'geometry'

    # Pick out lists of the coordinates:
    # Extra .values.reshape are to remove the column headings.
    x = df[x_col].values.reshape(len(df))
    y = df[y_col].values.reshape(len(df))

    # Convert each pair of coordinates to a Point(x, y).
    df[coords_col] = gpd.points_from_xy(x, y)

    # Convert to GeoDataFrame:
    gdf_units = gpd.GeoDataFrame(df, geometry=coords_col, crs=crs)

    return gdf_units


# ############################
# ##### COUNTRY OUTLINES #####
# ############################

def england_outline():
    """
    Import England boundaries in British National Grid crs.
    """
    # Relative import from package files:
    path_to_file = files('stroke_maps').joinpath('data').joinpath(
        'outline_England.geojson')
    gdf = gpd.read_file(path_to_file)
    return gdf


def wales_outline():
    """
    Import Wales boundaries in British National Grid crs.
    """
    # Relative import from package files:
    path_to_file = files('stroke_maps').joinpath('data').joinpath(
        'outline_Wales.geojson')
    gdf = gpd.read_file(path_to_file)
    return gdf


def englandwales_outline():
    """
    Import England boundaries in British National Grid crs.
    """
    # Relative import from package files:
    path_to_file = files('stroke_maps').joinpath('data').joinpath(
        'outline_EnglandWales.geojson')
    gdf = gpd.read_file(path_to_file)
    return gdf


def ni_outline():
    """
    Import Northern Irish boundaries in Irish Grid crs.
    """
    # Relative import from package files:
    path_to_file = files('stroke_maps').joinpath('data_ni').joinpath(
        'OSNI_Open_Data_-_50K_Boundaries_-_NI_Outline.geojson')
    gdf = gpd.read_file(path_to_file)

    # Convert to Irish grid coordinate system:
    gdf = gdf.to_crs('EPSG:29902')
    return gdf


# #########################
# ##### AREA OUTLINES #####
# #########################
def lsoa_geography():
    """
    Import LSOA boundaries.
    """
    # Relative import from package files:
    path_to_file = files('stroke_maps').joinpath('data').joinpath(
        'LSOA.geojson')
    gdf = gpd.read_file(path_to_file)
    return gdf


def sicbl_geography():
    """
    Import sub-Integrated Care Board Locations boundaries for England.
    """
    # Relative import from package files:
    path_to_file = files('stroke_maps').joinpath('data').joinpath(
        'SICBL.geojson')
    gdf = gpd.read_file(path_to_file)
    return gdf


def lhb_geography():
    """
    Import Local Health Board boundaries for Wales.
    """
    # Relative import from package files:
    path_to_file = files('stroke_maps').joinpath('data').joinpath(
        'LHB.geojson')
    gdf = gpd.read_file(path_to_file)
    return gdf


def isdn_geography():
    """
    Import Integrated Stroke Delivery Network boundaries for England.
    """
    # Relative import from package files:
    path_to_file = files('stroke_maps').joinpath('data').joinpath(
        'outline_isdn.geojson')
    gdf = gpd.read_file(path_to_file)
    return gdf


def ambulance21_geography():
    """
    Import ambulance service 2021 boundaries for England and Wales.
    """
    # Relative import from package files:
    path_to_file = files('stroke_maps').joinpath('data').joinpath(
        'ambulance_catchment_2021.geojson')
    gdf = gpd.read_file(path_to_file)
    return gdf


def ambulance22_geography():
    """
    Import ambulance service 2022 boundaries for England and Wales.
    """
    # Relative import from package files:
    path_to_file = files('stroke_maps').joinpath('data').joinpath(
        'ambulance_catchment_2022.geojson')
    gdf = gpd.read_file(path_to_file)
    return gdf


def ni_sa_geography():
    """
    Import Northern Irish Small Area (SA) boundaries.
    """
    # Relative import from package files:
    path_to_file = files('stroke_maps').joinpath('data_ni').joinpath(
        'sa2011.json')
    gdf = gpd.read_file(path_to_file)
    # This file doesn't automatically set the right coordinate
    # reference system of EPSG:29902 (Irish Grid) so force it now:
    gdf = gdf.set_crs('EPSG:29902', allow_override=True)
    return gdf


def ni_county_geography():
    """
    Import Northern Irish county boundaries.
    """
    # Relative import from package files:
    path_to_file = files('stroke_maps').joinpath('data_ni').joinpath(
        'OSNI_Open_Data_-_50K_Boundaries_-_NI_Counties.geojson')
    gdf = gpd.read_file(path_to_file)
    return gdf
