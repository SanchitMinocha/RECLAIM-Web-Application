from django.shortcuts import render
from django.http import HttpResponse
from pathlib import Path
from django.core.files.storage import FileSystemStorage
import numpy as np
import pandas as pd
import geopandas as gpd
import importlib
import traceback
import shutil
import plotly.express as px
import plotly.io as pio
from django.shortcuts import render
from uuid import uuid4
import re
import io
import json
from django.http import FileResponse, Http404
import datetime

# RECLAIM imports
import reclaim.generate_features as gf
from reclaim.reclaim import Reclaim


# File deletion upload
from mapapp.models import FileCleanupSettings


def should_delete_uploaded_files():
    """
    Returns True if admin toggle is enabled.
    Defaults to False if settings row does not exist.
    """
    settings = FileCleanupSettings.objects.first()
    return settings.delete_uploaded_files if settings else False



BASE_DIR = Path(__file__).resolve().parent.parent  # already in settings

base_dir = BASE_DIR / "mapapp" / "global_datasets"

importlib.reload(gf)

BASINS_FILE = "/var/www/html/reclaim/mapapp/basins_rat_sedi_v1 (1).geojson"

_BASIN_LIST_CACHE = None

def get_basin_list():
    global _BASIN_LIST_CACHE
    if _BASIN_LIST_CACHE is None:
        try:
            print("Loading 37MB Basin GeoJSON into memory... (This will take 15 seconds, but will only happen once)")
            basins_gdf = gpd.read_file(BASINS_FILE)
            _BASIN_LIST_CACHE = (
                basins_gdf[["HYBAS_ID", "RIVER_BASIN"]]
                .dropna(subset=["HYBAS_ID"])
                .sort_values("HYBAS_ID")
                .to_dict(orient="records")
            )
            print("Successfully cached Basin GeoJSON.")
        except Exception as e:
            print("Error loading basins:", e)
            _BASIN_LIST_CACHE = []
    return _BASIN_LIST_CACHE



def index(request):
    """Render homepage."""
    return render(request, "mapapp/index.html")


def estimator_view(request):
    """Render the estimator page and handle model execution."""
    if request.method == "POST":
        return run_reclaim(request)

    basin_list = get_basin_list()
    sample_datasets = get_sample_datasets()

    return render(
        request,
        "mapapp/map.html",
        {
            "basin_list": basin_list,
            "sample_datasets": sample_datasets,
            "form_data": {},
            "current_year": datetime.datetime.now().year,
        },
    )


def get_sample_datasets():
    """Helper to fetch sample datasets from disk."""
    sample_datasets = []
    samples_dir = BASE_DIR / "mapapp" / "sample_data"
    if samples_dir.exists():
        for item in samples_dir.iterdir():
            if item.is_dir():
                meta_path = item / "metadata.json"
                if meta_path.exists():
                    try:
                        with open(meta_path, "r") as f:
                            meta = json.load(f)
                            meta["folder_name"] = item.name
                            meta["json_str"] = json.dumps(meta)
                            sample_datasets.append(meta)
                    except Exception as meta_e:
                        print(f"Error parsing metadata.json for {item.name}: {meta_e}")

    return sorted(sample_datasets, key=lambda x: x.get("name", ""))


