# Backend Training on Google Colab

Use Colab for the heavy backend work: generating `backend/data/synthetic_100k.parquet` and training `backend/data/model.pkl`.

## 1. Create a Clean Project Zip

From Git Bash on your laptop:

```bash
cd /e/TenzorXAI
zip -r TenzorXAI-colab.zip backend README.md LICENSE -x "backend/data/*"
```

Upload `TenzorXAI-colab.zip` to Colab. This keeps `.venv`, frontend dependencies, and old generated data out of the upload.

## 2. Run the Notebook

Open `notebooks/train_backend_on_colab.ipynb` in Google Colab and run the cells from top to bottom.

The notebook will:

- Upload and unzip your project.
- Install `backend/requirements.txt`.
- Run `backend/scripts/synthetic_generator.py`.
- Run `backend/scripts/train_model.py`.
- Zip and download the generated `backend/data` folder.

## 3. Copy Results Back Locally

After Colab downloads `backend_data.zip`, unzip it into your local project so these files exist:

```text
E:\TenzorXAI\backend\data\synthetic_100k.parquet
E:\TenzorXAI\backend\data\locality_metadata.csv
E:\TenzorXAI\backend\data\circle_rates.csv
E:\TenzorXAI\backend\data\locality_confidence.json
E:\TenzorXAI\backend\data\model.pkl
```

## 4. Run Only the API Locally

From Git Bash:

```bash
cd /e/TenzorXAI
source .venv/Scripts/activate
python -m uvicorn main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Then test:

```text
http://127.0.0.1:8000/health
```

If you want auto-reload during development, watch only the backend folder:

```bash
python -m uvicorn main:app --app-dir backend --reload --reload-dir backend --host 127.0.0.1 --port 8000
```
