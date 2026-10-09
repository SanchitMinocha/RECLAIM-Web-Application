import os,sys,json,time,resource,math
from pathlib import Path
from contextlib import ExitStack
root=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(root));os.chdir(root)
os.environ['DJANGO_SETTINGS_MODULE']='worldmap.settings'
import django
django.setup()
from django.test import Client
folder=sys.argv[1];sample=root/'mapapp/sample_data'/folder
meta=json.loads((sample/'metadata.json').read_text())
rid=json.loads((sample/'reservoir.geojson').read_text())['features'][0]['properties']['GRILSS RID']
data=dict(res_name=meta['name'],Latitude=meta['latitude'],Longitude=meta['longitude'],cap_mcm=meta['capacity'],height=meta['height'],catchment_area=meta['catchment_area'],diff_CA_AreaKm2=meta['diff_ca'],built_year=meta['built_year'],obs_start_year=1984,obs_end_year=2023,BASIN_HYBAS_ID=meta['basin_hybas_id'],res_geom_id_col='GRILSS RID',res_geom_id_val=str(rid),cat_geom_id_col='GRILSS RID',cat_geom_id_val=str(rid))
files={'aec_file':'aec.csv','inflow_file':'inflow.csv','outflow_file':'outflow.csv','evaporation_file':'evaporation.csv','surface_area_file':'sarea_tmsos.csv','nssc_file':'nssc.csv','meteo_file':'catchment_climate.csv','reservoir_geojson':'reservoir.geojson','catchment_geojson':'catchment.geojson'}
c=Client(HTTP_HOST='localhost')
start=time.perf_counter()
with ExitStack() as stack:
 for field,name in files.items():data[field]=stack.enter_context((sample/name).open('rb'))
 response=c.post('/run-reclaim/',data)
elapsed=time.perf_counter()-start
summary={'sample':folder,'period':[1984,2023],'http_status':response.status_code,'request_seconds':round(elapsed,2),'process_peak_rss_gib':round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024**2,3)}
rows=c.session.get('reclaim_result_df',[])
summary['prediction_rows']=len(rows)
if response.status_code==200 and len(rows)==40:
 assert all(math.isfinite(float(row['Sedimentation Rate'])) for row in rows)
 assert [int(row['Year']) for row in rows]==list(range(1984,2024))
 result=c.get('/download_time_series/')
 assert result.status_code==200
 (root/'benchmark_results'/f'{folder}_predictions.csv').write_bytes(result.content)
 summary['csv_download_status']=result.status_code
 summary['rate_min']=min(row['Sedimentation Rate'] for row in rows)
 summary['rate_max']=max(row['Sedimentation Rate'] for row in rows)
 summary['passed']=True
else:
 summary['passed']=False
 (root/'benchmark_results'/f'{folder}_error.html').write_bytes(response.content)
(root/'benchmark_results'/f'{folder}_benchmark.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary),flush=True)
assert summary['passed'],summary
