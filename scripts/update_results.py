import requests

# ── 比賽日期（ESPN 用美國東部時間，台灣 4/26 = 美國 4/25）──
GAME_DATE = "20260425"
ESPN_URL = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={GAME_DATE}"

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

def parse_event(event):
    """回傳 (winner, score_a, score_b) 或 (None, None, None)"""
    if event["status"]["type"]["name"] != "STATUS_FINAL":
        return None, None, None
    comps = event["competitions"][0]["competitors"]
    away = next((c for c in comps if c["homeAway"] == "away"), comps[0])
    home = next((c for c in comps if c["homeAway"] == "home"), comps[1])
    winner_name = None
    for c in comps:
        if c.get("winner"):
            winner_name = TEAM_MAP.get(c["team"]["displayName"])
    return winner_name, away.get("score", ""), home.get("score", "")

def main():
    data = requests.get(ESPN_URL, timeout=10).json()

    results  = {i: None for i in range(4)}
    scores_a = {i: None for i in range(4)}  # teamA 比分（MATCHES 中的 a）
    scores_b = {i: None for i in range(4)}  # teamB 比分

    for event in data.get("events", []):
        comps = event["competitions"][0]["competitors"]
        away = next((c for c in comps if c["homeAway"] == "away"), comps[0])
        home = next((c for c in comps if c["homeAway"] == "home"), comps[1])
        away_zh = TEAM_MAP.get(away["team"]["displayName"])
        home_zh = TEAM_MAP.get(home["team"]["displayName"])
        team_names = {away_zh, home_zh}

        for mid, (a, b) in MATCHES.items():
            if team_names == {a, b}:
                winner, away_score, home_score = parse_event(event)
                if winner:
                    results[mid] = winner
                    # a 是 MATCHES 定義的左隊，判斷它是 away 還是 home
                    if away_zh == a:
                        scores_a[mid], scores_b[mid] = away_score, home_score
                    else:
                        scores_a[mid], scores_b[mid] = home_score, away_score
                break

    print("📊 賽果:", results)
    print("📊 比分A:", scores_a)
    print("📊 比分B:", scores_b)

    fields = {}
    for i in range(4):
        fields[f"r{i}"] = {"stringValue": results[i]}  if results[i]  else {"nullValue": None}
        fields[f"a{i}"] = {"stringValue": scores_a[i]} if scores_a[i] else {"nullValue": None}
        fields[f"b{i}"] = {"stringValue": scores_b[i]} if scores_b[i] else {"nullValue": None}

    field_names = [f"r{i}" for i in range(4)] + [f"a{i}" for i in range(4)] + [f"b{i}" for i in range(4)]
    mask = "&".join(f"updateMask.fieldPaths={f}" for f in field_names)
    r = requests.patch(f"{FIRESTORE_URL}?{mask}", json={"fields": fields}, timeout=10)
    print("✅ 成功" if r.status_code == 200 else f"❌ {r.status_code}: {r.text}")

if __name__ == "__main__":
    main()
