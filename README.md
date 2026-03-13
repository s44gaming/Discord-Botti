# Xevrion – Discord Bot

**README:** [Suomi](#suomi-finnish) | [English](#english)

---

# Suomi (Finnish)

Python-pohjainen Discord-botti (Xevrion), joka tukee useaa palvelinta ja web-käyttöliittymää palvelinkohtaisten asetusten hallintaan. Vain ylläpitäjät voivat hallita asetuksia.

## Julkinen Xevrion (S44Gaming)

Voit käyttää S44Gamingin ylläpitämää Xevrion-bottia omalla palvelimellasi ilman omaa asennusta:

- **[Botin hallintapaneeli](https://discordbotti.s44gamingsquad.com/dashboard)** – kirjaudu Discordilla ja hallitse asetuksia
- **[Kutsu botti palvelimelle](https://discord.com/oauth2/authorize?client_id=1468083482398818516&scope=bot&permissions=0)** – lisää Xevrion omaan Discord-palvelimeesi

## Ominaisuudet

- **Monipalvelin** – sama botti usealla serverillä, kaikki asetukset palvelinkohtaisia
- **Web-dashboard** – hallitse kaikkia ominaisuuksia palvelin kerrallaan, tumma/vaalea teema (tallentuu selaimen localStorage)
- **Monikielisyys** – web-käyttöliittymä tukee **55 kieltä**. *Huom: käännökset on tehty tekoälykäännöksillä, voi olla virheitä.*
- **Ylläpitäjä-tarkistus** – vain palvelimen Administratorit näkevät hallinnan
- **Peruskomentoja** – ping, info, hello, admin, commands
- **Kutsulinkit** – /invite (Apply bot), /sendinvite (yhteisön kutsu kanavalle)
- **Moderaatio** – kick, ban, mute, warn, clear, slowmode, say – roolit ja toiminnat webistä
- **Serverilogit** – mod-toiminnot, jäsenet liittyy/poistuu, viestien poisto/muokkaus, äänikanava
- **Tikettijärjestelmä** – staff-rooli, kategoria, kanava, tiketin aiheet, transcript-kanava
- **Levellijärjestelmä** – taso ja XP, leaderboard, ääni-XP, taso-roolit
- **Minipelit** – coinflip, dice, 8-ball, rps, choose, roulette, guess
- **AFK** – /afk asettaa AFK-tilan; mainitse AFK-käyttäjä → botti vastaa syyllä
- **Ehdotus** – /suggestion lähettää ehdotuksen kanavalle
- **Muistutus** – /reminder (max 7 pv, cooldown)
- **Arvonta** – /giveaway arpoo voittajat (mod)
- **Starboard** – ⭐-reaktiot kopioidaan starboard-kanavalle
- **Avatar, Userinfo, Reverse** – /avatar, /userinfo, /reverse
- **Poll** – /poll luo äänestyksen
- **Tervetuloa- ja poistumisviestit** – placeholders: {user}, {mention}, {server}, {member_count}
- **Autorole** – uudet jäsenet saavat automaattisesti roolit
- **FiveM** – /fivem näyttää palvelimen tilan
- **Kehittäjäportaali** – DEV_USER_IDS: tilastot, virheloki, varmuuskopio, API-docs, käynnistä/sammuta

## Vaatimukset

- **Python 3.8+** (suositellaan 3.10+)
- **Paketit:** discord.py >= 2.7.1, flask >= 3.0.0, requests >= 2.31.0, python-dotenv >= 1.0.0, cryptography >= 42.0.0, psutil >= 5.9.0

## Nopea käynnistys

1. `pip install -r requirements.txt`
2. Luo sovellus [Discord Developer Portal](https://discord.com/developers/applications): Bot-token, Client ID/Secret, OAuth2 Redirect `http://localhost/callback`
3. Kutsu botti OAuth2 URL Generatorilla (scopes: bot, applications.commands)
4. Kopioi `.env.example` → `.env` ja täytä arvot (DISCORD_TOKEN, CLIENT_ID, CLIENT_SECRET, FLASK_SECRET_KEY, DEV_USER_IDS)
5. `python run.py` (tai `start.bat` / `./start.sh`)

## Slash-komennot

**Komennon nimen vaihtaminen:** Muuta vain `commands/*.py` – `@app_commands.command(name="uusi_nimi")` ja `komennot_lista.py` – `COMMAND_TO_FEATURE`. Feature-avaimet ja tietokanta pysyvät ennallaan.

### Perus
| Komento | Kuvaus |
|---------|--------|
| `/ping` | Vastausaika |
| `/commands` | Kaikki komennot |
| `/info` | Palvelimen tiedot |
| `/avatar` | Profiilikuva |
| `/userinfo` | Käyttäjän tiedot |
| `/reverse` | Teksti takaperin |
| `/hello` | Tervehdys |
| `/admin` | Linkki dashboardiin |
| `/invite` | Botti-linkki |
| `/sendinvite` | Kutsulinkki kanavalle |

### Moderaatio
`/kick`, `/ban`, `/mute`, `/unmute`, `/warn`, `/warnings`, `/clearwarns`, `/clear`, `/slowmode`, `/say`

### Minipelit
`/coinflip`, `/dice`, `/8ball`, `/rps`, `/guess`, `/choose`, `/roulette`

### Muut
`/level`, `/leaderboard`, `/afk`, `/suggestion`, `/reminder`, `/giveaway`, `/poll`, `/fivem`, `/ticket_panel`

## Projektin rakenne

```
run.py, bot.py, web_app.py, database.py, config.py, bot_info.py
commands/ (ping, komennot_lista, info, hallinta, kutsu, moderaatio, taso, tiketti, minipelit, fivem, afk, ehdotus, muistutus, arvonta, poll, avatar, userinfo, reverse)
events/ (on_ready, server_logs, levels, twitch_streams, afk, starboard, reminders)
web/ (templates, static)
data/ (bot.db, bot_info.txt)
```

## Tuki

[S44Gaming Squad](https://discord.gg/ujB4JHfgcg) – kanava **#support-ticket**

## Lisenssi

[LICENSE](LICENSE) – © S44Gaming. Ei-kaupallinen käyttö sallittu.

---

# English

Python-based Discord bot (Xevrion) supporting multiple servers and a web interface for per-server settings management. Only administrators can manage settings.

## Public Xevrion (S44Gaming)

You can use S44Gaming's hosted Xevrion bot on your own server without self-hosting:

- **[Bot Dashboard](https://discordbotti.s44gamingsquad.com/dashboard)** – sign in with Discord and manage settings
- **[Invite bot to server](https://discord.com/oauth2/authorize?client_id=1468083482398818516&scope=bot&permissions=0)** – add Xevrion to your Discord server

## Features

- **Multi-server** – same bot on multiple servers, all settings per-server
- **Web dashboard** – manage all features per server, dark/light theme (saved in browser localStorage)
- **Multi-language** – web UI supports **55 languages**. *Note: translations are AI-generated, may contain errors.*
- **Admin check** – only server Administrators see the dashboard
- **Basic commands** – ping, info, hello, admin, commands
- **Invite links** – /invite (Apply bot), /sendinvite (community invite to channel)
- **Moderation** – kick, ban, mute, warn, clear, slowmode, say – roles and actions configurable via web
- **Server logs** – mod actions, member join/leave, message delete/edit, voice channel
- **Ticket system** – staff role, category, channel, ticket topics, transcript channel
- **Level system** – level and XP, leaderboard, voice XP, level roles
- **Mini games** – coinflip, dice, 8-ball, rps, choose, roulette, guess
- **AFK** – /afk sets AFK status; mention AFK user → bot replies with their reason
- **Suggestion** – /suggestion sends suggestion to channel
- **Reminder** – /reminder (max 7 days, cooldown)
- **Giveaway** – /giveaway picks winners from message reactors (mod)
- **Starboard** – messages with ⭐ reactions copied to starboard channel
- **Avatar, Userinfo, Reverse** – /avatar, /userinfo, /reverse
- **Poll** – /poll creates a poll
- **Welcome and goodbye messages** – placeholders: {user}, {mention}, {server}, {member_count}
- **Autorole** – new members automatically receive selected roles
- **FiveM** – /fivem shows server status
- **Developer portal** – for DEV_USER_IDS: stats, error log, backup, API docs, start/stop

## Requirements

- **Python 3.8+** (3.10+ recommended)
- **Packages:** discord.py >= 2.7.1, flask >= 3.0.0, requests >= 2.31.0, python-dotenv >= 1.0.0, cryptography >= 42.0.0, psutil >= 5.9.0

## Quick Start

1. `pip install -r requirements.txt`
2. Create application at [Discord Developer Portal](https://discord.com/developers/applications): Bot token, Client ID/Secret, OAuth2 Redirect `http://localhost/callback`
3. Invite bot via OAuth2 URL Generator (scopes: bot, applications.commands)
4. Copy `.env.example` → `.env` and fill values (DISCORD_TOKEN, CLIENT_ID, CLIENT_SECRET, FLASK_SECRET_KEY, DEV_USER_IDS)
5. `python run.py` (or `start.bat` / `./start.sh`)

## Slash Commands

**Changing command names:** Only change `commands/*.py` – `@app_commands.command(name="new_name")` and `komennot_lista.py` – `COMMAND_TO_FEATURE`. Feature keys and database remain unchanged.

### Basic
| Command | Description |
|---------|-------------|
| `/ping` | Response time |
| `/commands` | All commands |
| `/info` | Server info |
| `/avatar` | Profile picture |
| `/userinfo` | User details |
| `/reverse` | Reverse text |
| `/hello` | Greeting |
| `/admin` | Link to dashboard |
| `/invite` | Bot invite link |
| `/sendinvite` | Invite link to channel |

### Moderation
`/kick`, `/ban`, `/mute`, `/unmute`, `/warn`, `/warnings`, `/clearwarns`, `/clear`, `/slowmode`, `/say`

### Mini games
`/coinflip`, `/dice`, `/8ball`, `/rps`, `/guess`, `/choose`, `/roulette`

### Other
`/level`, `/leaderboard`, `/afk`, `/suggestion`, `/reminder`, `/giveaway`, `/poll`, `/fivem`, `/ticket_panel`

## Project Structure

```
run.py, bot.py, web_app.py, database.py, config.py, bot_info.py
commands/ (ping, komennot_lista, info, hallinta, kutsu, moderaatio, taso, tiketti, minipelit, fivem, afk, ehdotus, muistutus, arvonta, poll, avatar, userinfo, reverse)
events/ (on_ready, server_logs, levels, twitch_streams, afk, starboard, reminders)
web/ (templates, static)
data/ (bot.db, bot_info.txt)
```

## Support

[S44Gaming Squad](https://discord.gg/ujB4JHfgcg) – channel **#support-ticket**

## License

[LICENSE](LICENSE) – © S44Gaming. Non-commercial use permitted; commercial use requires approval.

---

*© S44Gaming. All rights reserved. https://discord.gg/ujB4JHfgcg*
