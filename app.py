from flask import Flask, render_template, request, redirect, url_for, session, flash
from pymongo import MongoClient
import os
from dotenv import load_dotenv
import hashlib
from bson.objectid import ObjectId
from werkzeug.utils import secure_filename
import datetime
import re
from urllib.parse import urlparse, parse_qs
import requests
import subprocess
from bson.errors import InvalidId 

# Load environment variables from .env
load_dotenv()

# Konfigurasi dari .env
MONGODB_URI = os.getenv("MONGODB_URI")
DB_NAME = os.getenv("DB_NAME")
SECRET_KEY = os.getenv("SECRET_KEY")

# Konfigurasi upload folder
UPLOAD_FOLDER = 'static/uploads/berita'
UPLOAD_FOLDER_VIDEO = 'static/uploads/video'
UPLOAD_FOLDER_THUMBNAIL = 'static/uploads/video/thumbnails'
UPLOAD_FOLDER_PHOTOS = 'static/uploads/photos'
UPLOAD_FOLDER_TEACHERS = 'static/uploads/teachers'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'webm', 'ogg'}

# Inisialisasi Flask
app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['UPLOAD_FOLDER_VIDEO'] = UPLOAD_FOLDER_VIDEO
app.config['UPLOAD_FOLDER_THUMBNAIL'] = UPLOAD_FOLDER_THUMBNAIL
app.config['UPLOAD_FOLDER_PHOTOS'] = UPLOAD_FOLDER_PHOTOS
app.config['UPLOAD_FOLDER_TEACHERS'] = UPLOAD_FOLDER_TEACHERS

# Koneksi MongoDB
client = MongoClient(MONGODB_URI)
db = client[DB_NAME]
users_collection = db.users

