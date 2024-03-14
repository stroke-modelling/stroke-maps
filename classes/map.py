import matplotlib.pyplot as plt
import pandas as pd
from shapely.geometry import Polygon # For extent box.
import geopandas

import classes.map_functions as maps  # for plotting.

# ##########################
# ##### DATA WRANGLING #####
# ##########################
def crop_data_to_shared_extent(
        gdf_boundaries_regions,
        gdf_points_units,
        gdf_boundaries_catchment,
        gdf_boundaries_lsoa,
        gdf_lines_transfer=None,
        leeway=20000
        ):
    # Find a shared axis extent for all GeoDataFrames.
    # Draw a box that just contains everything useful in all gdf,
    # then extend it a little bit for a buffer.
    box, map_extent = find_shared_map_extent(
        gdf_boundaries_regions,
        gdf_points_units,
        gdf_boundaries_catchment,
        gdf_lines_transfer,
        leeway
        )

    # Restrict all gdf to only geometry that falls within this box.
    gdf_boundaries_regions = _keep_only_geometry_in_box(
        gdf_boundaries_regions, box)
    gdf_points_units = _keep_only_geometry_in_box(
        gdf_points_units, box)
    gdf_boundaries_catchment = _keep_only_geometry_in_box(
        gdf_boundaries_catchment, box)
    gdf_boundaries_lsoa = _keep_only_geometry_in_box(
        gdf_boundaries_lsoa, box)

    if gdf_lines_transfer is None:
        pass
    else:
        gdf_lines_transfer = _keep_only_geometry_in_box(
            gdf_lines_transfer, box)

    # Crop any region boundaries that might extend outside the box.
    gdf_boundaries_regions = _restrict_geometry_edges_to_box(
        gdf_boundaries_regions, box)
    gdf_boundaries_catchment = _restrict_geometry_edges_to_box(
        gdf_boundaries_catchment, box)

    # Create labels *after* choosing the map
    # extent and restricting the regions to the edges of the box.
    # Otherwise labels could appear outside the plot.
    gdf_boundaries_regions = _assign_label_coords_to_regions(
        gdf_boundaries_regions, 'point_label')

    to_return = (
        gdf_boundaries_regions,
        gdf_points_units,
        gdf_boundaries_catchment,
        gdf_boundaries_lsoa,
        gdf_lines_transfer
        )
    return to_return


def filter_gdf_by_columns(gdf, col_names):
    # Which columns do we want?
    cols = gdf.columns.get_level_values('property').isin(col_names)
    # Subset of only these columns:
    gdf_selected = gdf.loc[:, cols]
    # Mask rows where any of these columns equal 1:
    mask = (gdf_selected == 1).any(axis='columns')
    # Only keep those rows:
    gdf_reduced = gdf.copy()[mask]
    return gdf_reduced


def find_shared_map_extent(
        gdf_boundaries_regions,
        gdf_points_units,
        gdf_boundaries_catchment,
        gdf_lines_transfer=None,
        leeway=None
    ):
    """
    # Take map extent from the combined LSOA, region,
    # and stroke unit geometry.
    """
    gdfs_to_merge = []

    # Regions.
    # Pick out regions that have been selected or contain periphery
    # units or LSOA.
    col_names = ['contains_unit']
    # 'contains_periphery_lsoa', 'contains_periphery_unit'
    gdf_regions_reduced = filter_gdf_by_columns(
        gdf_boundaries_regions, col_names)
    # Keep only the 'geometry' column and name it 'geometry' (no MultiIndex):
    gdf_regions_reduced = gdf_regions_reduced.reset_index()['geometry']
    gdf_regions_reduced.columns = ['geometry']
    # Set the geometry column again:
    gdf_regions_reduced = gdf_regions_reduced.set_geometry('geometry')
    # Store in list:
    gdfs_to_merge.append(gdf_regions_reduced)

    # Units.
    # Pick out units that have been selected or catch periphery LSOA.
    col_names = ['selected', 'periphery_unit']
    gdf_units_reduced = filter_gdf_by_columns(
        gdf_points_units, col_names)
    # Keep only the 'geometry' column and name it 'geometry' (no MultiIndex):
    gdf_units_reduced = gdf_units_reduced.reset_index()['geometry']
    gdf_units_reduced.columns = ['geometry']
    # Set the geometry column again:
    gdf_units_reduced = gdf_units_reduced.set_geometry('geometry')
    # Store in list:
    gdfs_to_merge.append(gdf_units_reduced)

    # LSOA catchment.
    # Pick out catchment areas of units that have been selected
    col_names = ['selected']
    gdf_catchment_reduced = filter_gdf_by_columns(
        gdf_boundaries_catchment, col_names)
    # Keep only the 'geometry' column and name it 'geometry' (no MultiIndex):
    gdf_catchment_reduced = gdf_catchment_reduced.reset_index()['geometry']
    gdf_catchment_reduced.columns = ['geometry']
    # Set the geometry column again:
    gdf_catchment_reduced = gdf_catchment_reduced.set_geometry('geometry')
    # Store in list:
    gdfs_to_merge.append(gdf_catchment_reduced)

    if gdf_lines_transfer is None:
        pass
    else:
        # Transfer lines.
        # Pick out catchment areas of units that have been selected
        col_names = ['selected']
        gdf_lines_reduced = filter_gdf_by_columns(
            gdf_lines_transfer, col_names)
        # Keep only the 'geometry' column and name it 'geometry' (no MultiIndex):
        gdf_lines_reduced = gdf_lines_reduced.reset_index()['geometry']
        gdf_lines_reduced.columns = ['geometry']
        # Set the geometry column again:
        gdf_lines_reduced = gdf_lines_reduced.set_geometry('geometry')
        # Store in list:
        gdfs_to_merge.append(gdf_lines_reduced)

    gdf_combo = pd.concat(gdfs_to_merge, axis='rows', ignore_index=True)

    # Set geometry column:
    # gdf_combo = gdf_combo.set_geometry('geometry')
    gdf_combo = geopandas.GeoDataFrame(
        gdf_combo,
        geometry='geometry',
        crs=gdfs_to_merge[0].crs
        )

    box, map_extent = get_selected_area_extent(gdf_combo, leeway)
    return box, map_extent


