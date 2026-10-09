# RECLAIM sample benchmarks and machine specifications

Recorded on October 9, 2026 (America/Los_Angeles).

All three sample reservoirs completed the Django estimator workflow for 1984–2023. Each returned HTTP 200, produced 40 finite annual predictions covering exactly those years, and exported a CSV with HTTP 200. This verifies execution and basic output structure; it does not establish scientific accuracy against observations.

## Results

| Reservoir | Request time (seconds) | Peak process RAM (GiB) | Annual predictions | Predicted rate range (MCM/year) | Validation |
|---|---:|---:|---:|---:|---|
| Bhakra | 20.87 | 0.904 | 40 | 12.0080–23.9259 | Passed |
| Naghlu | 13.67 | 0.608 | 40 | 4.1066–6.1957 | Passed |
| Davis Bor | 23.62 | 1.922 | 40 | 17.7218–27.0238 | Passed |

## Measurement method and limits

- Each reservoir ran once in a separate Python process, sequentially, using Django's test client to POST multipart sample files to `/run-reclaim/`. This invokes the real estimator view, model, database/session persistence, and template rendering. It does not exercise browser JavaScript, the network, or Gunicorn.
- Inputs match the sample metadata and default observation period (1984–2023); reservoir and catchment identifiers use `GRILSS RID`. No input values were adjusted for these benchmarks.
- Request time uses `time.perf_counter()` around the POST. It includes request processing, lazy imports, feature extraction, model loading/prediction, initial basin loading, rendering, and session persistence. It excludes process startup/Django setup and the subsequent CSV export request.
- Peak RAM uses Linux `resource.getrusage(RUSAGE_SELF).ru_maxrss`, converted from KiB to GiB. It is the maximum resident memory of the entire benchmark process through the POST, including interpreter/imports; it is not incremental inference memory or total machine memory. Child-process memory is not included.
- Operating-system disk caches were not cleared. These are fresh Python processes, not guaranteed cold-disk measurements. Other workloads, cache state, CPU threading, and storage performance can affect timings. No concurrency or sustained-load benchmark was performed.
- The development server remained available separately. Its memory is not included in benchmark process RAM.

## Machine specifications

| Item | Recorded specification |
|---|---|
| Hostname | `f-hossain-7.ce.washington.edu` |
| OS | Ubuntu 24.04.1 LTS (Noble Numbat) |
| Kernel / architecture | Linux 6.8.0-142-generic / x86_64 |
| CPU | 2 × Intel Xeon Gold 6242, nominal 2.80 GHz; reported maximum 3.90 GHz |
| CPU topology | 16 physical cores per socket, 32 physical cores total; 2 threads/core, 64 logical CPUs |
| NUMA | 2 nodes |
| RAM | 201,373,192,192 bytes, approximately 187.54 GiB usable reported by Linux |
| Available RAM at capture | Approximately 161.21 GiB; changes with other workloads |
| Swap | Approximately 2 GiB |
| App/data filesystem | `/tiger1` on `/dev/sda`: approximately 15 TiB total, 7.0 TiB used, 6.8 TiB free (rounded `df -h` values) |
| App/data disk | Seagate `ST16000NM000J-2TW103`, rotational HDD; reported device capacity 14.6 TiB |
| System filesystem | `/` on `/dev/nvme0n1p2`: approximately 1.9 TiB total, 1.1 TiB free |
| System disk | Micron `3400_MTFDKBA2T0TFH` NVMe SSD |
| Python | 3.12.3, project `.env/` virtual environment |
| Django / model package | Django 6.0.4 / pyreclaim 0.6.0 |
| Other key packages | NumPy 2.4.4, pandas 3.0.2, GeoPandas 1.1.3, scikit-learn 1.8.0, Gunicorn 25.3.0 |
| Database | SQLite |
| GPU | Not inventoried; no GPU requirement established by these benchmarks |

Repository base revision: `ef10134cfa2c5eeb0453e41d0c28f21f8a8ad191`, with local setup/template/path changes. This revision alone does not reproduce the modified working tree.

## Data locations and storage

Global inputs are read directly from `/tiger1/msanchit/research/sedimentation/RECLAIM_data/global_datasets`:

| File | Bytes |
|---|---:|
| `glc_share_combined.nc` | 513,591,970 |
| `hwsd2_soil_d1.nc` | 419,112,551 |
| `veg_gain_loss_1960_2019.nc` | 21,060,378 |
| `terrain.nc` | 16,796,687,738 |

These four files total approximately 16.53 GiB. Allow additional disk space for the Python environment, dashboard assets, samples, uploaded jobs, database, logs, backups, and any archives kept during deployment. These datasets were not hashed as part of this benchmark.

The basin file is `mapapp/basins_rat_sedi_v1.geojson`. Sample inputs are in `mapapp/sample_data/{Bhakra,Naghlu,Davis_Bor}/`, copied from RAT outputs and matching geometry records. Original RAT sources remain unchanged. Source basin/IDs: INDUS / 168 (Bhakra), INDUS / 1 (Naghlu), COLORADO_also_COLORADO_RIVER / 10257 (Davis Bor).

## Reproduce and inspect

From the project directory, with the configured datasets available:

```bash
.env/bin/python benchmark_results/run_sample_benchmark.py Bhakra
.env/bin/python benchmark_results/run_sample_benchmark.py Naghlu
.env/bin/python benchmark_results/run_sample_benchmark.py Davis_Bor
```

Reruns overwrite the corresponding benchmark JSON and prediction CSV, and create normal estimator uploads/sessions subject to the app's cleanup setting. Shell redirection can capture new logs if desired.

Supporting artifacts in this directory:

- `<sample>_benchmark.json`: runtime, RAM, output counts, status, and prediction range.
- `<sample>_predictions.csv`: exported annual predictions.
- `<sample>.log`: original execution logs.
- `machine_specs.json`: raw hardware/OS/resource snapshot and repository status.
- `environment.freeze.txt`: installed package versions.
- `run_sample_benchmark.py`: reproducible benchmark harness.

## Hosting interpretation

An 8 GB RAM VPS is a provisional starting point for a low-traffic deployment with one inference request at a time. The largest observed process peak was about 1.92 GiB for Davis Bor; other catchments or concurrent workers may require more. These measurements do not establish a minimum RAM requirement or predict VPS response time. CPU performance, thread counts, and disk access need to be measured on the chosen host before increasing concurrency. The current machine has substantially more resources than a small VPS.

See `../LOCAL_SETUP.md` for local startup and production prerequisites.
