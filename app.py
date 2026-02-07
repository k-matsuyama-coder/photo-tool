from flask import Flask, render_template, request
import smtplib
from email.message import EmailMessage
import os

app = Flask(__name__)

# ===== 設定 =====
FROM_EMAIL = "k-matsuyama@a-z-biz.com"
FROM_PASSWORD = "csiv fnjj rymp mawh"  # ※ 本番では環境変数推奨
TO_EMAIL = "k-matsuyama@a-z-biz.com"
# =================

@app.route("/", methods=["GET", "POST"])
def upload():
    if request.method == "POST":
        photos = request.files.getlist("photos")

        # 写真が1枚も選ばれていない場合
        if not photos or photos[0].filename == "":
            return "写真が選ばれていません"

        # メール作成
        msg = EmailMessage()
        msg["Subject"] = "写真送付テスト"
        msg["From"] = FROM_EMAIL
        msg["To"] = TO_EMAIL
        msg.set_content(f"{len(photos)} 枚の写真を送ります。")

        # 複数写真を添付
        for photo in photos:
            photo.stream.seek(0)
            msg.add_attachment(
                photo.read(),
                maintype="image",
                subtype="jpeg",
                filename=photo.filename
            )

        # Gmail送信
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(FROM_EMAIL, FROM_PASSWORD)
            smtp.send_message(msg)

        return "メール送信完了！"

    return render_template("index.html")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
