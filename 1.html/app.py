import os
import sqlite3
import threading
import uuid
from datetime import datetime
from flask import Flask, flash, redirect, render_template, request, session
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.secret_key = "ust_duzey_guvenli_ve_gizli_anahtar_metni"

DB_NAME = "veritabanı.db"
SQL_LOG_FILE = "veri.sql"


def veritabanini_kur():
    """Veritabanını status sütunu dahil olacak şekilde hazırlar."""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS kullanicilar (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                isim TEXT NOT NULL,
                sifre TEXT NOT NULL,
                yedek_sifre TEXT NOT NULL,
                ana_kimlik TEXT NOT NULL,
                yedek_kimlik TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'banlanma yok'
            )
        """
        )
        conn.commit()


def sql_dosyasina_yaz(isim, guvenli_sifre, guvenli_yedek_sifre, ana_kimlik, yedek_kimlik, durum):
    """Zaman damgalı loglama sistemine status (durum) bilgisini de ekler."""
    su_an = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_metni = (
        f"-- KAYIT TARİHİ: {su_an} --\n"
        f"INSERT INTO kullanicilar (isim, sifre, yedek_sifre, ana_kimlik, yedek_kimlik, status)\n"
        f"VALUES ('{isim}', '{guvenli_sifre[:15]}...', '{guvenli_yedek_sifre[:15]}...', '{ana_kimlik}', '{yedek_kimlik}', '{durum}');\n"
        f"{'-'*60}\n"
    )
    with open(SQL_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_metni)


def veritabani_sifirla():
    """Tüm kullanıcı verilerini temizler."""
    if os.path.exists(DB_NAME):
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM kullanicilar")
            conn.commit()
        print("\n🔥 [SİSTEM MÜDAHALESİ] Tüm kullanıcı bilgileri başarıyla silindi!")
    else:
        print("\n❌ [SİSTEM] Veritabanı bulunamadı.")


def kullanici_banla(kimlik):
    """Ana veya yedek kimliğe göre kullanıcıyı banlar."""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE kullanicilar SET status = 'banned' WHERE ana_kimlik = ? OR yedek_kimlik = ?",
            (kimlik, kimlik)
        )
        conn.commit()
        if cursor.rowcount > 0:
            print(f"\n🚫 [SİSTEM] {kimlik} kimlikli kullanıcı başarıyla BANLANDI (status=banned).")
        else:
            print(f"\n❌ [SİSTEM] {kimlik} kimliğine sahip bir kullanıcı bulunamadı.")


def kullanici_ban_kaldir(kimlik):
    """Ana veya yedek kimliğe göre kullanıcının banını kaldırır."""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE kullanicilar SET status = 'banlanma yok' WHERE ana_kimlik = ? OR yedek_kimlik = ?",
            (kimlik, kimlik)
        )
        conn.commit()
        if cursor.rowcount > 0:
            print(f"\n✅ [SİSTEM] {kimlik} kimlikli kullanıcının banı kaldırıldı (status=banlanma yok).")
        else:
            print(f"\n❌ [SİSTEM] {kimlik} kimliğine sahip bir kullanıcı bulunamadı.")


def terminal_dinleyici():
    """Arka planda komutları dinler ve analiz eder."""
    print("[SİSTEM] Admin Komut Masası Aktif.")
    print("-> Sıfırlamak için: boot/yes")
    print("-> Banlamak için: KİMLİK/ban")
    print("-> Ban kaldırmak için: KİMLİK/unban\n")
    
    while True:
        try:
            komut = input().strip()
            if not komut:
                continue
                
            if komut == "boot/yes":
                veritabani_sifirla()
            elif komut.endswith("/ban"):
                kimlik = komut.split("/ban")[0].strip().upper()
                kullanici_banla(kimlik)
            elif komut.endswith("/unban"):
                kimlik = komut.split("/unban")[0].strip().upper()
                kullanici_ban_kaldir(kimlik)
            else:
                print("❌ Bilinmeyen admin komutu.")
        except (KeyboardInterrupt, EOFError):
            break


@app.route("/")
def ana_sayfa():
    return redirect("/giris")


@app.route("/kayit", methods=["GET", "POST"])
def kayit():
    if request.method == "POST":
        isim = request.form.get("isim", "").strip()
        sifre = request.form.get("sifre", "")
        yedek_sifre = request.form.get("yedek_sifre", "")

        if not isim or not sifre:
            flash("Kullanıcı adı ve şifre alanları boş bırakılamaz!", "error")
            return redirect("/kayit")

        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM kullanicilar WHERE isim = ?", (isim,))
            if cursor.fetchone():
                flash("Bu kullanıcı adı zaten alınmış!", "error")
                return redirect("/kayit")

            guvenli_sifre = generate_password_hash(sifre)
            guvenli_yedek_sifre = generate_password_hash(yedek_sifre)
            ana_kimlik = str(uuid.uuid4())[:8].upper()
            yedek_kimlik = str(uuid.uuid4())[:8].upper()
            varsayilan_durum = "banlanma yok"

            cursor.execute(
                """
                INSERT INTO kullanicilar (isim, sifre, yedek_sifre, ana_kimlik, yedek_kimlik, status)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (isim, guvenli_sifre, guvenli_yedek_sifre, ana_kimlik, yedek_kimlik, varsayilan_durum),
            )
            conn.commit()

        sql_dosyasina_yaz(isim, guvenli_sifre, guvenli_yedek_sifre, ana_kimlik, yedek_kimlik, varsayilan_durum)
        flash("Hesabınız başarıyla oluşturuldu! Giriş yapabilirsiniz.", "success")
        return redirect("/giris")

    return render_template("kayit.html")


