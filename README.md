**BioDataMine**

**Understand your medical datasets before you train.**

BioDataMine is a medical data intelligence platform designed to ingest, analyze, and visualize medical datasets, 
with a strong focus on medical imaging. It helps teams understand what is actually inside their data 
before starting model training, annotation, or deployment.
_______________________________________________________________________________________________________________________

**Why BioDataMine?**

In medical AI, problems often start long before model training:

Unknown or mixed imaging modalities

Inconsistent anatomy coverage

Hidden dataset bias

Poor or missing metadata

Teams working on different dataset versions

BioDataMine solves this by making medical datasets transparent.
_______________________________________________________________________________________________________________________

**What BioDataMine Does**

Given a dataset URL (public dataset, archive, or storage bucket), BioDataMine:

🔗 Downloads and stores the dataset (local or S3-compatible storage)

🧠 Inspects files and metadata automatically

🖼️ Identifies 2D images vs 3D volumes

🏥 Detects imaging modality (CT, MRI, X-ray, Ultrasound, Optical, etc.)

🧍 Infers anatomy (chest, brain, cranial, liver, breast, etc.)

📊 Visualizes dataset composition (modality %, anatomy distribution)

👥 Enables team-based dataset sharing and collaboration

The goal is simple:

Know your medical data before you train.
_______________________________________________________________________________________________________________________

**Key Features**

URL-based dataset ingestion

Medical-imaging–aware analysis

Modality and anatomy distribution dashboards

2D vs 3D imaging detection

Local or S3-compatible storage

Team and dataset sharing
_______________________________________________________________________________________________________________________

**Who Is This For?**

Medical imaging ML engineers

AI researchers

Healthcare data scientists

Research labs and startups

Teams working with public or internal medical datasets
_______________________________________________________________________________________________________________________

**Project Status**

🚧 Actively under development

BioDataMine is currently in early development. APIs, features, and architecture may change as the project evolves.
_______________________________________________________________________________________________________________________

**Vision**

BioDataMine aims to become a dataset intelligence layer for medical AI, sitting between raw data and 
model training—making datasets understandable, comparable, and shareable.
_______________________________________________________________________________________________________________________

**Contributing**

Contributions, ideas, and feedback are welcome.
If you’re interested in medical imaging, data engineering, or healthcare AI, feel free to open an issue or pull request.
_______________________________________________________________________________________________________________________

**License**

MIT License
=======
# DataScan — Medical Image Analysis Platform (MVP Scaffold)

This repo is a starting implementation scaffold based on `Medical_Image_Analysis_System.txt`.

## What the MVP will do
- Ingest a **URL** that points to an archive (ex: `.zip`) or a single file.
- Extract files, **sniff** common medical formats:
  - DICOM (`.dcm` / DICM magic)
  - NIfTI (`.nii` / `.nii.gz`)
  - Common 2D images (`.png` / `.jpg`)
- Derive a first-pass metadata + summary:
  - **2D vs 3D** (basic heuristics)
  - **Modality** (DICOM tag-based; otherwise `unknown`)
  - Counts per modality for frontend pie chart
- Store **metadata in MongoDB** (files can be kept on local disk for MVP; later S3/MinIO).

## Project layout
- `backend/`: FastAPI API + ingestion/analysis services
- `docs/`: design notes (API, DB schema, component diagram)

## Quickstart (local)
1. Start MongoDB (no docker compose):

```bash
docker network create datascan-net 2>/dev/null || true
docker run -d --name datascan-mongo --network datascan-net -p 27017:27017 -v datascan_mongo:/data/db mongo:7
```

2. Run the API (pick one approach):

- A) Run locally with venv:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn app.main:app --app-dir backend --reload --port 8000
```

- B) Run as a Docker image:

```bash
docker build -t datascan-api:dev -f backend/Dockerfile .
docker run --rm --name datascan-api --network datascan-net -p 8000:8000 \
  -e DATASCAN_MONGO_URL=mongodb://datascan-mongo:27017 \
  -e DATASCAN_MONGO_DB=datascan \
  datascan-api:dev
```

3. Ingest a URL:

```bash
curl -X POST http://localhost:8000/datasets/ingest \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://example.com/some-dataset.zip","name":"Example dataset"}'
```

## Next steps
See `docs/component_level_architecture.md` for the proposed component/API/DB design, and how to extend this MVP into:
- Celery/Redis background processing
- S3/MinIO object storage
- JWT auth + team sharing roles (Owner/Editor/Viewer)
