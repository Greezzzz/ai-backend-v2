# UFW & SSH Tunnel — Amankan VPS, Tetap Bisa Akses Grafana/dkk

Dokumen ini untuk **production di VPS** (deploy docker compose). Isinya dua hal:

1. **Setup UFW** — tutup port infrastruktur dari internet, sisakan hanya yang
   memang publik.
2. **SSH tunnel** — cara tetap bisa buka Grafana/Prometheus/Jaeger/DB dari
   laptop padahal port-nya tidak lagi terbuka ke internet.

> Bacaan pendamping: `docs/learn/observability.md` (stack observability) dan
> bagian "Deploy" di `README.md`.

---

## 1. Kenapa perlu UFW

Saat `docker compose up` dengan `ports: "5433:5432"`, Docker mem-bind port ke
`0.0.0.0` — artinya **terbuka ke seluruh internet**, bukan cuma localhost.
Bot/scanner internet bisa mengetuk port tersebut. Yang paling berbahaya:

| Port | Service | Risiko kalau terbuka |
|------|---------|----------------------|
| `5433` | PostgreSQL | DB bisa diakses/dihapus dari internet |
| `6380` | Redis | Data/infra bisa dimanipulasi |
| `3000` | Grafana | Admin default bisa dicoba / dashboard bocor |
| `9090` | Prometheus | Info internal bocor |
| `16686`, `4318`, `4317` | Jaeger | Trace/telemetri bocor |
| `8000` | **App API** | **INI YANG PUBLIK** (dipakai aplikasi mobile) |
| `22` | SSH | Wajib buat admin — batasi ke IP sendiri kalau bisa |

**Aplikasi mobile hanya butuh port `8000`.** App container mengakses
Postgres/Redis lewat **network internal docker** (`postgres:5432`,
`redis:6379`), *bukan* lewat port host — jadi menutup port infra **tidak
memengaruhi aplikasi mobile sama sekali**.

---

## 2. Setup UFW di VPS

> Jalankan sebagai user dengan `sudo`. Jangan tutup port SSH sebelum punya
> koneksi cadangan — salah konfigurasi bisa mengunci diri sendiri.

### 2.1 Aturan dasar

```bash
# Allow SSH dulu (jangan sampai terkunci!)
sudo ufw allow OpenSSH
# atau kalau SSH di port non-default:
# sudo ufw allow 22/tcp

# Allow API app (port publik untuk mobile)
sudo ufw allow 8000/tcp

# Default: tolak semua koneksi masuk lain
sudo ufw default deny incoming
sudo ufw default allow outgoing
```

### 2.2 Nyalakan & cek status

```bash
sudo ufw enable
sudo ufw status verbose
```

Hasil yang diharapkan kurang lebih:

```
Status: active
To                         Action      From
--                         ------      ----
22/tcp                     ALLOW       Anywhere
8000/tcp                   ALLOW       Anywhere
22/tcp (v6)                ALLOW       Anywhere (v6)
8000/tcp (v6)              ALLOW       Anywhere (v6)
```

### 2.3 (Opsional) Batasi SSH ke IP kantor/kamu

```bash
sudo ufw delete allow 22/tcp            # hapus aturan allow semua
sudo ufw allow from <IP_KAMU> to any port 22 proto tcp
```

### 2.4 Verifikasi dari luar

Dari HP (data seluler, bukan WiFi kantor) atau VPS lain:

```bash
nc -vz <IP_VPS> 8000    # harus berhasil  (app publik)
nc -vz <IP_VPS> 5433    # harus gagal     (postgres tertutup)
nc -vz <IP_VPS> 3000    # harus gagal     (grafana tertutup)
```

Kalau port infra **masih** terbuka padahal UFW aktif, cek **firewall level
cloud** (security group AWS/GCP/Azure) — UFW di dalam VM tidak menutup port
yang sudah diizinkan di level cloud.

> Catatan Docker: UFW dan Docker kadang tidak akur karena Docker memodifikasi
> `iptables` sendiri — detail & solusinya di **2.5** dan **2.6** di bawah.

---

### 2.5 Build Docker putus (i/o timeout ke registry) setelah `ufw enable`

**Gejala:** `docker build` / `docker compose up -d --build` gagal dengan:

```
ERROR: failed to resolve source metadata ...
Head "https://registry-1.docker.io/v2/library/python/manifests/3.14-slim":
dial tcp <ip>:443: i/o timeout
```

**Penyebab:** saat `ufw enable`, UFW mengubah *default policy* chain
`FORWARD` iptables menjadi `DROP`. Container/build container butuh chain
`FORWARD` untuk routing keluar ke internet — jadi koneksi baru ke Docker Hub
ikut di-drop (container lama yang sudah jalan bisa tidak terasa karena
koneksinya masih lewat conntrack).

**Perbaikan:**

```bash
# 1) Izinkan forwarding — ini cuma routing antar/keluar container,
#    BUKAN membuka port masuk. Koneksi masuk (chain INPUT) tetap deny.
sudo sed -i 's/DEFAULT_FORWARD_POLICY="DROP"/DEFAULT_FORWARD_POLICY="ACCEPT"/' /etc/default/ufw
sudo ufw reload

# 2) Terapkan ulang aturan iptables Docker
sudo systemctl restart docker

# 3) Container mati setelah restart docker (compose prod tidak pakai
#    restart: unless-stopped) — hidupkan lagi dulu
cd /opt/apps/ai-backend
docker compose -f docker-compose.prod.yml up -d

# 4) Tes koneksi internet DARI DALAM CONTAINER (bukan dari host —
#    ini yang merepresentasikan kondisi build)
docker exec <nama-container-app> python -c \
  "import urllib.request; print(urllib.request.urlopen('https://registry-1.docker.io/v2/', timeout=15).status)"

# 5) Kalau sudah dapat status (200/401), build ulang
docker compose -f docker-compose.prod.yml up -d --build
```