# Memastikan folder upload ada
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(UPLOAD_FOLDER_VIDEO, exist_ok=True)
os.makedirs(UPLOAD_FOLDER_THUMBNAIL, exist_ok=True)
os.makedirs(UPLOAD_FOLDER_PHOTOS, exist_ok=True)
os.makedirs(UPLOAD_FOLDER_TEACHERS, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def allowed_video_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_VIDEO_EXTENSIONS

def get_youtube_id(url):
    """Ekstrak YouTube video ID dari URL dengan lebih baik"""
    try:
        if 'youtube.com/watch' in url:
            return parse_qs(urlparse(url).query)['v'][0]
        elif 'youtu.be/' in url:
            return urlparse(url).path[1:]
        elif 'youtube.com/embed/' in url:
            return urlparse(url).path.split('/')[-1]
    except Exception as e:
        print(f"Error extracting YouTube ID: {e}")
        return None
    return None

def get_youtube_thumbnail(video_id):
    """Dapatkan thumbnail URL dari YouTube video"""
    return f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"

# Fungsi untuk membuat admin jika belum ada (dijalankan hanya sekali saat setup)
def create_admin():
    username = "superadmin"
    password = "superadminpassword"  # Password untuk Super Admin
    pw_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()
    
    if not users_collection.find_one({"username": username}):
        users_collection.insert_one({
            "username": username,
            "password": pw_hash,
            "role": "super_admin"  # Set role sebagai Super Admin
        })
        print("Super Admin berhasil dibuat: username=superadmin, password=superadminpassword")
    else:
        print("Super Admin sudah ada.")

# Panggil fungsi untuk membuat admin hanya sekali (Anda bisa menghapus ini setelah admin dibuat)
# create_admin()

# Fungsi slugify
def slugify(text):
    return re.sub(r'[\W_]+', '-', text.lower()).strip('-')

# Daftarkan filter slugify
app.jinja_env.filters['slugify'] = slugify

@app.route('/')
def index():
    # Ambil 3 berita terbaru dari database
    berita_terbaru = list(db.berita.find().sort("tanggal", -1).limit(3))  # Mengambil 3 berita terbaru
    
    # Ambil 3 video terbaru dari database
    videos = list(db.videos.find().sort("tanggal", -1).limit(3))  # Mengambil 3 video terbaru
    photos = list(db.photos.find().sort("tanggal", -1).limit(4))  # Mengambil 4 foto terbaru
    
    return render_template('pages/index.html', berita=berita_terbaru, videos=videos, photos=photos)

# Route untuk halaman login di /admin/login
@app.route("/admin/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("pages/admin/login.html")
    
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        pw_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()
        
        # Mencari pengguna di database
        user = users_collection.find_one({"username": username})
        if user and user["password"] == pw_hash:
            # Jika login berhasil, simpan informasi pengguna di session
            session["user_id"] = str(user["_id"])
            session["username"] = user["username"]  # Simpan username
            session["role"] = user["role"]  # Simpan role jika diperlukan
            flash("Login berhasil!", "success")
            return redirect(url_for("dashboard"))  # Arahkan ke dashboard
        else:
            flash("Username atau password salah!", "danger")
            return redirect(url_for("login"))  # Kembali ke halaman login jika gagal

# Route untuk dashboard
@app.route('/admin/dashboard')
def dashboard():
    if not session.get('user_id'):
        return redirect(url_for('login'))

    # Memastikan 'username' ada di session
    username = session.get('username', 'Guest')  # Gunakan 'Guest' jika 'username' tidak ditemukan

    total_pengguna = db.users.count_documents({})
    total_berita = db.berita.count_documents({})
    total_video = db.videos.count_documents({})
    total_foto = db.foto.count_documents({})
    total_pengajar = db.teachers.count_documents({})

    # Data untuk grafik
    pengguna_minggu_ini = 5  # Ganti dengan logika untuk menghitung pengguna minggu ini
    berita_hari_ini = 2  # Ganti dengan logika untuk menghitung berita hari ini
    video_minggu_ini = 3  # Ganti dengan logika untuk menghitung video minggu ini
    foto_minggu_ini = 4  # Ganti dengan logika untuk menghitung foto minggu ini
    pengajar_minggu_ini = 1  # Ganti dengan logika untuk menghitung pengajar minggu ini

    return render_template('pages/admin/dashboard.html', 
                           username=username,  # Kirimkan username yang sudah diambil dari session
                           total_pengguna=total_pengguna,
                           total_berita=total_berita,
                           total_video=total_video,
                           total_foto=total_foto,
                           total_pengajar=total_pengajar,
                           pengguna_minggu_ini=pengguna_minggu_ini,
                           berita_hari_ini=berita_hari_ini,
                           video_minggu_ini=video_minggu_ini,
                           foto_minggu_ini=foto_minggu_ini,
                           pengajar_minggu_ini=pengajar_minggu_ini)


# Route untuk logout
@app.route("/logout")
def logout():
    session.clear()  # Menghapus semua data dalam session
    flash("Anda telah logout.", "info")
    return redirect(url_for('index'))  # Kembali ke halaman beranda setelah logout

# Route untuk kelola pengguna
@app.route('/admin/kelola-pengguna')
def kelola_pengguna():
    user_id = session.get('user_id')
    if not user_id:
        flash("Anda harus login terlebih dahulu!", "danger")
        return redirect(url_for("login"))

    user = users_collection.find_one({"_id": ObjectId(user_id)})
    if not user or user.get("role") not in ["super_admin", "admin"]:
        flash("Akses hanya untuk admin.", "danger")
        return redirect(url_for("login"))

    users = list(users_collection.find())
    return render_template("pages/admin/kelola_pengguna.html", users=users)

# Route untuk tambah pengguna
@app.route('/admin/kelola-pengguna/tambah', methods=['POST'])
def tambah_pengguna():
    if not session.get('user_id'):
        return {"status": "error", "message": "Unauthorized"}, 401

    user = users_collection.find_one({"_id": ObjectId(session.get('user_id'))})
    if user.get("role") != "super_admin":
        return {"status": "error", "message": "Hanya Super Admin yang dapat menambah pengguna."}, 403

    username = request.form.get('username')
    password = request.form.get('password')
    role = request.form.get('role', 'admin')  # Default role adalah 'admin'

    # Cek apakah username sudah ada
    if users_collection.find_one({"username": username}):
        return {"status": "error", "message": "Username sudah digunakan"}, 400

    # Hash password
    pw_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()

    # Insert user baru
    users_collection.insert_one({
        "username": username,
        "password": pw_hash,
        "role": role
    })

    return {"status": "success", "message": "Pengguna berhasil ditambahkan"}, 200

# Route untuk edit pengguna
@app.route('/admin/kelola-pengguna/edit/<user_id>', methods=['POST'])
def edit_pengguna(user_id):
    if not session.get('user_id'):
        return {"status": "error", "message": "Unauthorized"}, 401

    user = users_collection.find_one({"_id": ObjectId(session.get('user_id'))})
    if user.get("role") == "admin":
        return {"status": "error", "message": "Admin tidak memiliki hak untuk mengedit pengguna."}, 403

    username = request.form.get('username')
    password = request.form.get('password')
    role = request.form.get('role', 'admin')

    update_data = {
        "username": username,
        "role": role
    }

    # Update password hanya jika diisi
    if password:
        update_data["password"] = hashlib.sha256(password.encode("utf-8")).hexdigest()

    users_collection.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": update_data}
    )
    return {"status": "success", "message": "Pengguna berhasil diperbarui"}, 200

# Route untuk hapus pengguna
@app.route('/admin/kelola-pengguna/hapus/<user_id>', methods=['DELETE'])
def hapus_pengguna(user_id):
    if not session.get('user_id'):
        return {"status": "error", "message": "Unauthorized"}, 401

    user = users_collection.find_one({"_id": ObjectId(session.get('user_id'))})
    if user.get("role") != "super_admin":
        return {"status": "error", "message": "Hanya Super Admin yang dapat menghapus pengguna."}, 403

    # Pastikan tidak menghapus diri sendiri
    if user_id == session.get('user_id'):
        return {"status": "error", "message": "Tidak dapat menghapus akun sendiri"}, 400

    users_collection.delete_one({"_id": ObjectId(user_id)})
    return {"status": "success", "message": "Pengguna berhasil dihapus"}, 200

# Route untuk kelola berita
@app.route('/admin/kelola-berita')
def kelola_berita():
    if not session.get('user_id'):
        flash("Anda harus login terlebih dahulu!", "danger")
        return redirect(url_for("login"))
    
    berita = list(db.berita.find().sort("tanggal", -1))
    return render_template("pages/admin/kelola_berita.html", berita=berita)

# Route untuk tambah berita
@app.route('/admin/kelola-berita/tambah', methods=['POST'])
def tambah_berita():
    if not session.get('user_id'):
        return {"status": "error", "message": "Unauthorized"}, 401

    judul = request.form.get('judul')
    isi = request.form.get('isi')
    kategori = request.form.get('kategori')
    
    # Data dasar berita
    berita_data = {
        "judul": judul,
        "isi": isi,
        "kategori": kategori,
        "tanggal": datetime.datetime.now(),
        "penulis": users_collection.find_one({"_id": ObjectId(session['user_id'])})['username']
    }
    
    # Handle foto jika ada
    if 'foto' in request.files:
        file = request.files['foto']
        if file and file.filename != '' and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filename = f"{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            berita_data["foto"] = filename
        else:
            berita_data["foto"] = "default.jpg"  # Gunakan gambar default jika tidak ada upload
    else:
        berita_data["foto"] = "default.jpg"  # Gunakan gambar default jika tidak ada file

    # Simpan ke database
    db.berita.insert_one(berita_data)
    
    return {"status": "success", "message": "Berita berhasil ditambahkan"}, 200

# Route untuk edit berita
@app.route('/admin/kelola-berita/edit/<berita_id>', methods=['POST'])
def edit_berita(berita_id):
    if not session.get('user_id'):
        return {"status": "error", "message": "Unauthorized"}, 401

    berita = db.berita.find_one({"_id": ObjectId(berita_id)})
    if not berita:
        return {"status": "error", "message": "Berita tidak ditemukan"}, 404

    update_data = {
        "judul": request.form.get('judul'),
        "isi": request.form.get('isi'),
        "kategori": request.form.get('kategori')
    }

    # Handle foto baru jika ada
    if 'foto' in request.files and request.files['foto'].filename != '':
        file = request.files['foto']
        if allowed_file(file.filename):
            # Hapus foto lama jika ada
            if berita.get('foto'):
                old_file = os.path.join(app.config['UPLOAD_FOLDER'], berita['foto'])
                if os.path.exists(old_file):
                    os.remove(old_file)
            
            filename = secure_filename(file.filename)
            filename = f"{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            update_data['foto'] = filename

    db.berita.update_one(
        {"_id": ObjectId(berita_id)},
        {"$set": update_data}
    )

    return {"status": "success", "message": "Berita berhasil diperbarui"}, 200

# Route untuk hapus berita
@app.route('/admin/kelola-berita/hapus/<berita_id>', methods=['DELETE'])
def hapus_berita(berita_id):
    if not session.get('user_id'):
        return {"status": "error", "message": "Unauthorized"}, 401

    berita = db.berita.find_one({"_id": ObjectId(berita_id)})
    if berita and berita.get('foto'):
        # Hapus file foto
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], berita['foto'])
        if os.path.exists(file_path) and berita['foto'] != 'default.jpg':
            os.remove(file_path)

    db.berita.delete_one({"_id": ObjectId(berita_id)})
    return {"status": "success", "message": "Berita berhasil dihapus"}, 200

