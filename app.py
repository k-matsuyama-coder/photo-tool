from flask import Flask, render_template, request
import os
import io
import json
from datetime import datetime
from werkzeug.utils import secure_filename

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

app = Flask(__name__)

# フォームの name と、ファイル名に入れるカテゴリ名
PHOTO_FIELDS = [
    ("out_photos", "01_front"),      # 正面
    ("in_photos", "02_back"),        # 背面
    ("eq_photos", "03_right"),       # 右側面
    ("etc_photos", "04_left"),       # 左側面
    ("damage_photos", "05_damage"),  # 傷（任意）
]

SCOPES = ["https://www.googleapis.com/auth/drive.file"]


def get_drive_service():
    info = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"])
    creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    return build("drive", "v3", credentials=creds)


def make_drive_filename(work_date: str, project: str, label: str, original_name: str) -> str:
    """
    例: 2026-02-08_竹中_広町_01_front_154233_123456_sample.jpg
    """
    safe_original = secure_filename(original_name) or "photo.jpg"

    # 現場名は日本語OK。ただし / \ は危ないので置換
    project_clean = (project or "no_project").strip().replace("/", "_").replace("\\", "_")

    # 同名衝突防止のため時刻＋マイクロ秒
    ts = datetime.now().strftime("%H%M%S_%f")

    return f"{work_date}_{project_clean}_{label}_{ts}_{safe_original}"


def get_or_create_subfolder(service, parent_folder_id: str, folder_name: str) -> str:
    """
    parent_folder_id の直下に folder_name のフォルダがあればそのIDを返す。なければ作る。
    """
    # フォルダ検索（同名複数なら先頭）
    q = (
        f"'{parent_folder_id}' in parents and "
        f"name = '{folder_name}' and "
        f"mimeType = 'application/vnd.google-apps.folder' and "
        f"trashed = false"
    )

    res = service.files().list(
        q=q,
        fields="files(id, name)",
        pageSize=1,
        supportsAllDrives=True,
        includeItemsFromAllDrives=True,
    ).execute()

    files = res.get("files", [])
    if files:
        return files[0]["id"]

    # なければ作成
    meta = {
        "name": folder_name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_folder_id],
    }

    created = service.files().create(
        body=meta,
        fields="id",
        supportsAllDrives=True,
    ).execute()

    return created["id"]


def upload_file_to_drive(service, folder_id: str, file_storage, filename: str) -> str:
    stream = io.BytesIO(file_storage.read())
    stream.seek(0)

    media = MediaIoBaseUpload(
        stream,
        mimetype=file_storage.mimetype,
        resumable=False
    )

    meta = {"name": filename, "parents": [folder_id]}

    created = service.files().create(
        body=meta,
        media_body=media,
        fields="id",
        supportsAllDrives=True,
    ).execute()

    return created["id"]


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        project = (request.form.get("project") or "").strip()
        work_date = (request.form.get("work_date") or "").strip()

        # 入力チェック
        if not project:
            return render_template("index.html", project=project, work_date=work_date, message="現場名を入力してください")
        if not work_date:
            return render_template("index.html", project=project, work_date=work_date, message="日付を入力してください")

        try:
            # ========= デバッグ（必要なくなったら消してOK） =========
            print("FILES:", list(request.files.keys()))
            for k in ["out_photos", "in_photos", "eq_photos", "etc_photos", "damage_photos"]:
                print(k, "=", len(request.files.getlist(k)))
            # ======================================================

            # Drive準備
            root_folder_id = os.environ["DRIVE_FOLDER_ID"]
            service = get_drive_service()

            # 送信ごとにサブフォルダ（日付_現場名）を作る/取得する
            project_safe = project.replace("/", "_").replace("\\", "_")
            subfolder_name = f"{work_date}_{project_safe}"[:80]
            folder_id = get_or_create_subfolder(service, root_folder_id, subfolder_name)

            uploaded_count = 0

            # 全カテゴリを順番に処理
            for field_name, label in PHOTO_FIELDS:
                for f in request.files.getlist(field_name):
                    if not f or not f.filename:
                        continue

                    new_name = make_drive_filename(work_date, project, label, f.filename)
                    upload_file_to_drive(service, folder_id, f, new_name)
                    uploaded_count += 1

            if uploaded_count == 0:
                return render_template("index.html", project=project, work_date=work_date, message="写真が選ばれていません")

            return render_template(
                "index.html",
                project=project,
                work_date=work_date,
                message=f"✅ {uploaded_count} 枚の写真を保存しました（{subfolder_name}）"
            )

        except Exception as e:
            # RenderのLogsに詳細が出る
            print("UPLOAD ERROR:", repr(e))
            return render_template(
                "index.html",
                project=project,
                work_date=work_date,
                message="⚠️ 保存中にエラーが発生しました（管理者に連絡してください）"
            )

    # GET（初回表示）
    return render_template("index.html", project="", work_date="", message="")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
