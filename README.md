# Xevrion – Discord Bot

Python-pohjainen Discord-botti (Xevrion), joka tukee useaa palvelinta ja web-käyttöliittymää palvelinkohtaisten asetusten hallintaan. Vain ylläpitäjät voivat hallita asetuksia.

## Ominaisuudet

- **Monipalvelin** – sama botti usealla serverillä, kaikki asetukset palvelinkohtaisia
- **Web-dashboard** – hallitse kaikkia ominaisuuksia palvelin kerrallaan
- **Ylläpitäjä-tarkistus** – vain palvelimen Administratorit näkevät hallinnan
- **Peruskomentoja** – ping, info, tervehdys, hallinta, komennot-lista
- **Kutsulinkit** – /kutsu (Apply bot), /lähetäkutsu (yhteisön kutsu kanavalle)
- **Moderaatio** – kick, ban, mute, varoitukset, clear – roolit ja toiminnat hallitaan webistä
- **Serverilogit** – mod-toiminnot, jäsenet liittyy/poistuu, viestien poisto/muokkaus – kanava ja tyypit webistä
- **Tikettijärjestelmä** – staff-rooli, kategoria ja kanava määritellään webistä
- **Levellijärjestelmä** – taso ja XP, tasonboard – asetukset webistä
- **Minipelit** – kolikko, noppa, 8-pallo, kivi-paperi-sakset, arpa, ruletti – kytkettävissä webistä
- **FiveM-palvelimen tila** – /fivem näyttää pelaajamäärän jne., asetukset (host, port, status-kanava) webistä
- **Twitch stream -ilmoitukset** – ilmoitus kun seuraamasi streameri aloittaa striimin, streamerit ja kanava webistä
- **Kehittäjäportaali** – DEV_USER_IDS -käyttäjille: bottin tilat, konsoliloki, käynnistä/sammuta, palvelimen poisto

## Vaatimukset

- **Python 3.8+** (suositellaan 3.10 tai uudempi)
- **Paketit**:
  - discord.py >= 2.7.1
  - flask >= 3.0.0
  - requests >= 2.31.0
  - python-dotenv >= 1.0.0
  - cryptography >= 42.0.0 (botin tietojen salattu tallennus)

Vapaaehtoiset: `discord.py[speed]` nopeampaan JSON-käsittelyyn, `psutil` muistin käytön näyttämiseen kehittäjäportaalissa.

## Nopea käynnistys

### 1. Asenna riippuvuudet

```bash
pip install -r requirements.txt
```

### 2. Luo Discord-sovellus

