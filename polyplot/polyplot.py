import numpy as np
import xarray as xr
import pandas as pd
import dask.array as da
from dask import delayed, compute
from dask.dataframe import from_pandas
import scipy.spatial
import spatialpandas as sp
import cartopy.crs as ccrs
import cmocean

import pygeos as pg
import pgpd
import pyarrow as pa

#import multiprocessing

#from pathos.multiprocessing import ProcessingPool as Pool

import holoviews as hv
from holoviews import opts
from holoviews.operation.datashader import rasterize
import datashader as ds
import geoviews.feature as gf

#from numba import njit, prange

#import time





class poly_plot():
    def __init__(self, ds=None):
        """ Constructs a Poly Plot Object based on UGRID data 

        Args:
        ----------
        df : xr.dataset
            Grid data following the UGRID conventions
        x : ndarray
            1D array containing x coordinates of face edge nodes
            [1 x n_mesh_nodes]
        y : ndarray
            1D array containing y coordinates of face edge nodes
            [1 x n_mesh_nodes]
        face_nodes : ndarray
            2D array containing each polygon's face edge node indexes
            [n_faces x n_face_nodes]

        """

        # Dictonary for Variables
        var_dict = ds.ds_var_names
        ugrid_dict = dict((k, v) for k,v in var_dict.items())

            
        self.ds = ds.ds
        self.x = self.ds[ugrid_dict['Mesh2_node_x']].values
        self.y = self.ds[ugrid_dict['Mesh2_node_y']].values
        self.face_nodes = self.ds[ugrid_dict['Mesh2_face_nodes']].values
        self.n_faces, self.n_face_nodes = self.face_nodes.shape
        self.n_mesh_nodes = self.x.shape[0]
        self.index = self.face_nodes.astype(int)

        # Polygon Mesh Data (polygons and faces)
        self.df = None
        self.df_fixed = None
        self.face_array = None
        #self.poly_array = np.zeros((self.n_faces, 2*self.n_face_nodes))
        self.polygon_array = np.zeros((self.n_faces, self.n_face_nodes, 2))

        # Saved Index for Fixing Cells
        self.drop_index = None

        

    def data_mesh(self, name, dims, method="Mean"):
        """ Calculates the face value of each reconstructred polygon

        Args:
        ----------
        name : string
            Name of data variable for plotting
        method : string
            Method for calculating Fill Value

        Outputs:
        ----------
        face_array : ndarray
            Face Values for each Polygon

        """

        if name not in list(self.ds.data_vars):
            # add exception later
            print("Invalid Data Variable")
            return

        
        if method == "Mean":
            self.face_array = self.ds[name].isel(dims).values[self.index].mean(axis=1)
        else:
            self.face_array = None

        self.df['faces'] = self.face_array
        self.fix_cells()
    
        return self.df_fixed

    def construct_mesh(self):
        """ Constructs a Polygon Mesh suitable for rendering with Datashader

        Inputs:
        ----------
        x : ndarray
            1D array containing x coordinates of face edge nodes
            [1 x n_mesh_nodes]
        y : ndarray
            1D array containing y coordinates of face edge nodes
            [1 x n_mesh_nodes]
        face_nodes : ndarray
            2D array containing each polygon's face edge node indexes
            [n_faces x n_face_nodes]

        Outputs:
        ----------
        poly_array : ndarray
            Array containing each polygon's face edge node coordinates 
            [n_faces x 2 * n_face_nodes]
            [x1, y1, x2, y2, x3, y3, ...... xn, yn]
        df : GeoDataFrame
            Dataframe containing original polygons reconstructed from input data 
            "geometry" : Polygon Coordinates
            "faces" : Polygon Fill Values       
        """
        
    
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ Original Approach ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # Vectorized Approach 2 (~150ms)
        # x_coords = self.x[self.index]
        # y_coords = self.y[self.index]
        # self.poly_array[:, 0::2] = x_coords
        # self.poly_array[:, 1::2] = y_coords

        # # Create Polygon and Face Dataframe
        # self.poly_array = self.poly_array.reshape((self.n_faces, 1, 2*self.n_face_nodes))

        # # Main Performance Bottleneck
        # polygons = sp.geometry.PolygonArray(self.poly_array.tolist())
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ PyGeos Approach ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        x_coords = self.x[self.index]
        y_coords = self.y[self.index]
        self.polygon_array[:, :, 0] = x_coords
        self.polygon_array[:, :, 1] = y_coords

        geo = pg.polygons(self.polygon_array)

        arr_flat, part_indices = pg.get_parts(geo, return_index=True)
        offsets1 = np.insert(np.bincount(part_indices).cumsum(), 0, 0)
        arr_flat2, ring_indices = pg.geometry.get_rings(arr_flat, return_index=True)
        offsets2 = np.insert(np.bincount(ring_indices).cumsum(), 0, 0)
        coords, indices = pg.get_coordinates(arr_flat2, return_index=True)
        offsets3 = np.insert(np.bincount(indices).cumsum(), 0, 0)

        coords_flat = coords.ravel()
        offsets3 *= 2

        # create a pyarrow array from this
        _parr3 = pa.ListArray.from_arrays(pa.array(offsets3), pa.array(coords_flat))
        _parr2 = pa.ListArray.from_arrays(pa.array(offsets2), _parr3)
        parr = pa.ListArray.from_arrays(pa.array(offsets1), _parr2)

        polygons = sp.geometry.MultiPolygonArray(parr)
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

        # Used for Original and PyGeos Approaches above
        self.df = sp.GeoDataFrame({'geometry': polygons})
        
        
        
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ PyGeos + PGPD ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # x_coords = self.x[self.index]
        # y_coords = self.y[self.index]
        # self.polygon_array[:, :, 0] = x_coords
        # self.polygon_array[:, :, 1] = y_coords

        # polygons = pg.polygons(self.polygon_array)

        # df = pd.DataFrame({"geometry": polygons, "faces" : np.zeros(self.n_faces)})
        # df = df.astype({'geometry':'geos'})

        # self.df = df.geos.to_geopandas(geometry='geometry')
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        

    def fix_cells(self):
        '''Fixes cells near the edges of the map (around +-180 lon)
        
        Inputs:
        ----------
        df : GeoDataFrame
            Dataframe containing original polygons reconstructed from input data 

        Outputs:
        ----------
        df_fixed: GeoDataFrame
            Dataframe containing fixed polygons based on edge value wrap around conditions
        '''
        #n_poly = self.df['geometry'].values.shape[0]
        #print(self.df['geometry'].values.buffer_values.shape)
        #poly_data = self.df['geometry'].values.buffer_values.reshape(self.n_faces, 2*self.n_face_nodes)
        poly_data = np.zeros((self.n_faces, 2*self.n_face_nodes))
        poly_data[:, 0::2] = self.polygon_array[:, :, 0]
        poly_data[:, 1::2] = self.polygon_array[:, :, 1]
        
        face_data = self.df['faces'].values

        # Positive and Negative Value to ignore sign changes in x values
        center_buffer = 5

        # Get x values
        x = poly_data[:, ::2]
        x_abs = np.abs(poly_data[:, ::2])

        # Find violater cells (Sign Change in x values)
        out_left = np.all((-x - x_abs) == 0, axis=1)
        out_right = np.all((x - x_abs) == 0, axis=1)
        out = out_left | out_right


        # Index of violater cells
        drop_index = np.arange(0, self.n_faces, 1)
        drop_index = drop_index[~out]

        # Get cells to fix
        poly_to_fix = poly_data[drop_index]
        face_to_fix = face_data[drop_index]

        # Exclude any center cells (+-center_buffer) x
        corrected_index = np.any(np.abs(poly_to_fix[:, ::2]) < center_buffer, axis=1)
        poly_to_fix = poly_to_fix[~corrected_index]
        face_to_fix = face_to_fix[~corrected_index]
        drop_index = drop_index[~corrected_index]

        poly_list = []
        face_list = []

        # Split each violater cell into two cells
        for face, poly in zip(face_to_fix, poly_to_fix):
            poly_left = poly.copy()
            poly_right = poly.copy()
             
            # Start in RHS
            if poly[0] > 0:
                x_remain_index = poly[2::2] > 0
                poly_right[2::2][~x_remain_index] = poly[2::2][~x_remain_index] + 360 
                
                poly_left[0] = poly[0] - 360
                poly_left[2::2][x_remain_index] = poly[2::2][x_remain_index] - 360

                poly_list.extend([poly_left, poly_right])
                face_list.extend([face, face])
                continue
            # Start in LHS
            elif poly[0] < 0:
                x_remain_index = poly[2::2] < 0
                poly_left[2::2][~x_remain_index] = poly[2::2][~x_remain_index] - 360

                poly_right[0] = poly[0] + 360
                poly_right[2::2][x_remain_index] = poly[2::2][x_remain_index] + 360
                
                poly_list.extend([poly_left, poly_right])
                face_list.extend([face, face])
                continue
            # Ignore
            else:
                continue

        # Drop Violater Cells
        df_droped = self.df.drop(drop_index)

        # Create polygon and face arrays to add to df
        poly_insert = np.array(poly_list)
        poly_insert = poly_insert.reshape(len(poly_list), self.n_face_nodes, 2)

        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        geo = pg.polygons(poly_insert)

        arr_flat, part_indices = pg.get_parts(geo, return_index=True)
        offsets1 = np.insert(np.bincount(part_indices).cumsum(), 0, 0)
        arr_flat2, ring_indices = pg.geometry.get_rings(arr_flat, return_index=True)
        offsets2 = np.insert(np.bincount(ring_indices).cumsum(), 0, 0)
        coords, indices = pg.get_coordinates(arr_flat2, return_index=True)
        offsets3 = np.insert(np.bincount(indices).cumsum(), 0, 0)

        coords_flat = coords.ravel()
        offsets3 *= 2

        # create a pyarrow array from this
        _parr3 = pa.ListArray.from_arrays(pa.array(offsets3), pa.array(coords_flat))
        _parr2 = pa.ListArray.from_arrays(pa.   array(offsets2), _parr3)
        parr = pa.ListArray.from_arrays(pa.array(offsets1), _parr2)

        polygons = sp.geometry.MultiPolygonArray(parr)
        
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # Create new df with left and right cells
        df_insert = sp.GeoDataFrame({'geometry': polygons,
                                    'faces': face_list})


        # polygons = pg.polygons(poly_insert)
        # df_insert = pd.DataFrame({"geometry": polygons, "faces" : face_list})
        # df_insert = df_insert.astype({'geometry':'geos'})
        # df_insert = df_insert.geos.to_geopandas(geometry='geometry')
       

        # Join existing and new df
        self.df_fixed = pd.concat([df_insert, df_droped], ignore_index=True)
        
        return self.df_fixed

    def mesh(self):
        '''Return Polygon Mesh For Plotting with Datashader'''
        return self.df_fixed
    
    def plot_data(self):
        '''not implemented, currently done in notebook'''
        return 




























