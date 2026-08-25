# UV Cheat Sheet untuk Development & Production

> Ringkasan command `uv` yang paling sering digunakan untuk pengembangan aplikasi Python, khususnya FastAPI.

---

# 1. Inisialisasi Project

Membuat project baru.

```bash
uv init my-project

Atau pada folder yang sudah ada:

uv init

Struktur project:

my-project/
├── pyproject.toml
├── .python-version
├── src/
└── README.md
2. Virtual Environment

Membuat virtual environment.

uv venv

Menggunakan versi Python tertentu.

uv venv --python 3.12

atau

uv venv --python python3.12
3. Mengelola Python

Install Python.

uv python install 3.12

Melihat versi yang tersedia.

uv python list

Mengunci versi Python project.

uv python pin 3.12

File .python-version akan dibuat otomatis.

4. Menambahkan Dependency

Install package.

uv add fastapi

Beberapa package sekaligus.

uv add fastapi uvicorn sqlalchemy

Versi tertentu.

uv add "fastapi>=0.116,<1.0"

Package dari GitHub.

uv add git+https://github.com/tiangolo/fastapi.git

Editable install.

uv add -e .
5. Development Dependency

Install package khusus development.

uv add --dev pytest

Contoh lengkap.

uv add --dev black ruff mypy pytest

Hasil pada pyproject.toml.

[dependency-groups]
dev = [
    "black",
    "ruff",
    "mypy",
    "pytest"
]
6. Sinkronisasi Environment

Install semua dependency sesuai pyproject.toml.

uv sync

Production (menggunakan lock file).

uv sync --locked

Production tanpa dependency development.

uv sync --locked --no-dev
7. Menjalankan Program

Menjalankan script Python.

uv run python main.py

FastAPI.

uv run python -m uvicorn app.main:app --reload

Pytest.

uv run pytest

Alembic.

uv run alembic upgrade head

Black.

uv run black .

Ruff.

uv run ruff check .

Mypy.

uv run mypy .
8. Dependency Tree

Melihat dependency project.

uv tree

Contoh output.

fastapi
├── starlette
├── pydantic
└── typing-extensions
9. Update Dependency

Update semua package.

uv lock --upgrade

Update satu package.

uv lock --upgrade-package fastapi

Sinkronkan.

uv sync
10. Menghapus Dependency

Menghapus package.

uv remove fastapi

Menghapus dev dependency.

uv remove --dev pytest
11. Lock Dependency

Generate lock file.

uv lock

File yang dihasilkan.

uv.lock

Disarankan untuk di-commit ke Git.

12. Export Requirements

Untuk deployment yang masih menggunakan pip.

uv export -o requirements.txt

Tanpa dev dependency.

uv export --no-dev -o requirements.txt
13. UV Pip (Kompatibilitas)

Install dari requirements.

uv pip install -r requirements.txt

Melihat package.

uv pip list

Freeze package.

uv pip freeze

Reinstall package.

uv pip install --reinstall uvicorn
14. UV Tool

Menjalankan tool tanpa install permanen.

uvx ruff check .

atau

uv tool run ruff check .

Install tool global.

uv tool install pre-commit

Melihat tool.

uv tool list

Update tool.

uv tool upgrade pre-commit

Hapus tool.

uv tool uninstall pre-commit
15. Cache

Melihat lokasi cache.

uv cache dir

Membersihkan cache.

uv cache clean
Workflow Development
Setup Project
uv init
uv python pin 3.12
uv venv
Install Dependency
uv add fastapi uvicorn sqlalchemy
uv add --dev pytest black ruff mypy
Jalankan Aplikasi
uv run python -m uvicorn app.main:app --reload
Testing
uv run pytest
Linting
uv run ruff check .
Formatting
uv run black .
Type Checking
uv run mypy .
Update Dependency
uv lock --upgrade
uv sync
Workflow Production

Clone project.

git clone <repository>
cd project

Install dependency sesuai lock file.

uv sync --locked --no-dev

Menjalankan FastAPI.

uv run python -m uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000

Contoh menggunakan Gunicorn (Linux).

uv run gunicorn app.main:app \
    -k uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --workers 4
    
Cheat Sheet
Kebutuhan	Command
Inisialisasi project	uv init
Buat virtual environment	uv venv
Install Python	uv python install <version>
Pin Python	uv python pin <version>
Install package	uv add <package>
Install dev package	uv add --dev <package>
Hapus package	uv remove <package>
Sinkronisasi environment	uv sync
Install sesuai lock	uv sync --locked
Jalankan program	uv run ...
Lihat dependency	uv tree
Generate lock	uv lock
Update dependency	uv lock --upgrade
Update satu package	uv lock --upgrade-package <package>
Export requirements	uv export -o requirements.txt
Install tool	uv tool install <tool>
Jalankan tool sementara	uvx <tool>
Bersihkan cache	uv cache clean
List package	uv pip list
Freeze package	uv pip freeze