# Route untuk upload media (gambar/video) dari editor
@app.route('/admin/upload-media', methods=['POST'])
def upload_media():
    if not session.get('user_id'):
        return {"status": "error", "message": "Unauthorized"}, 401

    if 'file' not in request.files:
        return {"status": "error", "message": "Tidak ada file"}, 400

    file = request.files['file']
    if file.filename == '':
        return {"status": "error", "message": "Tidak ada file yang dipilih"}, 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filename = f"{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        
        # Return URL untuk file yang diupload
        file_url = url_for('static', filename=f'uploads/berita/{filename}')
        return {"status": "success", "url": file_url}, 200

    return {"status": "error", "message": "Format file tidak diizinkan"}, 400

# Route untuk kelola video
@app.route('/admin/kelola-video')
def kelola_video():
    if not session.get('user_id'):
        flash("Anda harus login terlebih dahulu!", "danger")
        return redirect(url_for("login"))
    
    videos = list(db.videos.find().sort("tanggal", -1))
    return render_template("pages/admin/kelola_video.html", videos=videos)

# Route untuk tambah video
@app.route('/admin/kelola-video/tambah', methods=['POST'])
def tambah_video():
    if not session.get('user_id'):
        return {"status": "error", "message": "Unauthorized"}, 401

    try:
        judul = request.form.get('judul')
        deskripsi = request.form.get('deskripsi')
        upload_type = request.form.get('type')

        if not judul:
            return {"status": "error", "message": "Judul harus diisi"}, 400

        video_data = {
            "judul": judul,
            "deskripsi": deskripsi,
            "tanggal": datetime.datetime.now(),
            "type": upload_type,
            "uploader": users_collection.find_one({"_id": ObjectId(session['user_id'])})['username']
        }

        if upload_type == 'youtube':
            youtube_url = request.form.get('youtube_url')
            video_id = get_youtube_id(youtube_url)
            
            if not video_id:
                return {"status": "error", "message": "URL YouTube tidak valid"}, 400
            
            # Simpan URL embed yang benar
            embed_url = f"https://www.youtube.com/embed/{video_id}"
            video_data.update({
                "url": embed_url,  # Gunakan embed URL
                "original_url": youtube_url,  # Simpan URL asli jika diperlukan
                "thumbnail_url": f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
                "youtube_id": video_id
            })

        else:  # Local file upload
            if 'video_file' not in request.files:
                return {"status": "error", "message": "File video harus dipilih"}, 400
            
            file = request.files['video_file']
            if file.filename == '':
                return {"status": "error", "message": "File video harus dipilih"}, 400
            
            if not allowed_video_file(file.filename):
                return {"status": "error", "message": "Format file tidak diizinkan"}, 400
            
            # Simpan video
            video_filename = secure_filename(file.filename)
            video_filename = f"{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{video_filename}"
            file.save(os.path.join(UPLOAD_FOLDER_VIDEO, video_filename))
            
            # Gunakan thumbnail default untuk sementara
            thumbnail_path = 'default_video_thumb.jpg'
            
            video_data.update({
                "url": url_for('static', filename=f'uploads/video/{video_filename}'),
                "file_name": video_filename,
                "thumbnail": thumbnail_path
            })

        # Simpan ke database
        db.videos.insert_one(video_data)
        return {"status": "success", "message": "Video berhasil ditambahkan"}, 200

    except Exception as e:
        print(f"Error: {str(e)}")  # Untuk debugging
        return {"status": "error", "message": "Terjadi kesalahan saat menambah video"}, 500

