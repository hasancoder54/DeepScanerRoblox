import urllib.request
import urllib.error
import json
import ssl
import time
from datetime import datetime, timezone
from flask import Flask, request, jsonify, send_from_directory, Response

app = Flask(__name__, static_folder='.')

class RobloxAPI:
    def __init__(self, auth_cookie="", proxy_url=""):
        # RoProxy uç noktaları ve gelişmiş OSINT servisleri
        self.users_api = "https://users.roproxy.com/v1"
        self.avatar_api = "https://avatar.roproxy.com/v1"
        self.groups_api = "https://groups.roproxy.com/v1"
        self.games_api = "https://games.roproxy.com"
        self.friends_api = "https://friends.roproxy.com/v1"
        self.badges_api = "https://badges.roproxy.com/v1"
        self.presence_api = "https://presence.roproxy.com/v1"
        self.thumbnails_api = "https://thumbnails.roproxy.com/v1"
        self.account_api = "https://accountinformation.roproxy.com/v1"
        self.inventory_api = "https://inventory.roproxy.com/v1"
        self.economy_api = "https://economy.roproxy.com/v1"
        self.premium_api = "https://premium.roproxy.com/v1"
        
        self.auth_cookie = auth_cookie
        self.proxy_url = proxy_url

    def _fetch_json(self, url, payload=None, headers=None, method='GET', ignore_errors=False, retries=2):
        if headers is None:
            headers = {}
            
        headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        headers["Accept"] = "application/json, text/plain, */*"
        headers["Accept-Language"] = "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7"
        headers["Origin"] = "https://www.roblox.com"
        headers["Referer"] = "https://www.roblox.com/"

        if self.auth_cookie:
            headers["Cookie"] = f".ROBLOSECURITY={self.auth_cookie}"
        
        data = None
        if payload is not None:
            data = json.dumps(payload).encode('utf-8')
            headers["Content-Type"] = "application/json"

        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        
        handlers = [urllib.request.HTTPSHandler(context=context)]
        
        if self.proxy_url:
            handlers.append(urllib.request.ProxyHandler({
                'http': self.proxy_url,
                'https': self.proxy_url
            }))

        opener = urllib.request.build_opener(*handlers)
        time.sleep(0.2)

        for attempt in range(retries + 1):
            try:
                with opener.open(req, timeout=15) as response:
                    return json.loads(response.read().decode('utf-8'))
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    if attempt < retries:
                        wait_time = (attempt + 1) * 2
                        time.sleep(wait_time)
                        continue
                if not ignore_errors:
                    print(f"[!] HTTP Hatası [{e.code}] -> URL: {url}")
                return None
            except Exception as e:
                if not ignore_errors:
                    print(f"[!] Hata -> URL: {url} | Sebeb: {str(e)}")
                return None
        return None

    def get_user_by_username(self, username):
        url = f"{self.users_api}/usernames/users"
        payload = {"usernames": [username], "excludeBannedUsers": False}
        res = self._fetch_json(url, payload=payload, method='POST')
        if res and res.get("data") and len(res["data"]) > 0:
            return res["data"][0]["id"]
        return None

    def get_users_batch(self, user_ids):
        if not user_ids:
            return {}
        users_map = {}
        # 100'erli paketler halinde kullanıcı bilgilerini çek
        for i in range(0, len(user_ids), 100):
            chunk = user_ids[i:i + 100]
            url = f"{self.users_api}/users"
            payload = {"userIds": chunk, "excludeBannedUsers": False}
            res = self._fetch_json(url, payload=payload, method='POST', ignore_errors=True)
            if res and res.get("data"):
                for user in res["data"]:
                    users_map[user.get("id")] = user
        return users_map

    def get_thumbnails_batch(self, target_ids, item_type="user_headshot"):
        if not target_ids:
            return {}
        result_map = {}
        # 100'erli paketler halinde thumbnail çek
        for i in range(0, len(target_ids), 100):
            chunk = target_ids[i:i + 100]
            ids_str = ",".join(map(str, chunk))
            if item_type == "user_headshot":
                url = f"{self.thumbnails_api}/users/avatar-headshots?userIds={ids_str}&size=150x150&format=Png&isCircular=false"
            elif item_type == "user_full":
                url = f"{self.thumbnails_api}/users/avatar?userIds={ids_str}&size=720x720&format=Png&isCircular=false"
            elif item_type == "group_icon":
                url = f"{self.thumbnails_api}/groups/icons?groupIds={ids_str}&size=150x150&format=Png"
            elif item_type == "game_icon":
                url = f"{self.thumbnails_api}/games/icons?universeIds={ids_str}&size=150x150&format=Png"
            else:
                continue
            
            res = self._fetch_json(url, ignore_errors=True)
            if res and res.get("data"):
                for item in res["data"]:
                    target_key = item.get("targetId")
                    img_url = item.get("imageUrl", "")
                    if target_key:
                        result_map[target_key] = img_url
        return result_map

    def get_avatar_3d(self, user_id):
        url = f"{self.avatar_api}/users/{user_id}/avatar-3d"
        res = self._fetch_json(url, ignore_errors=True)
        if res and res.get("imageUrl"):
            return res
        return None

    def get_username_history(self, user_id):
        url = f"{self.users_api}/users/{user_id}/username-history?limit=50&sortOrder=Desc"
        res = self._fetch_json(url, ignore_errors=True)
        if res and res.get("data"):
            return [item.get("name") for item in res["data"]]
        return []

    def get_gamepasses(self, universe_id):
        url = f"{self.games_api}/v1/games/{universe_id}/game-passes?limit=50&sortOrder=Asc"
        res = self._fetch_json(url, ignore_errors=True)
        if res and res.get("data"):
            return [{"name": gp.get("name"), "price": gp.get("price", 0), "id": gp.get("id")} for gp in res["data"]]
        return []

    def get_collectibles_rap(self, user_id):
        url = f"{self.inventory_api}/users/{user_id}/assets/collectibles?assetType=All&limit=100&sortOrder=Asc"
        res = self._fetch_json(url, ignore_errors=True)
        total_rap = 0
        items = []
        if res and res.get("data"):
            for item in res["data"]:
                rap = item.get("recentAveragePrice", 0)
                total_rap += rap
                items.append({
                    "id": item.get("assetId"),
                    "name": item.get("name"),
                    "rap": rap,
                    "serial": item.get("serialNumber", "Yok"),
                    "userAssetId": item.get("userAssetId")
                })
        return {"total_rap": total_rap, "items": items, "count": len(items)}

    def get_user_outfits(self, user_id):
        url = f"{self.avatar_api}/users/{user_id}/outfits?page=1&itemsPerPage=50"
        res = self._fetch_json(url, ignore_errors=True)
        if res and res.get("data"):
            return [{"id": o.get("id"), "name": o.get("name"), "isEditable": o.get("isEditable")} for o in res["data"]]
        return []

    def get_primary_group(self, user_id):
        url = f"{self.groups_api}/users/{user_id}/primary-group"
        res = self._fetch_json(url, ignore_errors=True)
        if res and res.get("group"):
            g = res["group"]
            r = res.get("role", {})
            return {
                "id": g.get("id"),
                "name": g.get("name"),
                "role": r.get("name"),
                "rank": r.get("rank")
            }
        return None

    def calculate_account_age(self, date_string):
        if not date_string: return {"days": 0, "years": "0"}
        try:
            dt = datetime.strptime(date_string.split(".")[0], "%Y-%m-%dT%H:%M:%S")
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            days = (now - dt).days
            years = round(days / 365.25, 1)
            return {"days": days, "years": str(years)}
        except:
            return {"days": 0, "years": "0"}

    def format_date(self, date_string):
        if not date_string: return "Bilinmiyor"
        try:
            dt = datetime.strptime(date_string.split(".")[0], "%Y-%m-%dT%H:%M:%S")
            return dt.strftime("%d-%m-%Y %H:%M:%S")
        except:
            return date_string

    def presence_translator(self, p_type):
        return {0: "Çevrimdışı", 1: "Çevrimiçi", 2: "Oyunda", 3: "Stüdyoda", 4: "Görünmez"}.get(p_type, "Bilinmiyor")

    def analyze_user_to_dict(self, identifier, is_id=False):
        user_id = int(identifier) if is_id else self.get_user_by_username(identifier)
        if not user_id:
            return {"error": "Hedef kullanıcı bulunamadı veya RoProxy isteği engellendi."}

        data = {
            "id": user_id,
            "profile": {},
            "social": {},
            "groups": [],
            "primary_group": self.get_primary_group(user_id),
            "games": [],
            "favorites": [],
            "avatar": {},
            "clothing_worn": [],
            "outfits": self.get_user_outfits(user_id),
            "collectibles": self.get_collectibles_rap(user_id),
            "badges": [],
            "avatar_3d": self.get_avatar_3d(user_id),
            "external_links": {
                "rolimons": f"https://www.rolimons.com/player/{user_id}",
                "roblox": f"https://www.roblox.com/users/{user_id}/profile",
                "roblox_db": f"https://roblox.com.kg/user/{user_id}",
                "btr_profile": f"https://www.roblox.com/users/{user_id}/profile"
            }
        }

        # Profil & Varlık (Presence)
        user_info = self._fetch_json(f"{self.users_api}/users/{user_id}")
        presence_res = self._fetch_json(f"{self.presence_api}/presence/users", payload={"userIds": [user_id]}, method='POST')
        presence = presence_res["userPresences"][0] if presence_res and presence_res.get("userPresences") else {}
        past_names = self.get_username_history(user_id)

        # Görseller (Full Body + Headshot)
        headshot_map = self.get_thumbnails_batch([user_id], "user_headshot")
        full_body_map = self.get_thumbnails_batch([user_id], "user_full")

        if user_info:
            created_raw = user_info.get("created")
            age_metrics = self.calculate_account_age(created_raw)
            data["profile"] = {
                "username": user_info.get("name"),
                "displayName": user_info.get("displayName"),
                "created": self.format_date(created_raw),
                "accountAgeDays": age_metrics["days"],
                "accountAgeYears": age_metrics["years"],
                "isBanned": user_info.get("isBanned", False),
                "hasVerifiedBadge": user_info.get("hasVerifiedBadge", False),
                "description": user_info.get("description", "Açıklama Yok"),
                "presence": self.presence_translator(presence.get("userPresenceType")),
                "presenceTypeRaw": presence.get("userPresenceType", 0),
                "lastLocation": presence.get("lastLocation", "Yok"),
                "placeId": presence.get("placeId"),
                "rootPlaceId": presence.get("rootPlaceId"),
                "gameId": presence.get("gameId"),
                "pastUsernames": past_names,
                "headshot": headshot_map.get(user_id, ""),
                "fullBody": full_body_map.get(user_id, "")
            }

        # Arkadaş Bilgileri ve İsim Çözümleme
        friends = self._fetch_json(f"{self.friends_api}/users/{user_id}/friends/count", ignore_errors=True)
        followers = self._fetch_json(f"{self.friends_api}/users/{user_id}/followers/count", ignore_errors=True)
        following = self._fetch_json(f"{self.friends_api}/users/{user_id}/followings/count", ignore_errors=True)
        
        friends_list_res = self._fetch_json(f"{self.friends_api}/users/{user_id}/friends", ignore_errors=True)
        raw_friends = friends_list_res.get("data", []) if friends_list_res else []

        friend_ids = [f.get("id") for f in raw_friends if f.get("id")]
        friend_avatars = self.get_thumbnails_batch(friend_ids, "user_headshot")
        
        # Eğer arkadaş isimleri eksik gelirse toplu olarak users API'den çözümle
        friend_users_info = self.get_users_batch(friend_ids)

        friends_data = []
        for f in raw_friends:
            f_id = f.get("id")
            detailed_u = friend_users_info.get(f_id, {})
            
            name = f.get("name") or detailed_u.get("name") or f"User_{f_id}"
            display_name = f.get("displayName") or detailed_u.get("displayName") or name
            
            friends_data.append({
                "id": f_id,
                "name": name,
                "displayName": display_name,
                "isBanned": f.get("isBanned", False),
                "hasVerifiedBadge": f.get("hasVerifiedBadge", False) or detailed_u.get("hasVerifiedBadge", False),
                "headshot": friend_avatars.get(f_id, "")
            })

        data["social"] = {
            "friends_count": friends.get("count", len(friends_data)) if friends else len(friends_data),
            "followers_count": followers.get("count", 0) if followers else 0,
            "following_count": following.get("count", 0) if following else 0,
            "friends_list": friends_data
        }

        # Gruplar ve Logoları
        groups_res = self._fetch_json(f"{self.groups_api}/users/{user_id}/groups/roles")
        if groups_res and groups_res.get("data"):
            group_ids = [g.get("group", {}).get("id") for g in groups_res["data"]]
            group_icons = self.get_thumbnails_batch(group_ids, "group_icon")
            
            for g in groups_res["data"]:
                group_info = g.get("group", {})
                role_info = g.get("role", {})
                g_id = group_info.get("id")
                data["groups"].append({
                    "name": group_info.get("name"),
                    "id": g_id,
                    "memberCount": group_info.get("memberCount", 0),
                    "role": role_info.get("name"),
                    "rank": role_info.get("rank"),
                    "icon": group_icons.get(g_id, "")
                })

        # Favori Oyunlar & Detaylı Bilgileri
        fav_res = self._fetch_json(f"{self.games_api}/v2/users/{user_id}/favorite/games?limit=50", ignore_errors=True)
        if fav_res and fav_res.get("data"):
            fav_place_ids = [f.get("rootPlaceId", f.get("id")) for f in fav_res["data"] if f.get("rootPlaceId") or f.get("id")]
            
            if fav_place_ids:
                places_str = ",".join(map(str, fav_place_ids[:50]))
                places_details = self._fetch_json(f"{self.games_api}/v1/games/multiget-place-details?placeIds={places_str}", ignore_errors=True)
                
                universe_ids = []
                if places_details:
                    universe_ids = [p.get("universeId") for p in places_details if p.get("universeId")]
                
                if universe_ids:
                    uni_str = ",".join(map(str, universe_ids[:50]))
                    fav_games_details = self._fetch_json(f"{self.games_api}/v1/games?universeIds={uni_str}", ignore_errors=True)
                    fav_icons = self.get_thumbnails_batch(universe_ids, "game_icon")

                    if fav_games_details and fav_games_details.get("data"):
                        for fg in fav_games_details["data"]:
                            u_id = fg.get("id")
                            data["favorites"].append({
                                "name": fg.get("name"),
                                "universeId": u_id,
                                "rootPlaceId": fg.get("rootPlaceId"),
                                "visits": fg.get("visits", 0),
                                "playing": fg.get("playing", 0),
                                "created": self.format_date(fg.get("created")),
                                "description": fg.get("description", "Açıklama Yok"),
                                "icon": fav_icons.get(u_id, "")
                            })

        # Kullanıcının Ürettiği Oyunlar ve İstatistik Toplamı
        games_res = self._fetch_json(f"{self.games_api}/v2/users/{user_id}/games?accessFilter=Public&limit=50")
        total_place_visits = 0
        if games_res and games_res.get("data"):
            universe_ids = [game["id"] for game in games_res["data"]]
            if universe_ids:
                uni_str = ",".join(map(str, universe_ids[:50]))
                details_res = self._fetch_json(f"{self.games_api}/v1/games?universeIds={uni_str}")
                game_icons = self.get_thumbnails_batch(universe_ids, "game_icon")
                games_data = details_res.get("data", []) if details_res else games_res["data"]
                
                for g in games_data:
                    uni_id = g.get("id")
                    visits = g.get("visits", 0)
                    total_place_visits += visits
                    gamepasses = self.get_gamepasses(uni_id)
                    data["games"].append({
                        "name": g.get("name"),
                        "universeId": uni_id,
                        "visits": visits,
                        "playing": g.get("playing", 0),
                        "created": self.format_date(g.get("created")),
                        "description": g.get("description", "Açıklama Yok"),
                        "gamepasses": gamepasses,
                        "icon": game_icons.get(uni_id, "")
                    })

        data["profile"]["totalGameVisits"] = total_place_visits

        # Avatar Öğeleri & Giyilenler
        avatar_res = self._fetch_json(f"{self.avatar_api}/users/{user_id}/avatar")
        if avatar_res:
            data["avatar"]["type"] = avatar_res.get("playerAvatarType")
            data["avatar"]["scales"] = avatar_res.get("scales", {})
            data["avatar"]["bodyColors"] = avatar_res.get("bodyColors", {})
            assets = avatar_res.get("assets", [])
            data["avatar"]["assets"] = [{"name": a.get("name"), "type": a.get("assetType", {}).get("name"), "id": a.get("id")} for a in assets]
            
            clothing_types = ["Shirt", "Pants", "TShirt", "Hat", "Accessory", "ShirtAccessory", "PantsAccessory", "FaceAccessory", "NeckAccessory", "ShoulderAccessory", "FrontAccessory", "BackAccessory", "WaistAccessory"]
            data["clothing_worn"] = [{"name": a.get("name"), "id": a.get("id"), "type": a.get("assetType", {}).get("name")} for a in assets if a.get("assetType", {}).get("name") in clothing_types]

        # Rozetler
        official_badges = self._fetch_json(f"{self.account_api}/users/{user_id}/roblox-badges")
        if official_badges:
            for ob in official_badges:
                data["badges"].append({"name": ob.get("name"), "description": ob.get("description", ""), "type": "Resmi Rozet"})

        game_badges_res = self._fetch_json(f"{self.badges_api}/users/{user_id}/badges?limit=50&sortOrder=Desc", ignore_errors=True)
        if game_badges_res and game_badges_res.get("data"):
            for gb in game_badges_res["data"]:
                data["badges"].append({"name": gb.get("name"), "id": gb.get("id"), "type": "Oyun Rozeti"})

        return data

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/api/proxy-image')
def proxy_image():
    image_url = request.args.get('url', '')
    if not image_url:
        return Response("URL eksik", status=400)

    try:
        req = urllib.request.Request(
            image_url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8"
            }
        )
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        with urllib.request.urlopen(req, context=context, timeout=12) as resp:
            content_type = resp.headers.get('Content-Type', 'image/png')
            image_bytes = resp.read()
            return Response(image_bytes, mimetype=content_type)
    except Exception as e:
        return Response(f"Görsel çekilemedi: {str(e)}", status=500)

@app.route('/api/scan', methods=['POST'])
def scan_user():
    req_data = request.json or {}
    target = req_data.get('target', '').strip()
    is_id = req_data.get('is_id', False)
    cookie = req_data.get('cookie', '').strip()
    proxy = req_data.get('proxy', '').strip()

    if not target:
        return jsonify({"error": "Hedef belirtilmedi."}), 400

    api = RobloxAPI(auth_cookie=cookie, proxy_url=proxy)
    result = api.analyze_user_to_dict(target, is_id=is_id)
    return jsonify(result)

if __name__ == "__main__":
    print("="*60)
    print("[+] ULTIMATE ROBLOX OSINT SUNUCUSU V3 AKTİF")
    print("[+] Tarayıcından Aç: http://127.0.0.1:5000")
    print("="*60)
    app.run(host='127.0.0.1', port=5000, debug=False)