> Kalau perintah panjang disalin dari chat lalu terpecah jadi beberapa baris
> (shell baca tiap baris terpisah), ketik ulang dalam **satu baris** utuh —
> terutama perintah `sed` yang memakai tanda kutip.

---

### 2.6 UFW tidak memblokir port yang di-publish Docker

UFW mengatur chain `INPUT`, tapi port bawaan compose (`ports: "5433:5432"`)
memakai DNAT Docker di chain `FORWARD` — akibatnya port infra **tetap terbuka
ke internet** walau UFW aktif, dan noise bot/scanner tetap masuk.

Cara yang benar-benar pasti menutup port infra dari internet: **bind
`127.0.0.1`** di compose:

```yaml
services:
  postgres:
    ports:
      - "127.0.0.1:5433:5432"   # hanya bisa diakses dari dalam server / SSH tunnel
```

- App container **tetap** bisa akses via network internal docker
  (`postgres:5432`, `redis:6379`) — tidak terpengaruh.
- Yang berubah hanya akses dari luar server: port tidak lagi bisa dihajar
  internet, tapi tetap bisa dibuka lewat SSH tunnel (lihat bagian 3).
- Biarkan app API tetap `"8000:8000"` supaya aplikasi mobile bisa akses.

---

## 3. SSH Tunnel — Akses Grafana/dkk dari Laptop

Dengan UFW aktif, port infra tertutup dari internet. Untuk buka Grafana,
Prometheus, Jaeger, atau DB dari laptop, buat **tunnel SSH**: koneksi aman
lewat port 22 yang mem-forward port lokal ke port di server.

### 3.1 Konsep

```
Laptop                 SSH tunnel (port 22)              VPS
browser ── localhost:3000 ───────────────────────────▶ 127.0.0.1:3000 (grafana)
psql    ── localhost:5433 ───────────────────────────▶ 127.0.0.1:5433 (postgres)
redis-cli── localhost:6380 ───────────────────────────▶ 127.0.0.1:6380 (redis)
```

Yang terbuka di internet tetap hanya port 22 (SSH) + 8000 (app). Semua port
infra hanya bisa diakses **dari dalam VPS** atau lewat tunnel.

### 3.2 Tunnel Grafana + Prometheus + Jaeger sekaligus

```bash
ssh -N -L 3000:localhost:3000 \
       -L 9090:localhost:9090 \
       -L 16686:localhost:16686 \
       ubuntu@<IP_VPS>
```

- `-N` = jangan buka shell, cuma forward port.
- Biarkan terminal ini berjalan.
- Lalu di browser laptop:
  - Grafana → `http://localhost:3000`
  - Prometheus → `http://localhost:9090`
  - Jaeger → `http://localhost:16686`

### 3.3 Tunnel PostgreSQL & Redis (untuk `psql` / `redis-cli` dari laptop)

```bash
ssh -N -L 5433:localhost:5433 -L 6380:localhost:6380 ubuntu@<IP_VPS>
```

Di terminal lain:

```bash
psql -h localhost -p 5433 -U postgres -d ai_backend_v2
redis-cli -h localhost -p 6380
```

### 3.4 Tunnel sekali untuk semua

```bash
ssh -N \
  -L 3000:localhost:3000 \
  -L 9090:localhost:9090 \
  -L 16686:localhost:16686 \
  -L 4318:localhost:4318 \
  -L 5433:localhost:5433 \
  -L 6380:localhost:6380 \
  ubuntu@<IP_VPS>
```

### 3.5 Windows (PowerShell / OpenSSH)

```powershell
ssh -N -L 3000:localhost:3000 ubuntu@<IP_VPS>
```

Kalau pakai PuTTY: buat session → Connection → SSH → Tunnels →
`Source port: 3000`, `Destination: localhost:3000`, pilih Local, Add.

### 3.6 Opsional: tetap buka Grafana dari HP tanpa tunnel

Kalau ingin akses dari HP tanpa SSH tunnel, jangan buka port 3000 ke semua —
cukup izinkan IP kamu (lihat 2.3) atau pasang reverse proxy + auth. Untuk
belajar, **SSH tunnel sudah cukup** dan paling aman.

---

## 4. Ringkasan port

| Port | Service | Internet | Akses |
|------|---------|----------|-------|
| `22` | SSH | (boleh, batasi IP) | langsung |
| `8000` | App API | **terbuka** | langsung |
| `3000` | Grafana | tertutup | SSH tunnel |
| `9090` | Prometheus | tertutup | SSH tunnel |
| `16686`, `4318`, `4317` | Jaeger | tertutup | SSH tunnel |
| `5433` | PostgreSQL | tertutup | SSH tunnel |
| `6380` | Redis | tertutup | SSH tunnel |

> Setelah UFW aktif, kalau ingin *benar-benar* memastikan port infra tidak
> bisa diakses dari container lain, pertimbangkan juga mengubah mapping port
> di compose menjadi `127.0.0.1:5433:5432` — tapi itu di luar lingkup dokumen
> ini (lihat README deploy).