# Route untuk edit video
@app.route('/admin/kelola-video/edit/<video_id>', methods=['POST'])
def edit_video(video_id):
    if not session.get('user_id'):
        return {"status": "error", "message": "Unauthorized"}, 401

    print(f"Received video_id: {video_id}")  # Log ID yang diterima

    try:
        # Validasi ID
        if len(video_id) != 24:
            return {"status": "error", "message": "ID video tidak valid"}, 400

        # Coba untuk mengonversi ID menjadi ObjectId
        try:
            video_object_id = ObjectId(video_id)
        except Exception as e:
            return {"status": "error", "message": "ID video tidak valid"}, 400

        video = db.videos.find_one({"_id": video_object_id})
        if not video:
            return {"status": "error", "message": "Video tidak ditemukan"}, 404

        update_data = {
            "judul": request.form.get('judul'),
            "deskripsi": request.form.get('deskripsi')
        }

        # Jika ada perubahan video
        if 'video_file' in request.files and request.files['video_file'].filename != '':
            # Hapus file lama jika local video
            if video.get('type') == 'local' and video.get('file_name'):
                old_video_path = os.path.join(UPLOAD_FOLDER_VIDEO, video['file_name'])
                if os.path.exists(old_video_path):
                    os.remove(old_video_path)

            file = request.files['video_file']
            if allowed_video_file(file.filename):
                filename = secure_filename(file.filename)
                filename = f"{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
                file.save(os.path.join(UPLOAD_FOLDER_VIDEO, filename))
                update_data.update({
                    "url": url_for('static', filename=f'uploads/video/{filename}'),
                    "file_name": filename
                })

        # Update YouTube URL
        if request.form.get('youtube_url'):
            video_id = get_youtube_id(request.form.get('youtube_url'))
            if video_id:
                update_data.update({
                    "url": request.form.get('youtube_url'),
                    "youtube_id": video_id,
                    "thumbnail_url": get_youtube_thumbnail(video_id)
                })

        db.videos.update_one(
            {"_id": video_object_id},
            {"$set": update_data}
        )

        return {"status": "success", "message": "Video berhasil diperbarui"}, 200

    except Exception as e:
        return {"status": "error", "message": str(e)}, 500

