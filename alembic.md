# Alembic Command Notes

Alembic digunakan untuk mengelola **database schema migration** pada project.

## 1. Initialize Alembic

```bash
alembic init alembic
```

Membuat struktur awal:

```text
alembic/
├── versions/
├── env.py
├── script.py.mako
└── README

alembic.ini
```

---

## 2. Create Migration

### Manual migration

```bash
alembic revision -m "migration description"
```

Digunakan ketika migration ditulis secara manual.

### Auto-generate migration

```bash
alembic revision --autogenerate -m "migration description"
```

Alembic membandingkan:

```text
SQLAlchemy Models
        ↓
Base.metadata
        ↓
Database Schema
```

Kemudian menghasilkan perubahan schema yang terdeteksi.

**Selalu review file migration hasil autogenerate sebelum menjalankannya.**

---

## 3. Apply Migration

### Apply semua migration sampai versi terbaru

```bash
alembic upgrade head
```

### Apply satu migration

```bash
alembic upgrade +1
```

---

## 4. Rollback Migration

### Rollback satu migration

```bash
alembic downgrade -1
```

### Rollback ke revision tertentu

```bash
alembic downgrade <revision_id>
```

### Rollback semua migration

```bash
alembic downgrade base
```

---

## 5. Check Migration Status

### Melihat revision database saat ini

```bash
alembic current
```

### Melihat seluruh migration history

```bash
alembic history
```

### Melihat history dalam bentuk verbose

```bash
alembic history --verbose
```

---

## 6. Menjalankan Migration ke Revision Tertentu

```bash
alembic upgrade <revision_id>
```

Contoh:

```bash
alembic upgrade a1b2c3d4
```

---

## 7. Membuat Migration dari Perubahan Model

Workflow normal:

```text
1. Modify SQLAlchemy Model
        ↓
2. Generate migration
        ↓
alembic revision --autogenerate -m "describe change"
        ↓
3. Review migration
        ↓
4. Apply migration
        ↓
alembic upgrade head
```

Contoh:

```bash
alembic revision --autogenerate -m "add conversation title"
alembic upgrade head
```

---

## 8. Important Commands

| Command                                    | Fungsi                                  |
| ------------------------------------------ | --------------------------------------- |
| `alembic current`                          | Melihat migration aktif                 |
| `alembic history`                          | Melihat history migration               |
| `alembic revision -m "..."`                | Membuat migration kosong                |
| `alembic revision --autogenerate -m "..."` | Generate migration dari perubahan model |
| `alembic upgrade head`                     | Apply seluruh migration terbaru         |
| `alembic upgrade +1`                       | Apply satu migration                    |
| `alembic downgrade -1`                     | Rollback satu migration                 |
| `alembic downgrade base`                   | Rollback seluruh migration              |

## Recommended Workflow

Untuk development:

```bash
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

Sebelum migration digunakan, **review file migration yang dihasilkan Alembic**. Jangan menganggap hasil `--autogenerate` selalu benar.
