# Local RECLAIM setup

The app is in `/tiger1/msanchit/research/reclaim_web_app`; `.env/` is its Python 3.12 virtual environment, not a dotenv configuration file.

```bash
cd /tiger1/msanchit/research/reclaim_web_app
source .env/bin/activate
python manage.py runserver 127.0.0.1:8000
```

For access from your laptop, forward the port over SSH:

```bash
ssh -L 8000:127.0.0.1:8000 msanchit@f-hossain-7.ce.washington.edu
```

Then open http://localhost:8000. The development server must be running on the remote machine.

## Global datasets

The incomplete Zenodo download was cancelled and deleted. The app uses the existing datasets directly from:

`/tiger1/msanchit/research/sedimentation/RECLAIM_data/global_datasets`

All four required NetCDF files are present: `glc_share_combined.nc`, `hwsd2_soil_d1.nc`, `veg_gain_loss_1960_2019.nc`, and `terrain.nc`. No dataset copy is needed.

## Basin and sample inputs

The basin file is copied to `mapapp/basins_rat_sedi_v1.geojson` from `sedimentation/Rat_Run/rat_sedi_inputs`.

Bhakra (168), Naghlu (1), and Davis Bor (10257) have copied RAT final-output CSVs and individually extracted reservoir/catchment GeoJSONs in `mapapp/sample_data/<dam>/`. Downloadable ZIPs sit alongside these folders. See each sample's README for upload field mapping. Source outputs are from INDUS for Bhakra/Naghlu and COLORADO_also_COLORADO_RIVER for Davis Bor. Original source files are unchanged. All three samples passed estimator execution for 1984–2023. See [benchmark results and machine specifications](benchmark_results/README.md).

## Production prerequisites

This machine has enough hardware capacity, but university approval, inbound connectivity, a stable hostname, and uptime/backup arrangements must be confirmed before deployment.

- Install Nginx or Caddy for reverse proxying, static files, HTTPS, request limits, and timeouts. No reverse proxy was found on PATH during setup.
- Gunicorn is included in the Python environment. Run it under systemd with a dedicated service account and bounded worker/thread counts. Profile inference memory and latency before choosing concurrency.
- Obtain a domain and TLS certificate (Caddy can automate this; Nginx commonly uses Certbot). Arrange DNS and firewall access to ports 80/443.
- Use a private `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=false`, and explicit `DJANGO_ALLOWED_HOSTS`. Configure CSRF trusted origins, secure cookies, HTTPS redirects, and proxy trust for the actual proxy topology. Run `python manage.py check --deploy` with production settings.
- Consider PostgreSQL plus its Python driver for concurrent production usage. Current settings use SQLite; installing PostgreSQL alone does not switch the app database.
- Configure backups for the database and data, log rotation, monitoring, security updates, upload limits, retention, and disk quotas.
- For slow or concurrent inference, consider a task queue such as Celery/RQ with Redis, with corresponding application changes and job status handling.
- Review and load-test uploads and inference before public access. Do not use Django's development server for production.

Production services have not been installed or exposed publicly by this setup.