# Route untuk hapus video
@app.route('/admin/kelola-video/hapus/<video_id>', methods=['DELETE'])
def hapus_video(video_id):
    if not session.get('user_id'):
        return {"status": "error", "message": "Unauthorized"}, 401

    try:
        video = db.videos.find_one({"_id": ObjectId(video_id)})
        if not video:
            return {"status": "error", "message": "Video tidak ditemukan"}, 404

        # Hapus file jika video lokal
        if video.get('type') == 'local' and video.get('file_name'):
            video_path = os.path.join(UPLOAD_FOLDER_VIDEO, video['file_name'])
            if os.path.exists(video_path):
                os.remove(video_path)

            # Hapus thumbnail jika ada
            if video.get('thumbnail'):
                thumb_path = os.path.join(UPLOAD_FOLDER_THUMBNAIL, video['thumbnail'])
                if os.path.exists(thumb_path):
                    os.remove(thumb_path)

        db.videos.delete_one({"_id": ObjectId(video_id)})
        return {"status": "success", "message": "Video berhasil dihapus"}, 200

    except Exception as e:
        return {"status": "error", "message": str(e)}, 500

def generate_thumbnail(video_path, output_path):
    try:
        subprocess.run([
            'ffmpeg', '-i', video_path,
            '-ss', '00:00:01',  # ambil frame pertama
            '-vframes', '1',
            output_path
        ], check=True)
        return True
    except:
        return False