class poly_plot_dask():
    def __init__(self, ds=None, ugrid_dict = None, x=None, y=None, face_nodes=None):
        """ Constructs a Poly Plot Object based on UGRID data 

        Args:
        ----------
        df : xr.dataset
            Grid data following the UGRID conventions
        x : ndarray
            1D array containing x coordinates of face edge nodes
            [1 x n_mesh_nodes]
        y : ndarray
            1D array containing y coordinates of face edge nodes
            [1 x n_mesh_nodes]
        face_nodes : ndarray
            2D array containing each polygon's face edge node indexes
            [n_faces x n_face_nodes]

        """

        # UGRID Data (coordinates and faces)
        if ds is not None and ugrid_dict is not None:
            self.x = ds[ugrid_dict['Mesh2_node_x']].values
            self.y = ds[ugrid_dict['Mesh2_node_y']].values
            self.face_nodes = ds[ugrid_dict['Mesh2_face_nodes']].values
            self.n_faces, self.n_face_nodes = self.face_nodes.shape
            self.n_mesh_nodes = self.x.shape[0]
            self.index = self.face_nodes.astype(int)
        else:
            self.x, self.y = x, y
            self.face_nodes = face_nodes
            self.n_faces, self.n_face_nodes = face_nodes.shape
            self.n_mesh_nodes = x.shape[0]
            self.index = face_nodes.astype(int)
        
        # Convert To Dask
        self.x = da.from_array(self.x, chunks=('auto'))
        self.y = da.from_array(self.y, chunks=('auto'))
        self.face_nodes = da.from_array(self.face_nodes, chunks=('auto', -1))
        self.index = da.from_array(self.index, chunks=('auto', -1))
  
        # Polygon Mesh Data (polygons and faces)
        self.df = None
        self.df_fixed = None
        self.face_array = None
        self.poly_array = np.zeros((self.n_faces, 2*self.n_face_nodes))

        

    def set_data(self, data, method="Mean"):
        """ Calculates the face value of each reconstructred polygon

        Args:
        ----------
        data : ndarray
            Data Values used for calculated face fill value
        method : string
            Method for calculating Fill Value

        Outputs:
        ----------
        face_array : ndarray
            Face Values for each Polygon

        """

        if method == "Mean":    
            self.face_array = da.mean(data[self.index], axis=1)
        
        else:
            self.face_array = None

    def to_poly_mesh(self):
        """ Constructs a Polygon Mesh suitable for rendering with Datashader

        Inputs:
        ----------
        x : ndarray
            1D array containing x coordinates of face edge nodes
            [1 x n_mesh_nodes]
        y : ndarray
            1D array containing y coordinates of face edge nodes
            [1 x n_mesh_nodes]
        face_nodes : ndarray
            2D array containing each polygon's face edge node indexes
            [n_faces x n_face_nodes]

        Outputs:
        ----------
        poly_array : ndarray
            Array containing each polygon's face edge node coordinates 
            [n_faces x 2 * n_face_nodes]
            [x1, y1, x2, y2, x3, y3, ...... xn, yn]
        df : GeoDataFrame
            Dataframe containing original polygons reconstructed from input data 
            "geometry" : Polygon Coordinates
            "faces" : Polygon Fill Values       
        """
        # Point Index
        p_index = np.arange(0, 2*self.n_face_nodes)

        # Vectorized Approach
        for n, i, j in zip(range(self.n_face_nodes), p_index[::2], p_index[1::2]):
            self.poly_array[:, i] = self.x[self.index[:, n]]
            self.poly_array[:, j] = self.y[self.index[:, n]]
        
        # Create Polygon and Face Dataframe
        self.poly_array = self.poly_array.reshape((self.n_faces, 1, 2*self.n_face_nodes))

        #polygons = sp.geometry.PolygonArray(self.poly_array.tolist())
        polygons = self.poly_array

        if self.face_array is None:
            self.df = sp.GeoDataFrame({'geometry': polygons})
        else:
            self.df = sp.GeoDataFrame({'geometry': polygons,
                                       'faces': self.face_array.tolist()})

        self.df = from_pandas(self.df, npartitions=4)

        # Correct Edge Cells 
        self.fix_cells()

    def fix_cells(self):
        '''Fixes cells near the edges of the map (around +-180 lon)
        
        Inputs:
        ----------
        df : GeoDataFrame
            Dataframe containing original polygons reconstructed from input data 

        Outputs:
        ----------
        df_fixed: GeoDataFrame
            Dataframe containing fixed polygons based on edge value wrap around conditions
        '''
        n_poly = self.df['geometry'].values.shape[0]
        poly_data = self.df['geometry'].values.buffer_values.reshape(n_poly, 2*self.n_face_nodes)
        face_data = self.df['faces'].values

        # Positive and Negative Value to ignore sign changes in x values
        center_buffer = 5

        # Get x values
        x = poly_data[:, ::2]
        x_abs = np.abs(poly_data[:, ::2])

        # Find violater cells (Sign Change in x values)
        out_left = np.all((-x - x_abs) == 0, axis=1)
        out_right = np.all((x - x_abs) == 0, axis=1)
        out = out_left | out_right

        # Index of violater cells
        drop_index = np.arange(0, n_poly, 1)
        drop_index = drop_index[~out]

        # Get cells to fix
        poly_to_fix = poly_data[drop_index]
        face_to_fix = face_data[drop_index]

        # Exclude any center cells (+-center_buffer) x
        corrected_index = np.any(np.abs(poly_to_fix[:, ::2]) < center_buffer, axis=1)
        poly_to_fix = poly_to_fix[~corrected_index]
        face_to_fix = face_to_fix[~corrected_index]
        drop_index = drop_index[~corrected_index]

        poly_list = []
        face_list = []

        # Split each violater cell into two cells
        for face, poly in zip(face_to_fix, poly_to_fix):
            poly_left = poly.copy()
            poly_right = poly.copy()
             
            # Start in RHS
            if poly[0] > 0:
                x_remain_index = poly[2::2] > 0
                poly_right[2::2][~x_remain_index] = poly[2::2][~x_remain_index] + 360 
                
                poly_left[0] = poly[0] - 360
                poly_left[2::2][x_remain_index] = poly[2::2][x_remain_index] - 360

                poly_list.extend([poly_left, poly_right])
                face_list.extend([face, face])
                continue
            # Start in LHS
            elif poly[0] < 0:
                x_remain_index = poly[2::2] < 0
                poly_left[2::2][~x_remain_index] = poly[2::2][~x_remain_index] - 360

                poly_right[0] = poly[0] + 360
                poly_right[2::2][x_remain_index] = poly[2::2][x_remain_index] + 360
                
                poly_list.extend([poly_left, poly_right])
                face_list.extend([face, face])
                continue
            # Ignore
            else:
                continue

        # Drop Violater Cells
        df_droped = self.df.drop(drop_index)

        # Create polygon and face arrays to add to df
        poly_insert = np.array(poly_list)
        poly_insert = poly_insert.reshape(len(poly_list), 1, 2*self.n_face_nodes)

        # Create new df with left and right cells
        polygons = sp.geometry.PolygonArray(poly_insert.tolist())
        df_insert = sp.GeoDataFrame({'geometry': polygons,
                                    'faces': face_list})
    
        # Join existing and new df
        self.df_fixed = pd.concat([df_insert, df_droped], ignore_index=True)
        self.df_fixed = from_pandas(self.df_fixed, npartitions=4)
        
        return self.df_fixed

    def mesh(self):
        '''Return Polygon Mesh For Plotting with Datashader'''
        return self.df_fixed
    
    def plot_data(self):
        '''not implemented, currently done in notebook'''
        return 


