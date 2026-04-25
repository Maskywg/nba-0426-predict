import requests
import json

# ── 比賽日期（ESPN 用美國東部時間，台灣 4/26 = 美國 4/25）──
GAME_DATE = "20260425"

ESPN_URL = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={GAME_DATE}"

# ESPN 英文隊名 → 中文
TEAM_MAP = {
    "Orlando Magic":          "魔術",
    "Detroit Pistons":        "活塞",
    "Phoenix Suns":           "太陽",
    "Oklahoma City Thunder":  "雷霆",
    "Atlanta Hawks":          "老鷹",
    "New York Knicks":        "尼克",
    "Minnesota Timberwolves": "灰狼",
    "Denver Nuggets":         "金塊",
}

# match_id → (隊A, 隊B)
MATCHES = {
    0: ("魔術", "活塞"),
    1: ("太陽", "雷霆"),
    2: ("老鷹", "尼克"),
    3: ("灰狼", "金塊"),
}

FIRESTORE_URL = (
    "https://firestore.googleapis.com/v1/projects/"
    "gen-lang-client-0737444461/databases/(default)/"
    "documents/game_results/nba_0426"
)

def get_winner(event):
    status = event["status"]["type"]["name"]
    if status != "STATUS_FINAL":
        return None
    for comp in event["competitions"][0]["competitors"]:
        if comp.get("winner", False):
            return TEAM_MAP.get(comp["team"]["displayName"])
    return None

def main():
    resp = requests.get(ESPN_URL, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    results = {i: None for i in range(4)}

    for event in data.get("events", []):
        competitors = event["competitions"][0]["competitors"]
        team_names = {
            TEAM_MAP.get(c["team"]["displayName"])
            for c in competitors
        }
        for match_id, (a, b) in MATCHES.items():
            if team_names == {a, b}:
                winner = get_winner(event)
                if winner:
                    results[match_id] = winner
                break

    print("📊 目前賽果:", results)

    # 寫入 Firestore（只更新有結果的欄位）
    fields = {}
    for i, winner in results.items():
        if winner:
            fields[f"r{i}"] = {"stringValue": winner}
        else:
            fields[f"r{i}"] = {"nullValue": None}

    mask = "&".join(f"updateMask.fieldPaths=r{i}" for i in range(4))
    patch_url = f"{FIRESTORE_URL}?{mask}"

    r = requests.patch(patch_url, json={"fields": fields}, timeout=10)
    if r.status_code == 200:
        print("✅ Firestore 更新成功")
    else:
        print(f"❌ Firestore 錯誤 {r.status_code}: {r.text}")

if __name__ == "__main__":
    main()