def run_reclaim(request):
    """Handle RECLAIM form submission, run model, return sedimentation rate."""
    if request.method != "POST":
        return HttpResponse("POST requests only.", status=405)

    form = request.POST
    files = request.FILES

    def create_empty_csv(path: Path, columns: list):
        df = pd.DataFrame({col: [] for col in columns})
        df.to_csv(path, index=False)
        return path

    try:
        # Create upload folder
        # Get reservoir name
        res_name = form.get("res_name", "")

        # Clean it
        def clean_name(name):
            name = name.strip().lower()
            name = re.sub(r'\s+', '_', name)
            name = re.sub(r'[^a-z0-9_]', '', name)
            return name

        safe_name = clean_name(res_name)

        # Create unique folder
        job_id = str(uuid4())[:8]
        folder_name = f"{safe_name}_{job_id}"

        upload_root = Path("/var/www/html/reclaim_dev/uploaded_files") / folder_name
        upload_root.mkdir(parents=True, exist_ok=True)

        fs = FileSystemStorage(location=str(upload_root))

        def save_uploaded_file(key):
            f = files.get(key)
            if not f:
                return None
            return upload_root / fs.save(f.name, f)

        # Reservoir CSVs
        aec_path = save_uploaded_file("aec_file")
        if not aec_path:
            aec_path = upload_root / "aec_empty.csv"
            create_empty_csv(
                aec_path,
                ["area", "elevation", "storage", "storage (mil. m3)", "elevation_srtm"],
            )

        inflow_path = save_uploaded_file("inflow_file")
        if not inflow_path:
            inflow_path = upload_root / "inflow_empty.csv"
            create_empty_csv(inflow_path, ["date", "inflow (m3/d)"])

        outflow_path = save_uploaded_file("outflow_file")
        if not outflow_path:
            outflow_path = upload_root / "outflow_empty.csv"
            create_empty_csv(outflow_path, ["date", "outflow (m3/d)"])

        evaporation_path = save_uploaded_file("evaporation_file")
        if not evaporation_path:
            evaporation_path = upload_root / "evaporation_empty.csv"
            create_empty_csv(evaporation_path, ["date", "evaporation (mm)"])

        surface_area_path = save_uploaded_file("surface_area_file")
        if not surface_area_path:
            surface_area_path = upload_root / "surface_area_empty.csv"
            create_empty_csv(surface_area_path, ["date", "area (km2)"])

        # NSSC CSVs

        nssc_path = save_uploaded_file("nssc_file")

        DATE_COL = "date"
        NSSC1_COL = "NSSC (nir/red per pixel)"
        NSSC2_COL = "NSSC (red/green per pixel)"

        # Create empty NSSC if missing
        if not nssc_path:
            nssc_path = upload_root / "nssc_empty.csv"
            create_empty_csv(nssc_path, [DATE_COL, NSSC1_COL, NSSC2_COL])

        # Read safely
        df_nssc = pd.read_csv(nssc_path)

        # If user uploaded a file, enforce schema
        if nssc_path.name != "nssc_empty.csv":
            if not {DATE_COL, NSSC1_COL, NSSC2_COL}.issubset(df_nssc.columns):
                return HttpResponse("NSSC file missing required columns.", status=400)

        # Climate CSVs
        meteo_path = save_uploaded_file("meteo_file")

        METEO_COLS = ["time", "precip", "tmin", "tmax", "wind"]

        # Create empty meteo if missing
        if not meteo_path:
            meteo_path = upload_root / "meteo_empty.csv"
            create_empty_csv(meteo_path, METEO_COLS)

        meteo_df = pd.read_csv(meteo_path)

        # If user uploaded a file, enforce schema
        if meteo_path.name != "meteo_empty.csv":
            missing = set(METEO_COLS) - set(meteo_df.columns)
            if missing:
                return HttpResponse(
                    f"Meteorological file missing columns: {missing}", status=400
                )

        # Geometry files
        reservoir_gdf = gpd.read_file(save_uploaded_file("reservoir_geojson"))
        catchment_gdf = gpd.read_file(save_uploaded_file("catchment_geojson"))

        # Helpers for numeric inputs
        def safe_float(key, default=0.0):
            val = form.get(key)
            return np.float64(val.replace(",", "")) if val else np.float64(default)

        def safe_int(key, default=0):
            val = form.get(key)
            return np.int64(val.replace(",", "")) if val else np.int64(default)

        # Numeric inputs
        built_year = safe_int("built_year")
        obs_start_year = safe_int("obs_start_year")
        obs_end_year = safe_int("obs_end_year")

        height = safe_float("height", default=0.0)
        diff_catchment_area = safe_float("diff_CA_AreaKm2", default=0.0)
        cap_mcm = safe_float("cap_mcm")
        catchment_area = safe_float("catchment_area")
        basin_id = safe_int("BASIN_HYBAS_ID")
        lat = safe_float("Latitude")
        lon = safe_float("Longitude")

        # Extract geometries by GRILSS RID
        # Choose id column from all columns reservoir_gdf.columns. Remove geoemetry and show column list to user
        # User will proceed to select one column from the dropdown
        # The column name selected by the user will replace the GRILLS RID
        # User will proceed to select a specific value from the column selected from list of reservoir_gdf.unique which will replace target_id
        res_col = form.get("res_geom_id_col")
        res_val = form.get("res_geom_id_val")

        cat_col = form.get("cat_geom_id_col")
        cat_val = form.get("cat_geom_id_val")

        if not all([res_col, res_val, cat_col, cat_val]):
            return HttpResponse("Geometry identifiers not fully specified.", status=400)

        try:
            res_geom = reservoir_gdf.loc[
                reservoir_gdf[res_col].astype(str) == str(res_val), "geometry"
            ].iloc[0]
        except IndexError:
            return HttpResponse("Reservoir geometry not found.", status=400)

        try:
            cat_geom = catchment_gdf.loc[
                catchment_gdf[cat_col].astype(str) == str(cat_val), "geometry"
            ].iloc[0]
        except IndexError:
            return HttpResponse("Catchment geometry not found.", status=400)

        try:
            target_id = np.int64(res_val)
        except Exception:
            target_id = np.int64(1)

        # Build input dictionary for RECLAIM
        # Check if target_id is a valid integer otherwise replace with 1
        inputs = {
            "idx": target_id,
            "observation_period": [max(built_year, obs_start_year), obs_end_year],
            "reservoir_static_params": {
                "obc": cap_mcm,
                "hgt": height,
                "mrb": basin_id,
                "lat": lat,
                "lon": lon,
                "by": np.int64(built_year),
                "reservoir_polygon": res_geom,
                "aec_df": pd.read_csv(aec_path) if aec_path else None,
            },
            "catchment_static_params": {
                "ca": catchment_area,
                "dca": diff_catchment_area,
                "catchment_geometry": cat_geom,
                "glc_share_path": str(base_dir / "glc_share_combined.nc"),
                "hwsd2_path": str(base_dir / "hwsd2_soil_d1.nc"),
                "hilda_veg_freq_path": str(base_dir / "veg_gain_loss_1960_2019.nc"),
                "terrain_path": str(base_dir / "terrain.nc"),
            },
            "reservoir_dynamic_info": {
                "inflow": {
                    "path": inflow_path,
                    "time_column": "date",
                    "data_column": "inflow (m3/d)",
                },
                "outflow": {
                    "path": outflow_path,
                    "time_column": "date",
                    "data_column": "outflow (m3/d)",
                },
                "evaporation": {
                    "path": evaporation_path,
                    "time_column": "date",
                    "data_column": "evaporation (mm)",
                },
                "surface_area": {
                    "path": surface_area_path,
                    "time_column": "date",
                    "data_column": "area (km2)",
                },
                "nssc": {
                    "path": nssc_path,
                    "time_column": "date",
                    "data_column": NSSC2_COL,
                },
                "nssc2": {
                    "path": nssc_path,
                    "time_column": "date",
                    "data_column": NSSC1_COL,
                },
            },
            "catchment_dynamic_info": {
                "precip": {
                    "path": meteo_path,
                    "time_column": "time",
                    "data_column": "precip",
                },
                "tmin": {
                    "path": meteo_path,
                    "time_column": "time",
                    "data_column": "tmin",
                },
                "tmax": {
                    "path": meteo_path,
                    "time_column": "time",
                    "data_column": "tmax",
                },
                "wind": {
                    "path": meteo_path,
                    "time_column": "time",
                    "data_column": "wind",
                },
            },
            "time_interval": 1,
        }

        # Run RECLAIM model
        X = gf.create_features_per_reservoir(**inputs)
        model = Reclaim()
        model.load_model()
        preds = model.predict(
            X, log_transform=False, dynamic_weight=True, threshold=15, smooth_factor=0.7
        )
        # Attach predictions
        X["predictions"] = preds
        # Keep only OSY and predictions for the table
        result_df = X.loc[:, ["OSY", "predictions"]].copy()
        result_df.columns = ["Year", "Sedimentation Rate"]
        result_df.loc[:, "Year"] = result_df["Year"].astype(int)
        result_df.loc[:, "Sedimentation Rate"] = result_df["Sedimentation Rate"].round(
            4
        )
        
        print(result_df)
        # Save the result_df to session for CSV download
        request.session["reclaim_result_df"] = result_df.to_dict(orient="records")
        print("result_df saved to session")
        fig = px.line(
            result_df,
            x="Year",
            y="Sedimentation Rate",
            markers=True,
            title="Predicted Sedimentation Rate Over Time",
        )

        fig.update_layout(
            xaxis_title="Year",
            yaxis_title="Sedimentation Rate (MCM/year)",
            template="plotly_white",
            height=400,
        )

        fig_json = pio.to_json(fig)

        table_html = result_df.to_html(
            index=False,
            float_format="%.4f",
            classes="table table-striped",
        )

        # Convert selected reservoir geometry to GeoJSON
        res_gdf = gpd.GeoDataFrame(geometry=[res_geom], crs=reservoir_gdf.crs)
        res_gdf = res_gdf.to_crs(epsg=4326)
        res_geojson = json.loads(res_gdf.to_json())

        # Convert selected catchment geometry to GeoJSON
        cat_gdf = gpd.GeoDataFrame(geometry=[cat_geom], crs=catchment_gdf.crs)
        cat_gdf = cat_gdf.to_crs(epsg=4326)
        cat_geojson = json.loads(cat_gdf.to_json())

        basin_list = get_basin_list()
        sample_datasets = get_sample_datasets()

        return render(
            request,
            "mapapp/map.html",
            {
                "plot_x": result_df["Year"].tolist(),
                "plot_y": result_df["Sedimentation Rate"].tolist(),
                "show_results": True,
                "res_geojson": json.dumps(res_geojson),
                "cat_geojson": json.dumps(cat_geojson),
                "basin_list": basin_list,
                "sample_datasets": sample_datasets,
                "form_data": form,
                "current_year": datetime.datetime.now().year,
            },
        )

    except Exception as e:
        traceback.print_exc()
        return HttpResponse(f"Error processing request: {e}", status=500)
    finally:
        if upload_root.exists() and should_delete_uploaded_files():
            shutil.rmtree(upload_root)


def download_time_series(request):
    """Return the RECLAIM sedimentation time series as a CSV."""
    # Retrieve the predicted dataframe stored in session
    df = request.session.get("reclaim_result_df")
    if not df:
        return HttpResponse("No time series available for download.", status=404)

    # Convert dict stored in session back to DataFrame
    df = pd.DataFrame(df)

    # Create CSV in memory
    buffer = io.StringIO()
    df.to_csv(buffer, index=False)
    buffer.seek(0)

    response = HttpResponse(buffer, content_type="text/csv")
    response["Content-Disposition"] = (
        'attachment; filename="sedimentation_timeseries.csv"'
    )
    return response

def download_sample_zip(request, folder_name):
    """Return a generated ZIP file for the specified sample reservoir."""
    zip_path = BASE_DIR / "mapapp" / "sample_data" / f"{folder_name}.zip"
    if zip_path.exists():
        return FileResponse(open(zip_path, 'rb'), as_attachment=True, filename=f"{folder_name}.zip")
    raise Http404("Sample dataset zip not found.")
