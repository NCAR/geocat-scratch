import uxarray as ux
import xarray as xr
import numpy as np
import geocat.comp as gc

def zonal_mpsi(uxds):
    """
    Calculate the zonally averaged meridional mass streamfunction (mpsi) from a UXarray Dataset.

    Parameters
    ----------
    uxds : uxarray.UxDataset
        Input dataset containing the following required fields:
            - V : Meridional wind component (on hybrid sigma-pressure levels)
            - PS : Surface pressure
            - hyam : Hybrid A coefficients
            - hybm : Hybrid B coefficients
            - uxgrid : Grid information for uxarray

    Returns
    -------
    ux_mpsi : uxarray.UxDataArray
        Zonal mean meridional mass streamfunction, scaled by Earth's geometry and gravity.
        Dimensions: ["time", "latitudes", "plev"]

    Notes
    -----
    - Converts wind data from hybrid sigma-pressure levels to pressure levels.
    - Computes zonal means and pressure integration deltas.
    - Integrates over pressure levels, handling orientation.
    - Applies scaling factor based on Earth's radius and gravity.
    - Currently only supports UXarray Datasets with specified structure.
    """

    # constants
    a = 6.371e6  # Earth radius (m)
    g = 9.80665  # gravity (m/s^2)

    # convert from sigma hybrid to pressure levels
    da_ipress = gc.interpolation.interp_hybrid_to_pressure(
        uxds.V, 
        uxds.PS, 
        uxds.hyam, 
        uxds.hybm)
    ux_ipress = ux.UxDataArray(da_ipress, uxgrid=uxds.uxgrid) # convert back to uxarray

    # zonal means
    ux_v_zonal = ux_ipress.zonal_mean()
    ux_v_zonal['plev'] = ux_ipress.plev # re-add plev coordinate

    ux_PS_zonal = uxds.PS.zonal_mean()

    # integration deltas
    np_dp_zonal = gc.meteorology.delta_pressure(ux_v_zonal.plev, ux_PS_zonal)
    da_dp_zonal = xr.DataArray(
        np_dp_zonal,
        dims=["time", "latitudes", "plev"],
        coords={
            "plev": ux_v_zonal.plev,
            "latitudes": ux_v_zonal.latitudes
            },
        name="delta_pressure"
    ) # convert from numpy array to xarray
    ux_dp_zonal = ux.UxDataArray(da_dp_zonal, uxgrid=uxds.uxgrid) # convert back to uxarray

    # scaling factor
    da_scaling_factor = 2 * np.pi * a * np.cos(ux_v_zonal.latitudes) / g

    # check orientation and integrate
    if ux_v_zonal.plev.values[0] < ux_v_zonal.plev.values[-1]:
        integrand = ux_v_zonal * ux_dp_zonal
        ux_mpsi = integrand.cumsum(dim="plev")
    else:
        integrand = (ux_v_zonal * ux_dp_zonal).isel(plev=slice(None, None, -1)) # reverse for integration
        ux_mpsi = integrand.cumsum(dim="plev").isel(plev=slice(None, None, -1)) # reverse back

    return ux_mpsi * da_scaling_factor
    