from flask import Flask, render_template, request
import smtplib
from email.message import EmailMessage

app = Flask(__name__)

# ===== 設定 =====
FROM_EMAIL = "k-matsuyama@a-z-biz.com"
FROM_PASSWORD = "csiv fnjj rymp mawh"
TO_EMAIL = "k-matsuyama@a-z-biz.com"
# =================

@app.route("/", methods=["GET", "POST"])
def upload():
    if request.method == "POST":
        photo = request.files["photo"]

        if photo.filename == "":
            return "写真が選ばれていません"

        # 一時保存
        file_path = "sample.jpg"
        photo.save(file_path)

        # メール作成
        msg = EmailMessage()
        msg["Subject"] = "写真送付テスト"
        msg["From"] = FROM_EMAIL
        msg["To"] = TO_EMAIL
        msg.set_content("写真を送ります。")

        # 写真を添付
        with open(file_path, "rb") as f:
            msg.add_attachment(
                f.read(),
                maintype="image",
                subtype="jpeg",
                filename="photo.jpg"
            )

        # Gmail送信
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(FROM_EMAIL, FROM_PASSWORD)
            smtp.send_message(msg)

        return "メール送信完了！"

    return render_template("index.html")

import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
