import os
import sys
import json
import shutil
import pathlib
import pandas as pd
import geopandas as gpd

def get_base_dir():
    return pathlib.Path(__file__).resolve().parent

def build_sample_dataset(rid):
    base = get_base_dir()
    dam_info_path = base / "rat_outputs" / "dam_info.xlsx"
    reservoirs_geojson = base / "rat_outputs" / "reservoirs_rat_sedi_v1.geojson"
    catchments_geojson = base / "rat_outputs" / "catchments_rat_sedi_v1.geojson"
    final_outputs = base / "rat_outputs" / "final_outputs"
    
    # 1. Read dam_info.xlsx to find the row for this RID
    if not dam_info_path.exists():
        print(f"Error: {dam_info_path} not found.")
        sys.exit(1)
        
    df = pd.read_excel(dam_info_path, engine="openpyxl")
    row = df[df["GRILSS RID"] == rid]
    if row.empty:
        print(f"Error: RID {rid} not found in dam_info.xlsx")
        sys.exit(1)
        
    row = row.iloc[0]
    res_name = row["Reservoir"]
    
    # Clean the name to create a safe directory
    safe_name = f"{str(res_name).replace(' ', '_').replace('/', '_')}"
    sample_dir = base / "sample_data" / safe_name
    sample_dir.mkdir(parents=True, exist_ok=True)
    
    # Extract metadata properties for auto-fill functionality
    metadata = {
        "name": res_name,
        "country": str(row["Country"]),
        "basin": str(row.get("Major River Basin", "")),
        "basin_hybas_id": str(row.get("BASIN_HYBAS_ID", "")),
        "latitude": float(row["Latitude"]),
        "longitude": float(row["Longitude"]),
        "catchment_area": float(row.get("Catchment Area (Km^2)", 0.0)),
        "height": float(row.get("Height (m)", 0.0)),
        "capacity": float(row.get("Cap (MCM)", 0.0)),
        "built_year": int(row.get("Built Year", 0)),
        "diff_ca": float(row.get("diff_CA_AreaKm2", 0.0))
    }
    
    # Save metadata
    with open(sample_dir / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=4)
        
    print(f"[*] Processing {res_name} (RID: {rid})")
        
    # 2. Extract & Copy Dynamic Files
    dynamics = {
        "inflow": "inflow.csv",
        "outflow": "outflow.csv",
        "evaporation": "evaporation.csv",
        "sarea_tmsos": "surface_area.csv",
        "catchment_climate": "meteo.csv",
        "nssc": "nssc.csv",
        "aec": "aec.csv"
    }
    
    search_str = f"{rid}_"
    for folder_name, new_name in dynamics.items():
        src_folder = final_outputs / folder_name
        if not src_folder.exists():
            continue
        
        # Find the file starting with "{rid}_"
        matching_files = list(src_folder.glob(f"{search_str}*.csv"))
        if matching_files:
            shutil.copy(matching_files[0], sample_dir / new_name)
            print(f"  -> Copied {new_name}")
        else:
            print(f"  [!] Missing {new_name}")

    # 3. GeoJSON Filtering
    def filter_geojson(src, dest, rid):
        if not src.exists():
            print(f"  [!] Missing geometry file {src.name}")
            return
            
        gdf = gpd.read_file(src)
        # Search properties for GRILSS RID
        filtered = gdf[gdf["GRILSS RID"] == rid]
        if not filtered.empty:
            filtered.to_file(dest, driver="GeoJSON")
            print(f"  -> Extracted geometry to {dest.name}")
        else:
            print(f"  [!] RID {rid} not found in {src.name}")

    filter_geojson(reservoirs_geojson, sample_dir / "reservoir.geojson", rid)
    filter_geojson(catchments_geojson, sample_dir / "catchment.geojson", rid)
            
    # 4. Create ZIP package for users to download directly via UI
    zip_target = base / "sample_data" / safe_name
    shutil.make_archive(str(zip_target), 'zip', str(sample_dir))
    print(f"[*] Created Zip Output: {zip_target}.zip")
    
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generate Sample Dataset for UI.")
    parser.add_argument("--rid", type=int, required=True, help="GRILSS RID of the dam")
    args = parser.parse_args()
    build_sample_dataset(args.rid)
