import numpy as np
import xarray as xr
import cf_xarray
import geocat.comp as gcomp

in_ta = xr.open_dataset("./test/atmos_ta.nc")         # 6-hourly 3-d T
in_ps = xr.open_dataset("./test/atmos_ps.nc")         # 6-hourly surface pressure
in_zsfc = xr.open_dataset("./test/atmos_zsfc.nc")     # static surface geopotential

#Prepare Variables for Interpolation ----------------------------------------------------------------------------------
hyam = in_ta.cf['hyam']
hybm = in_ta.cf['hybm']
hyai = in_ta.cf['hyai']
hybi = in_ta.cf['hybi']

surf_pressure = in_ps.cf['PS']

default_levs = np.array([1000.0, 975.0, 950.0, 925.0, 900.0, 850.0, 800.0, 750.0, 700.0, 650.0, 600.0, 550.0, 500.0, \
             450.0, 400.0, 350.0, 300.0, 250.0, 200.0, 150.0, 100.0, 70.0, 50.0, 30.0, 20.0, 10.0 ])

temp = in_ta["T"]

temp_interp = gcomp.interpolation.interp_hybrid_to_pressure(temp.isel(time=0),surf_pressure.isel(time=0),hyam,hybm,
                                                            new_levels=default_levs,
                                                            lev_dim = 'lev',
                                                            method='log',
                                                            extrapolate=True,
                                                            variable='temperature',
                                                            t_bot=temp.isel(lev=-1,time=0),
                                                            phi_sfc=in_zsfc['PHIS'])