def get_selected_area_extent(
        gdf_selected,
        leeway=20000,
        ):
    """
    What is the spatial extent of everything in this GeoDataFrame?
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


def _keep_only_geometry_in_box(gdf, box):
    mask = gdf.geometry.intersects(box)
    gdf = gdf[mask]
    return gdf


def _restrict_geometry_edges_to_box(gdf, box):
    gdf.geometry = gdf.geometry.intersection(box)
    return gdf


def _assign_label_coords_to_regions(
        gdf, col_point_label):
    # Get coordinates for where to plot each label:
    point_label = ([poly.representative_point() for
                    poly in gdf.geometry])
    gdf[col_point_label] = point_label
    return gdf


# ###########################
# ##### SETUP FOR PLOTS #####
# ###########################
def _setup_plot_map_outcome(
        gdf_boundaries_lsoa,
        scenario: str,
        outcome: str,
        boundary_kwargs={},
        ):
    """

    """
    # Find shared outcome limits.
    # Take only scenarios containing 'diff':
    mask = gdf_boundaries_lsoa.columns.get_level_values(
        'scenario').str.contains('diff')
    if scenario.startswith('diff'):
        pass
    else:
        # Take the opposite condition, take only scenarios
        # not containing 'diff'.
        mask = ~mask

    mask = (
        mask &
        (gdf_boundaries_lsoa.columns.get_level_values('subtype') == 'mean') &
        (gdf_boundaries_lsoa.columns.get_level_values('property') == outcome)
    )
    all_mean_vals = gdf_boundaries_lsoa.iloc[:, mask]
    vlim_abs = all_mean_vals.abs().max().values[0]
    vmax = all_mean_vals.max().values[0]
    vmin = all_mean_vals.min().values[0]

    lsoa_boundary_kwargs = {
        'column': outcome,
        'edgecolor': 'face',
        # Adjust size of colourmap key, and add label
        'legend_kwds': {
            'shrink': 0.5,
            'label': outcome
            },
        # Set to display legend
        'legend': True,
        }

    cbar_diff = True if scenario.startswith('diff') else False
    if cbar_diff:
        lsoa_boundary_kwargs['cmap'] = 'seismic'
        lsoa_boundary_kwargs['vmin'] = -vlim_abs
        lsoa_boundary_kwargs['vmax'] = vlim_abs
    else:
        cmap = 'plasma'
        if outcome == 'mRS shift':
            # Reverse the colourmap because lower values
            # are better for this outcome.
            cmap += '_r'
        lsoa_boundary_kwargs['cmap'] = cmap
        lsoa_boundary_kwargs['vmin'] = vmin
        lsoa_boundary_kwargs['vmax'] = vmax
    # Update this with anything from the input dict:
    lsoa_boundary_kwargs = lsoa_boundary_kwargs | boundary_kwargs

    return lsoa_boundary_kwargs


# #######################
# ##### PYPLOT MAPS #####
# #######################
def plot_map_selected_regions(
        gdf_boundaries_regions,
        gdf_points_units,
        map_extent=[],
        path_to_file='',
        show=False
        ):
    fig, ax = plt.subplots(figsize=(8, 5))

    ax, extra_artists = maps.plot_map_selected_regions(
        gdf_boundaries_regions,
        gdf_points_units,
        ax=ax,
        map_extent=map_extent
    )

    if path_to_file is None:
        pass
    else:
        # Return extra artists so that bbox_inches='tight' line
        # in savefig() doesn't cut off the legends.
        # Adding legends with ax.add_artist() means that the
        # bbox_inches='tight' line ignores them.
        plt.savefig(
            path_to_file,
            bbox_extra_artists=extra_artists,
            dpi=300, bbox_inches='tight'
            )
    if show:
        # Add dummy axis to the sides so that
        # extra_artists are not cut off when plt.show() crops.
        fig = maps.plot_dummy_axis(fig, ax, extra_artists[1], side='left')
        fig = maps.plot_dummy_axis(fig, ax, extra_artists[0], side='right')
        plt.show()
    else:
        plt.close()


def plot_map_selected_units(
        gdf_boundaries_regions,
        gdf_points_units,
        gdf_lines_transfer,
        map_extent=[],
        path_to_file='',
        show=False
        ):
    fig, ax = plt.subplots(figsize=(6, 5))

    ax, extra_artists = maps.plot_map_selected_units(
        gdf_boundaries_regions,
        gdf_points_units,
        gdf_lines_transfer,
        ax=ax,
        map_extent=map_extent,
    )

    if path_to_file is None:
        pass
    else:
        plt.savefig(
            path_to_file,
            bbox_extra_artists=extra_artists,
            dpi=300, bbox_inches='tight'
            )
    if show:
        # Add dummy axis to the sides so that
        # extra_artists are not cut off when plt.show() crops.
        fig = maps.plot_dummy_axis(fig, ax, extra_artists[0], side='left')
        plt.show()
    else:
        plt.close()


def plot_map_catchment(
        gdf_boundaries_lsoa,
        gdf_boundaries_regions,
        gdf_points_units,
        gdf_lines_transfer,
        title='',
        lsoa_boundary_kwargs={},
        map_extent=[],
        show=False,
        path_to_file=''
        ):
    boundary_kwargs = {
        'cmap': 'Blues',
        'edgecolor': 'face'
    }
    # Update this with anything from the input dict:
    lsoa_boundary_kwargs = boundary_kwargs | lsoa_boundary_kwargs

    fig, ax = plt.subplots(figsize=(6, 5))
    ax.set_title(title)

    ax, extra_artists = maps.plot_map_catchment(
        gdf_boundaries_lsoa,
        gdf_boundaries_regions,
        gdf_points_units,
        gdf_lines_transfer,
        ax=ax,
        map_extent=map_extent,
        boundary_kwargs=lsoa_boundary_kwargs,
    )

    if path_to_file is None:
        pass
    else:
        plt.savefig(
            path_to_file,
            bbox_extra_artists=extra_artists,
            dpi=300, bbox_inches='tight')
    if show:
        # Add dummy axis to the sides so that
        # extra_artists are not cut off when plt.show() crops.
        fig = maps.plot_dummy_axis(fig, ax, extra_artists[0], side='left')
        plt.show()
    else:
        plt.close()


def plot_map_outcome(
        gdf_boundaries_lsoa,
        gdf_boundaries_regions,
        gdf_points_units,
        scenario,
        outcome,
        title='',
        lsoa_boundary_kwargs={},
        draw_region_boundaries=True,
        show=False,
        path_to_file=None
        ):
    lsoa_boundary_kwargs = _setup_plot_map_outcome(
        gdf_boundaries_lsoa,
        scenario,
        outcome,
        boundary_kwargs=lsoa_boundary_kwargs,
        )

    fig, ax = plt.subplots(figsize=(7, 5))
    ax.set_title(title)

    ax, extra_artists = maps.plot_map_outcome(
        gdf_boundaries_lsoa,
        gdf_boundaries_regions,
        gdf_points_units,
        ax=ax,
        boundary_kwargs=lsoa_boundary_kwargs,
        draw_region_boundaries=draw_region_boundaries,
    )

    if path_to_file is None:
        pass
    else:
        plt.savefig(
            path_to_file,
            bbox_extra_artists=extra_artists,
            dpi=300, bbox_inches='tight'
            )
    if show:
        # Add dummy axis to the sides so that
        # extra_artists are not cut off when plt.show() crops.
        fig = maps.plot_dummy_axis(fig, ax, extra_artists[0], side='left')
        plt.show()
    else:
        plt.close()