@app.route("/giris", methods=["GET", "POST"])
def giris():
    if request.method == "POST":
        isim = request.form.get("isim", "").strip()
        girilen_sifre = request.form.get("sifre", "")

        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT isim, sifre, ana_kimlik, yedek_kimlik, status FROM kullanicilar WHERE isim = ?",
                (isim,),
            )
            kullanici = cursor.fetchone()

        if kullanici:
            # 🚫 KESİN BAN KONTROLÜ: Eğer kullanıcı banned ise şifre ne olursa olsun giremez
            if kullanici[4] == "banned":
                flash("Bu hesap banlı!", "error")
                return redirect("/giris")
            
            # Şifre Doğrulma Adımı
            if check_password_hash(kullanici[1], girilen_sifre):
                # Giriş yapan kullanıcının statüsünü aktife çekiyoruz
                with sqlite3.connect(DB_NAME) as conn:
                    cursor = conn.cursor()
                    cursor.execute("UPDATE kullanicilar SET status = 'banlanma yok' WHERE isim = ?", (isim,))
                    conn.commit()

                session["kullanici_adi"] = kullanici[0]
                session["ana_kimlik"] = kullanici[2]
                session["yedek_kimlik"] = kullanici[3]
                return redirect("/profil")
            else:
                flash("Hatalı kullanıcı adı veya şifre girdiniz!", "error")
                return redirect("/giris")
        else:
            flash("Hatalı kullanıcı adı veya şifre girdiniz!", "error")
            return redirect("/giris")

    return render_template("giris.html")


@app.route("/profil")
def profil():
    if "kullanici_adi" not in session:
        flash("Lütfen önce sisteme giriş yapın.", "error")
        return redirect("/giris")

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM kullanicilar WHERE isim = ?", (session["kullanici_adi"],))
        durum = cursor.fetchone()
        
    if durum and durum[0] == "banned":
        session.clear()
        flash("Bu hesap banlı!", "error")
        return redirect("/giris")

    return render_template(
        "profil.html",
        isim=session["kullanici_adi"],
        ana_kimlik=session["ana_kimlik"],
        yedek_kimlik=session["yedek_kimlik"],
    )


@app.route("/cikis")
def cikis():
    if "kullanici_adi" in session:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE kullanicilar SET status = 'oturumu_kapalı' WHERE isim = ?",
                (session["kullanici_adi"],)
            )
            conn.commit()
            
    session.clear()
    flash("Güvenli bir şekilde çıkış yaptınız. Durum: Oturumu Kapalı", "success")
    return redirect("/giris")


if __name__ == "__main__":
    veritabanini_kur()
    
    t = threading.Thread(target=terminal_dinleyici, daemon=True)
    t.start()
    
    # Render.com portu otomatik atar, eğer bulamazsa varsayılan olarak 8080 kullanır
    port = int(os.environ.get("PORT", 8080))
    print(f"\n[BEYİN] Uygulama Port {port} üzerinde internete açılıyor...")
    
    # host="0.0.0.0" yapmalıyız ki dış dünyadan gelen isteklere yanıt verebilsin
    app.run(host="0.0.0.0", port=port, debug=False)