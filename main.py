import os
import requests
import feedparser
from email.mime.text import MIMEText
import smtplib
from flask import Flask, request, jsonify

app = Flask(__name__)

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
EMAIL_USER = os.environ.get("EMAIL_USER")
EMAIL_PW = os.environ.get("EMAIL_PW")


def fetch_rss():
    feeds = [
        "https://www.zdnet.co.kr/news/news_xml.asp?ct=0000",
        "https://rss.etnews.com/Section902.xml"
    ]
    items = []

    try:
        for f in feeds:
            parsed = feedparser.parse(f)
            if not hasattr(parsed, "entries"):
                print("RSS 구조 오류:", f)
                continue
            for e in parsed.entries[:5]:
                items.append({"title": e.title, "link": e.link})
    except Exception as e:
        print("RSS Fetch Error:", e)

    return items


def summarize_with_gpt(text):
    url = "https://api.openai.com/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }

    prompt = f"""
다음 IT 뉴스들을 5줄로 요약하고 키워드 5개 뽑아줘:

{text}
"""

    data = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3
    }

    try:
        res = requests.post(url, headers=headers, json=data, timeout=20)
        res.raise_for_status()

        j = res.json()
        if "choices" not in j:
            print("GPT 응답 구조 오류:", j)
            return "GPT 응답 오류로 요약 생성에 실패했습니다."

        return j["choices"][0]["message"]["content"]

    except Exception as e:
        print("GPT Error:", e)
        return "GPT 호출 실패로 오늘 뉴스 요약을 생성하지 못했습니다."


def send_email(summary):
    msg = MIMEText(summary.replace("\n", "<br>"), "html")
    msg["Subject"] = "Daily IT Trend"
    msg["From"] = EMAIL_USER
    msg["To"] = EMAIL_USER

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587, timeout=10)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PW)
        server.sendmail(EMAIL_USER, EMAIL_USER, msg.as_string())
        server.quit()
    except Exception as e:
        print("Email send error:", e)


# --------------------------
# Cloud Run 엔드포인트
# --------------------------
@app.route("/", methods=["GET"])
def hello_http():
    rss_items = fetch_rss()

    text = "\n".join([f"{i['title']} ({i['link']})" for i in rss_items])

    summary = summarize_with_gpt(text)
    send_email(summary)

    return jsonify({"status": "ok", "summary": summary})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