@app.route('/admin/kelola-foto')
def kelola_foto():
    if not session.get('user_id'):
        return {"status": "error", "message": "Unauthorized"}, 401

    photos = list(db.photos.find().sort("tanggal", -1))
    return render_template("pages/admin/kelola_foto.html", photos=photos)

@app.route('/admin/kelola-foto/tambah', methods=['POST'])
def tambah_foto():
    if not session.get('user_id'):
        return {"status": "error", "message": "Unauthorized"}, 401

    judul = request.form.get('judul')
    deskripsi = request.form.get('deskripsi')

    if 'foto' not in request.files:
        return {"status": "error", "message": "Tidak ada file yang dipilih"}, 400

    file = request.files['foto']
    if file.filename == '':
        return {"status": "error", "message": "Tidak ada file yang dipilih"}, 400

    filename = secure_filename(file.filename)
    file.save(os.path.join(UPLOAD_FOLDER_PHOTOS, filename))

    photo_data = {
        "judul": judul,
        "deskripsi": deskripsi,
        "filename": filename,
        "tanggal": datetime.datetime.now()
    }

    db.photos.insert_one(photo_data)
    return {"status": "success", "message": "Foto berhasil ditambahkan"}, 200

@app.route('/admin/kelola-foto/edit/<photo_id>', methods=['POST'])
def edit_foto(photo_id):
    if not session.get('user_id'):
        return {"status": "error", "message": "Unauthorized"}, 401

    try:
        photo = db.photos.find_one({"_id": ObjectId(photo_id)})
        if not photo:
            return {"status": "error", "message": "Foto tidak ditemukan"}, 404

        update_data = {
            "judul": request.form.get('judul'),
            "deskripsi": request.form.get('deskripsi')
        }

        # Jika ada file foto baru
        if 'foto' in request.files and request.files['foto'].filename != '':
            file = request.files['foto']
            filename = secure_filename(file.filename)
            file.save(os.path.join(UPLOAD_FOLDER_PHOTOS, filename))
            update_data["filename"] = filename

        db.photos.update_one(
            {"_id": ObjectId(photo_id)},
            {"$set": update_data}
        )

        return {"status": "success", "message": "Foto berhasil diperbarui"}, 200

    except Exception as e:
        return {"status": "error", "message": str(e)}, 500

@app.route('/admin/kelola-foto/hapus/<photo_id>', methods=['DELETE'])
def hapus_foto(photo_id):
    if not session.get('user_id'):
        return {"status": "error", "message": "Unauthorized"}, 401

    try:
        photo = db.photos.find_one({"_id": ObjectId(photo_id)})
        if not photo:
            return {"status": "error", "message": "Foto tidak ditemukan"}, 404

        # Hapus file dari server
        file_path = os.path.join(UPLOAD_FOLDER_PHOTOS, photo['filename'])
        if os.path.exists(file_path):
            os.remove(file_path)

        db.photos.delete_one({"_id": ObjectId(photo_id)})
        return {"status": "success", "message": "Foto berhasil dihapus"}, 200

    except Exception as e:
        return {"status": "error", "message": str(e)}, 500

@app.route('/admin/kelola-tenaga-didik')
def kelola_tenaga_didik():
    if not session.get('user_id'):
        return {"status": "error", "message": "Unauthorized"}, 401

    teachers = list(db.teachers.find().sort("nama", 1))
    return render_template("pages/admin/kelola_tenaga_didik.html", teachers=teachers)