1. Mene [Discord Developer Portal](https://discord.com/developers/applications)
2. **New Application** → anna nimi
3. Vasemmalla **Bot** → **Reset Token** → kopioi token
4. Ota käyttöön: **Message Content Intent** ja **Server Members Intent** (mod-roolit, serverilogit)
5. Vasemmalla **OAuth2** → kopioi **Client ID** ja **Client Secret**
6. **OAuth2 → Redirects** → lisää: `http://localhost/callback` (portti 80)

### 3. Kutsu botti palvelimelle

1. **OAuth2 → URL Generator**
2. Valitse scopet: `bot`, `applications.commands`
3. Valitse bot-oikeudet: `Administrator` (tai vähintään: Manage Channels, Kick/Ban Members, Moderate Members, Manage Messages)
4. Kopioi generoitu URL ja avaa selaimessa
5. Valitse palvelin ja hyväksy

### 4. Konfiguroi ympäristö

1. Kopioi `.env.example` → `.env`
2. Täytä arvot:

```env
DISCORD_TOKEN=botin_token_tähän
DISCORD_CLIENT_ID=sovelluksen_client_id
DISCORD_CLIENT_SECRET=client_secret
DISCORD_REDIRECT_URI=http://localhost/callback

# Tärkeää: Luo satunnainen avain!
FLASK_SECRET_KEY=generate_a_random_secret_key

# Kehittäjäportaali: Discord-käyttäjä-ID:t (pilkulla erotettuna)
DEV_USER_IDS=123456789012345678

# Botin tiedot (voi myös data/bot_info.txt tai salattu data/bot_info.enc)
BOT_DESCRIPTION=Monipalvelin-botti, hallinta: !hallinta
BOT_DEVELOPERS=S44Gaming
BOT_INVITE_LINK=https://discord.gg/...
BOT_APPLY_URL=
BOT_INFO_EDIT_PASSWORD=  # Muokkaussalasana kehittäjäportaalin Botin tiedot -osiolle

# Twitch stream -ilmoitukset (valinnainen)
TWITCH_CLIENT_ID=
TWITCH_CLIENT_SECRET=
```

**FLASK_SECRET_KEY**: Luo turvallinen satunnainen avain esim. komennolla:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Kopioi tulos ja käytä sitä `FLASK_SECRET_KEY`-arvona.

### 5. Käynnistä botti

Botti toimii Windowsilla, Linuxilla ja macOS:lla.

**Windows:**
```bash
python run.py
# tai kaksoisklikkaa start.bat
```

**Linux / macOS:**
```bash
python3 run.py
# tai
chmod +x start.sh && ./start.sh
```

Tämä käynnistää:
- Discord-botin (slash-komennot)
- Web-dashboardin osoitteessa: http://localhost

---

## Web-dashboard

1. Avaa http://localhost
2. **Kirjaudu Discordilla** – tarvitaan Discord-tili
3. Valitse palvelin – näkyvät vain palvelimet, joilla sinulla on **Administrator**-oikeudet
4. Hallitse asetuksia – muutokset astuvat voimaan heti

### Webissä hallittavat asetukset (palvelinkohtaisesti)

| Osa | Asetukset |
|-----|-----------|
| **Komennot** | Ping, Komennot, Info, Tervehdys, Hallinta, Kutsu, Kutsuviesti, Tiketti, Taso, Tasonboard – päälle/pois |
| **Minipelit** | Kolikko, Noppa, 8-pallo, Kivi-paperi-sakset, Arvaa luku, Arpa, Ruletti – päälle/pois |
| **FiveM** | Palvelimen osoite, portti (oletus 30120), kanava johon status voidaan lähettää |
| **Twitch** | Seuratut streamerit (käyttäjänimet), kanava johon ilmoitukset lähetetään |
| **Moderaatio** | Moderaattoriroolit, yksittäisten mod-toimintojen päälle/pois |
| **Logit** | Logikanava, lokityypit (mod-toiminnot, jäsen liittyy/poistuu, viestin poisto/muokkaus) |
| **Tervetuloa** | Päälle/pois, tervetulokanava |
| **Levellijärjestelmä** | Päälle/pois, XP-asetukset, tasoroolit, äänekäs XP |
| **Tiketit** | Staff-rooli, kategoria tiketille, kanava josta tiketti avataan |

### Kehittäjäportaali (vain DEV_USER_IDS)

Jos Discord-käyttäjä-IDsi on `.env`:ssä `DEV_USER_IDS`-listalla, näet linkin **Kehittäjäportaali**. Siellä voit:
- nähdä bottin tilat (latenssi, palvelimet, muisti, ajoaika)
- tarkastella konsolilokia
- käynnistää/sammuttaa botin tai koko sovelluksen
- poistaa bottin palvelimelta
- muokata botin tietoja (kuvaus, kehittäjät, Apply bot -linkki, yhteisön kutsu) – vaatii muokkaussalasanan

---

## Slash-komennot

### Peruskomentoja

| Komento | Kuvaus |
|---------|--------|
| `/ping` | Botin vastausaika |
| `/komennot` | Näytä kaikki komennot (päivittyy automaattisesti) |
| `/info` | Palvelimen tiedot |
| `/tervehdys` | Tervehdys |
| `/hallinta` | Linkki web-dashboardiin |
| `/kutsu` | Linkki lisätä botti omaan palvelimeen (Apply bot) |
| `/lähetäkutsu` | Lähettää yhteisön kutsulinkin kanavalle (vaatii Manage Server) |

### Moderaatiokomennot

| Komento | Kuvaus |
|---------|--------|
| `/kick` | Potkaise jäsen palvelimelta |
| `/ban` | Estä jäsen palvelimelta |
| `/mute` | Mykistä jäsen (timeout) |
| `/unmute` | Poista mykistys |
| `/varoitus` | Anna varoitus jäsenelle |
| `/varoitukset` | Näytä jäsenen varoitukset |
| `/poista_varoitukset` | Poista kaikki varoitukset jäseneltä |
| `/clear` | Poista viestejä kanavalta |

*Mod-roolit määritellään webissä. Ylläpitäjillä on aina mod-oikeudet.*

### Minipelit

| Komento | Kuvaus |
|---------|--------|
| `/kolikko` | Heitä kolikkoa (kruuna/klaava) |
| `/noppa` | Heitä noppaa (esim. 1d6, 2d20) |
| `/8ball` | Maaginen 8-pallo vastaa kysymykseesi |
| `/kps` | Kivi, paperi, sakset – pelaa bottia vastaan |
| `/arvaa_luku` | Arvaa luku 1–10 |
| `/arpa` | Arpa valitsee vaihtoehdoista (pilkulla erotettu lista) |
| `/ruletti` | Venäläinen ruletti (1/6) |

### Taso- ja levellijärjestelmä

| Komento | Kuvaus |
|---------|--------|
| `/taso` | Näytä taso ja XP |
| `/tasonboard` | TasoTOP-10 |

### FiveM

| Komento | Kuvaus |
|---------|--------|
| `/fivem` | FiveM-palvelimen tila (pelaajat, kartta). Aseta palvelin webistä. Valinnalla »Lähetä kanavalle« lähettää statusin asetettuun kanavaan. |

### Twitch stream -ilmoitukset

Botti lähettää automaattisesti viestin Discord-kanavalle, kun joku seuraamistasi Twitch-streamereistä aloittaa striimin.

**Miten Twitch-ilmoitukset saadaan toimimaan**

1. **Luo Twitch-sovellus**
   - Mene [Twitch Developer Console](https://dev.twitch.tv/console)
   - **Register Your Application** → anna nimi, käyttötarkoitus (esim. "Discord bot stream notifications")
   - Valitse **Application Category** (esim. Application Integration)
   - OAuth Redirect URL voi olla `http://localhost` (ei tarvita tähän ominaisuuteen)
   - Luo sovellus ja avaa sen asetuksista **Client ID** sekä luo **Client Secret**

2. **Lisää tunnukset .env-tiedostoon**
   ```env
   TWITCH_CLIENT_ID=client_id_tähän
   TWITCH_CLIENT_SECRET=client_secret_tähän
   ```

3. **Aseta web-dashboardissa** (Twitch stream -ilmoitukset -osio)
   - Ota Twitch käyttöön Komennot-osiosta (Twitch-valintaruutu)
   - Lisää seuratut streamerit (Twitch-käyttäjänimet, esim. `s44gaming`)
   - Valitse kanava johon ilmoitukset lähetetään
   - Tallenna asetukset

4. **Käynnistä botti** – ilmoitukset alkavat noin 2 minuutin sisällä kun streameri aloittaa striimin

Ilmoituksessa näkyy striimin nimi, peli, katsojamäärä ja linkki Twitchiin. Jos TWITCH_CLIENT_ID tai TWITCH_CLIENT_SECRET puuttuu, ominaisuus ei toimi.

### Tikettijärjestelmä

| Komento | Kuvaus |
|---------|--------|
| `/tiketti_paneeli` | Lähettää "Avaa tiketti" -viestin webistä valituille kanavalle (vain ylläpitäjille) |

**Miten tikettijärjestelmä toimii**

1. **Aseta web-dashboardissa** (Tikettijärjestelmä -osio):
   - **Rooli joka näkee tiketit** – rooli (esim. Staff), joka pääsee vastaamaan tikeille
   - **Kategoria tiketille** – kategoria johon uudet tiketit luodaan
   - **Kanava josta tiketti avataan** – kanava johon "Avaa tiketti" -viesti lähetetään
2. **Ota Tikettijärjestelmä käyttöön** (Perusominaisuudet -osio)
3. **Suorita Discordissa** `/tiketti_paneeli` – botti lähettää viestin valitulle kanavalle
4. **Käyttäjät** painavat "Avaa tiketti" -nappia → luodaan yksityinen kanava (vain avaaja + staff näkevät)
5. **Staff** vastaa tiketissa ja voi sulkea sen "Sulje tiketti" -napilla

---

Kaikki ominaisuudet voidaan ottaa pois käytöstä web-dashboardista palvelin kerrallaan.

### Botin status ja tiedot

Botin Discord-statuksessa (»Watching«) näkyy palvelimien määrä, kuvaus ja kehittäjät. Nämä voi muokata:
- **data/bot_info.txt** tai salattu **data/bot_info.enc**
- tai kehittäjäportaalin Botin tiedot -osiossa (vaatii BOT_INFO_EDIT_PASSWORD .env:ssä)

## Projektin rakenne

```
DiscordBotti/
├── LICENSE
├── run.py              # Käynnistys (botti + web)
├── start.sh            # Käynnistys Linux/macOS
├── start.bat           # Käynnistys Windows
├── bot.py              # Discord-botin logiikka
├── web_app.py          # Flask web-sovellus
├── database.py         # Tietokanta (SQLite)
├── config.py           # Konfiguraatio
├── bot_info.py         # Botin tiedot (kuvaus, kehittäjät, linkit) – salasanasuojattu
├── fivem_status.py     # FiveM-palvelimen tilan haku
├── twitch_streams.py   # Twitch API -apu (livestream-kyselyt)
├── shared_state.py     # Jaettu tila (dev-portaalia varten)
├── logs.py
├── requirements.txt
├── .env.example
├── commands/
│   ├── ping.py
│   ├── komennot_lista.py  # /komennot – kaikki komennot
│   ├── info.py
│   ├── tervehdys.py
│   ├── hallinta.py
│   ├── kutsu.py         # /kutsu, /lähetäkutsu
│   ├── moderaatio.py
│   ├── taso.py
│   ├── tiketti.py
│   ├── minipelit.py     # kolikko, noppa, 8ball, kps, arpa, ruletti
│   └── fivem.py         # /fivem
├── events/
│   ├── on_ready.py
│   ├── server_logs.py
│   ├── levels.py
│   └── twitch_streams.py  # Twitch stream -ilmoitukset (taustapollaus)
├── web/
│   ├── templates/
│   └── static/
└── data/
    ├── bot.db
    ├── bot_info.txt     # Botin tiedot (voi olla salattu bot_info.enc)
    └── ...
```

## Tuotantokäyttö

- Vaihda `BASE_URL` ja `DISCORD_REDIRECT_URI` tuotannon domainiin
- Käytä vahvaa `FLASK_SECRET_KEY`-arvoa
- Harkitse HTTPS:ää ja reverse-proxyä (esim. Nginx)
- Voit käyttää Gunicornia web-sovellukselle erillisessä prosessissa

### Cross-platform (Windows, Linux, macOS)

Sovellus toimii kaikilla yllä mainituilla alustoilla. Käytössä `os.path` ja `pathlib` – polut toimivat oikein riippumatta käyttöjärjestelmästä.

**Linux-palvelimella:**

```bash
# Asenna riippuvuudet
pip3 install -r requirements.txt

# Luo virtuaaliympäristö (suositeltu)
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Käynnistä
python3 run.py
# tai: chmod +x start.sh && ./start.sh
```

**Windowsilla:** käytä `python run.py` tai kaksoisklikkaa `start.bat`.

**Kopiointi Linux-koneelle:** vie koko projektikansio (esim. `scp -r` tai git clone). `.env` tulee luoda uudelleen tai kopioida erikseen.

## Tuki ja yhteisö

Jos tarvitset apua botin kanssa, liity [S44Gaming Squad](https://discord.gg/ujB4JHfgcg) Discord-palvelimelle ja lähetä viesti kanavalle **#tukitiketti**.

## Lisenssi

Katso [LICENSE](LICENSE). Tekijän oikeudet: S44Gaming. Ei-kaupallinen käyttö sallittu; kaupallinen käyttö vain S44Gaming:n suostumuksella.

---

*Tekijänoikeudet S44Gaming kaikki oikeudet pidätetään. https://discord.gg/ujB4JHfgcg*
