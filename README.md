# Xevrion – Discord Bot

Python-pohjainen Discord-botti (Xevrion), joka tukee useaa palvelinta ja web-käyttöliittymää palvelinkohtaisten asetusten hallintaan. Vain ylläpitäjät voivat hallita asetuksia.

## Julkinen Xevrion (S44Gaming)

Voit käyttää S44Gamingin ylläpitämää Xevrion-bottia omalla palvelimellasi ilman omaa asennusta:

- **[Botin hallintapaneeli](https://discordbotti.s44gamingsquad.com/dashboard)** – kirjaudu Discordilla ja hallitse asetuksia
- **[Kutsu botti palvelimelle](https://discord.com/oauth2/authorize?client_id=1468083482398818516&scope=bot&permissions=0)** – lisää Xevrion omaan Discord-palvelimeesi


## Ominaisuudet

- **Monipalvelin** – sama botti usealla serverillä, kaikki asetukset palvelinkohtaisia
- **Web-dashboard** – hallitse kaikkia ominaisuuksia palvelin kerrallaan, tumma/vaalea teema (tallentuu selaimen localStorage)
- **Monikielisyys** – web-käyttöliittymä tukee **55 kieltä**: suomi, englanti, saksa, ranska, espanja, italia, hollanti, puola, portugali, venäjä, japani, kiina, ruotsi, norja, tanska, turkki, korea, tšekki, unkari, indonesia, thai, vietnam, arabia, hindi, ukraina, romania, kreikka, slovakia, heprea, filipino, malaiji, bengali, serbia, bulgaria, kroatia, slovenia, liettua, latvia, viro, persia, swahili, afrikaans, katalaani, galicia, tamil, telugu, malajalam, urdu, azeri, armenia, georgia, sinhala, nepal, burma, khmer. *Huom: käännökset on tehty teköälykäännöksillä, joten niissä voi olla virheitä.*
- **Ylläpitäjä-tarkistus** – vain palvelimen Administratorit näkevät hallinnan
- **Peruskomentoja** – ping, info, tervehdys, hallinta, komennot-lista
- **Kutsulinkit** – /kutsu (Apply bot), /lähetäkutsu (yhteisön kutsu kanavalle)
- **Moderaatio** – kick, ban, mute, varoitukset, clear – roolit ja toiminnat hallitaan webistä
- **Serverilogit** – mod-toiminnot, jäsenet liittyy/poistuu, viestien poisto/muokkaus – kanava ja tyypit webistä
- **Tikettijärjestelmä** – staff-rooli, kategoria, kanava, tiketin aiheet (pudotusvalikko), transcript-kanava suljetuille tikeille – webistä
- **Levellijärjestelmä** – taso ja XP, tasonboard, ääni-XP, taso-roolit, kanavat ilman XP – asetukset webistä
- **Minipelit** – kolikko, noppa, 8-pallo, kivi-paperi-sakset, arpa, ruletti, arvaa luku – kytkettävissä webistä
- **AFK** – /afk asettaa AFK-tilan; kun mainitset AFK-käyttäjän, botti vastaa syyllä
- **Ehdotus** – /ehdotus lähettää ehdotuksen määritellylle kanavalle
- **Muistutus** – /muistutus asettaa muistutuksen (esim. 5m, 1h); max 7 päivää, cooldown ja raja käyttäjää kohti
- **Arvonta** – /arvonta arpoo voittajat viestin reagoijista (mod-oikeudet)
- **Starboard** – viestit joissa tarpeeksi ⭐ reaktioita kopioidaan erityiselle kanavalle; vähimmäisreaktiot webistä
- **Tervetuloa- ja poistumisviestit** – viestimalli placeholdereilla ({user}, {mention}, {server}, {member_count})
- **Autorole** – uudet jäsenet saavat automaattisesti valitut roolit
- **FiveM-palvelimen tila** – /fivem näyttää pelaajamäärän jne., asetukset (host, port, status-kanava) webistä
- **Twitch stream -ilmoitukset** – ilmoitus kun seuraamasi streameri aloittaa striimin, streamerit ja kanava webistä
- **Kehittäjäportaali** – DEV_USER_IDS -käyttäjille: tilastot (CPU, muisti, latenssihistoria), virheloki, tietokanta-tilastot, riippuvuuksien versiot, varmuuskopio (asetusten export), API-dokumentaatio, konsoliloki (suodatin), käynnistä/sammuta, palvelimen poisto

## Vaatimukset

- **Python 3.8+** (suositellaan 3.10 tai uudempi)
- **Paketit**:
  - discord.py >= 2.7.1
  - flask >= 3.0.0
  - requests >= 2.31.0
  - python-dotenv >= 1.0.0
  - cryptography >= 42.0.0 (botin tietojen salattu tallennus)
  - psutil >= 5.9.0 (CPU- ja muistikäyttö kehittäjäportaalissa)

Vapaaehtoinen: `discord.py[speed]` nopeampaan JSON-käsittelyyn.

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
5. **Teema** – vaihda tumma/vaalea teema headerin napilla (tallentuu selaimen localStorageen)

### Webissä hallittavat asetukset (palvelinkohtaisesti)

| Osa | Asetukset |
|-----|-----------|
| **Komennot** | Ping, Info, Hallinta, Kutsu, Kutsuviesti, Tiketti, Taso, Tasonboard, minipelit, Twitch, AFK, Muistutus, Ehdotus, Arvonta jne. – päälle/pois |
| **Minipelit** | Kolikko, Noppa, 8-pallo, Kivi-paperi-sakset, Arvaa luku, Arpa, Ruletti – päälle/pois |
| **FiveM** | Palvelimen osoite, portti (oletus 30120), kanava johon status voidaan lähettää |
| **Twitch** | Seuratut streamerit (käyttäjänimet), kanava johon ilmoitukset lähetetään |
| **Moderaatio** | Moderaattoriroolit, yksittäisten mod-toimintojen päälle/pois |
| **Logit** | Logikanava, lokityypit (mod-toiminnot, jäsen liittyy/poistuu, viestin poisto/muokkaus) |
| **Tervetuloa** | Päälle/pois, kanava, viestimalli ({user}, {mention}, {server}, {member_count}) |
| **Poistumisviesti** | Päälle/pois, kanava, viestimalli ({user}, {server}) |
| **Ehdotus** | Ehdotuskanava |
| **AFK, Arvonta, Muistutus** | Päälle/pois; muistutuksille: max/käyttäjä, cooldown (sek) |
| **Autorole** | Roolit joita uudet jäsenet saavat automaattisesti |
| **Levellijärjestelmä** | Päälle/pois, XP/viesti, cooldown, ääni-XP, taso-roolit, kanavat ilman XP |
| **Tiketit** | Staff-rooli, kategoria, kanava, transcript-kanava, tiketin aiheet (pudotusvalikko), paneelin otsikko ja ohjeteksti |
| **Starboard** | Kanava, vähimmäisreaktiot (⭐) |

### Teema (dashboard)

Dashboardissa voit vaihtaa tumman ja vaalean teeman välillä. Valinta tallentuu selaimen localStorageen ja pätee dashboardille sekä palvelimen asetuksille.

### Kehittäjäportaali (vain DEV_USER_IDS)

Jos Discord-käyttäjä-IDsi on `.env`:ssä `DEV_USER_IDS`-listalla, näet linkin **Kehittäjäportaali**. Siellä voit:
- nähdä bottin tilat (latenssi, palvelimet, muisti, CPU %, ajoaika, komennot)
- latenssin historian graafina
- tarkastella virhelokia (käsittelemättömät virheet tallentuvat automaattisesti)
- tyhjentää virhelokin
- tarkastella tietokannan tilastoja (taulut, rivimäärät, koko)
- nähdä ympäristömuuttujien avaimet (ei arvoja)
- nähdä riippuvuuksien versiot (discord.py, flask, jne.)
- ladata varmuuskopion (kaikki palvelinasetukset JSON-tiedostona)
- tarkastella API-dokumentaatiota (endpointit)
- tarkastella konsolilokia suodattimella
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

### AFK, Ehdotus, Muistutus, Arvonta

| Komento | Kuvaus |
|---------|--------|
| `/afk` | Aseta AFK-tila (valinnainen syy). Kun mainitset AFK-käyttäjän, botti vastaa syyllä. |
| `/ehdotus` | Lähetä ehdotus ylläpidolle – lähetetään ehdotuskanavalle (aseta webistä). |
| `/muistutus` | Aseta muistutus: aika (esim. 5m, 1h, 1h30m) ja viesti. Minimi 10 s, max 7 päivää. |
| `/arvonta` | Arvo voittajat viestin reagoijista (vaatii mod-oikeudet). Parametrit: määrä (1–20), viestin ID. |

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
| `/tiketti_paneeli` | Lähettää tiketti-paneelin webistä valituille kanavalle (vain ylläpitäjille) |

**Miten tikettijärjestelmä toimii**

1. **Aseta web-dashboardissa** (Tikettijärjestelmä -osio):
   - **Rooli joka näkee tiketit** – rooli (esim. Staff), joka pääsee vastaamaan tikeille
   - **Kategoria tiketille** – kategoria johon uudet tiketit luodaan
   - **Kanava josta tiketti avataan** – kanava johon paneeli lähetetään
   - **Transcript-kanava** – suljetut tiketit tallennetaan sinne (valinnainen)
   - **Tiketin aiheet** – pudotusvalikon aiheet (otsikko, kuvaus, emoji, rooli); jos aiheita on, käyttäjät valitsevat aiheen
   - **Paneelin otsikko ja ohjeteksti** – näkyvät Discord-embedissä
2. **Ota Tikettijärjestelmä käyttöön** (Komennot -osiossa Tiketti)
3. **Suorita Discordissa** `/tiketti_paneeli` – botti lähettää paneelin valitulle kanavalle
4. **Käyttäjät** valitsevat aiheen pudotusvalikosta ja painavat nappia → luodaan yksityinen kanava
5. **Staff** vastaa tiketissa ja voi sulkea sen "Sulje tiketti" -napilla; suljetut tiketit tallennetaan transcript-kanavalle

### Starboard

Viestit joissa vähintään N ⭐ reaktiota kopioidaan automaattisesti starboard-kanavalle. Aseta web-dashboardissa (Integraatiot) starboard-kanava ja vähimmäisreaktioiden määrä (1–20). Tähtimäärä päivittyy reaktioiden muuttuessa; jos tähtimäärä putoaa alle rajan, viesti poistetaan starboardilta.

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
│   ├── fivem.py         # /fivem
│   ├── afk.py           # /afk
│   ├── ehdotus.py       # /ehdotus
│   ├── muistutus.py     # /muistutus
│   └── arvonta.py       # /arvonta
├── events/
│   ├── on_ready.py
│   ├── server_logs.py
│   ├── levels.py
│   ├── twitch_streams.py  # Twitch stream -ilmoitukset (taustapollaus)
│   ├── afk.py             # AFK-maininnan käsittely
│   ├── starboard.py       # Starboard (⭐-reaktiot)
│   └── reminders.py       # Muistutusten taustaloop
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