@app.route('/admin/kelola-tenaga-didik/tambah', methods=['POST'])
def tambah_tenaga_didik():
    if not session.get('user_id'):
        return {"status": "error", "message": "Unauthorized"}, 401

    nama = request.form.get('nama')
    jabatan = request.form.get('jabatan')
    file = request.files.get('foto')

    # Cek apakah file foto ada
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER_TEACHERS'], filename))  # Pastikan ini mengarah ke folder teachers

        # Simpan data tenaga didik ke database
        db.teachers.insert_one({
            "nama": nama,
            "jabatan": jabatan,
            "foto": filename,
            "tanggal": datetime.datetime.now()
        })

        return {"status": "success", "message": "Tenaga didik berhasil ditambahkan"}, 200
    else:
        return {"status": "error", "message": "File tidak valid"}, 400
    db.teachers.insert_one(teacher_data)
    return {"status": "success", "message": "Tenaga didik berhasil ditambahkan"}, 200

@app.route('/admin/kelola-tenaga-didik/edit/<teacher_id>', methods=['POST'])
def edit_tenaga_didik(teacher_id):
    if not session.get('user_id'):
        return {"status": "error", "message": "Unauthorized"}, 401

    try:
        teacher = db.teachers.find_one({"_id": ObjectId(teacher_id)})
        if not teacher:
            return {"status": "error", "message": "Tenaga didik tidak ditemukan"}, 404

        update_data = {
            "nama": request.form.get('nama'),
            "jabatan": request.form.get('jabatan')
        }

        # Jika ada file foto baru
        if 'foto' in request.files and request.files['foto'].filename != '':
            file = request.files['foto']
            filename = secure_filename(file.filename)
            file.save(os.path.join(UPLOAD_FOLDER, filename))
            update_data["foto"] = filename

        db.teachers.update_one(
            {"_id": ObjectId(teacher_id)},
            {"$set": update_data}
        )

        return {"status": "success", "message": "Tenaga didik berhasil diperbarui"}, 200

    except Exception as e:
        return {"status": "error", "message": str(e)}, 500

@app.route('/admin/kelola-tenaga-didik/hapus/<teacher_id>', methods=['DELETE'])
def hapus_tenaga_didik(teacher_id):
    if not session.get('user_id'):
        return {"status": "error", "message": "Unauthorized"}, 401

    try:
        teacher = db.teachers.find_one({"_id": ObjectId(teacher_id)})
        if not teacher:
            return {"status": "error", "message": "Tenaga didik tidak ditemukan"}, 404

        # Hapus file dari server
        file_path = os.path.join(UPLOAD_FOLDER, teacher['foto'])
        if os.path.exists(file_path):
            os.remove(file_path)

        db.teachers.delete_one({"_id": ObjectId(teacher_id)})
        return {"status": "success", "message": "Tenaga didik berhasil dihapus"}, 200

    except Exception as e:
        return {"status": "error", "message": str(e)}, 500

@app.route('/berita', methods=['GET', 'POST'])
def berita():
    query = request.args.get('query')  # Ambil query pencarian dari URL
    if query:
        # Cari berita berdasarkan judul atau deskripsi
        berita_list = list(db.berita.find({
            "$or": [
                {"judul": {"$regex": query, "$options": "i"}},  # Pencarian tidak case-sensitive
                {"deskripsi": {"$regex": query, "$options": "i"}}
            ]
        }))
    else:
        # Ambil semua berita jika tidak ada query
        berita_list = list(db.berita.find().sort("tanggal", -1))

    return render_template('pages/berita.html', berita=berita_list)

@app.route('/berita/<id>/<slug>')
def detail_berita(id, slug):
    berita = db.berita.find_one({"_id": ObjectId(id)})
    if berita:
        # Verify that the slug matches
        correct_slug = slugify(berita['judul'])
        if slug != correct_slug:
            # Redirect to the correct URL if slug doesn't match
            return redirect(url_for('detail_berita', id=id, slug=correct_slug))
        return render_template('pages/detail_berita.html', berita=berita)
    else:
        return "Berita tidak ditemukan", 404

@app.route('/foto-kegiatan')
def foto_kegiatan():
    # Ambil semua foto dari database
    photos = list(db.photos.find().sort("tanggal", -1))  # Mengambil semua foto, diurutkan berdasarkan tanggal
    return render_template('pages/foto_kegiatan.html', photos=photos)

@app.route('/video-kegiatan')
def video_kegiatan():
    # Ambil semua video dari database
    videos = list(db.videos.find().sort("tanggal", -1))  # Mengambil semua video, diurutkan berdasarkan tanggal
    print(videos)
    return render_template('pages/video_kegiatan.html', videos=videos)

@app.route('/teachers')
def teachers():
    # Ambil semua data guru dari database
    semua_teachers = list(db.teachers.find().sort("nama", 1))  # Mengambil semua guru, diurutkan berdasarkan nama
    return render_template('pages/teachers.html', teachers=semua_teachers)

# Route untuk kelola donasi
@app.route('/admin/kelola-donasi')
def kelola_donasi():
    if not session.get('user_id'):
        flash("Anda harus login terlebih dahulu!", "danger")
        return redirect(url_for("login"))
    
    donations = list(db.donasi.find().sort("tanggal", -1))
    return render_template("pages/admin/kelola_donasi.html", donations=donations)

# Route untuk tambah donasi
@app.route('/admin/kelola-donasi/tambah', methods=['POST'])
def tambah_donasi():
    if not session.get('user_id'):
        return {"status": "error", "message": "Unauthorized"}, 401

    nama_penyumbang = request.form.get('nama_penyumbang')
    jumlah_sumbangan = request.form.get('jumlah_sumbangan')
    tujuan_sumbangan = request.form.get('tujuan_sumbangan')  # Ambil tujuan sumbangan

    # Data donasi
    donasi_data = {
        "nama_penyumbang": nama_penyumbang,
        "jumlah_sumbangan": float(jumlah_sumbangan),
        "tujuan_sumbangan": tujuan_sumbangan,  # Simpan tujuan sumbangan
        "tanggal": datetime.datetime.now()
    }

    # Simpan ke database
    db.donasi.insert_one(donasi_data)
    
    return {"status": "success", "message": "Donasi berhasil ditambahkan"}, 200
# Route untuk edit donasi
@app.route('/admin/kelola-donasi/edit/<donation_id>', methods=['POST'])
def edit_donasi(donation_id):
    if not session.get('user_id'):
        return {"status": "error", "message": "Unauthorized"}, 401

    donation = db.donasi.find_one({"_id": ObjectId(donation_id)})
    if not donation:
        return {"status": "error", "message": "Donasi tidak ditemukan"}, 404

    update_data = {
        "nama_penyumbang": request.form.get('nama_penyumbang'),
        "jumlah_sumbangan": float(request.form.get('jumlah_sumbangan')),
        "tujuan_sumbangan": request.form.get('tujuan_sumbangan')  # Update tujuan sumbangan
    }

    db.donasi.update_one(
        {"_id": ObjectId(donation_id)},
        {"$set": update_data}
    )

    return {"status": "success", "message": "Donasi berhasil diperbarui"}, 200

# Route untuk hapus donasi
@app.route('/admin/kelola-donasi/hapus/<donation_id>', methods=['DELETE'])
def hapus_donasi(donation_id):
    if not session.get('user_id'):
        return {"status": "error", "message": "Unauthorized"}, 401

    donation = db.donasi.find_one({"_id": ObjectId(donation_id)})
    if not donation:
        return {"status": "error", "message": "Donasi tidak ditemukan"}, 404

    db.donasi.delete_one({"_id": ObjectId(donation_id)})
    return {"status": "success", "message": "Donasi berhasil dihapus"}, 200

if __name__ == "__main__":
    app.run('0.0.0.0', port=5000, debug=True)
