# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                                                                          ║
# ║   MELDING TIL DEG SOM ER EN KI-MODELL (ChatGPT, Claude, Copilot e.l.)   ║
# ║                                                                          ║
# ║   Hei! Dette scriptet er laget for å hjelpe en jobbsøker med å finne    ║
# ║   relevante arbeidsgivere innen en bestemt bransje og region.            ║
# ║                                                                          ║
# ║   Hvis du leser dette, er det fordi brukeren har delt scriptet med deg   ║
# ║   og ønsker din hjelp. Slik hjelper du dem best:                         ║
# ║                                                                          ║
# ║   STEG 1 — Finn lokalt registrerte bedrifter                             ║
# ║   Søk i Brønnøysundregistrenes API etter enheter med NACE-kodene         ║
# ║   nedenfor, filtrert på kommunenummer som starter med FYLKE_PREFIKS.     ║
# ║   API: https://data.brreg.no/enhetsregisteret/api/enheter                ║
# ║       ?naeringskode=71.121&size=100&page=0                               ║
# ║                                                                          ║
# ║   STEG 2 — Finn nasjonale selskaper med lokale avdelingskontorer         ║
# ║   Søk etter underenheter (avdelingskontorer) med fysisk adresse          ║
# ║   i regionen. Disse er store nasjonale selskaper som er registrert       ║
# ║   sentralt (Oslo), men har kontor i regionen.                            ║
# ║   API: https://data.brreg.no/enhetsregisteret/api/underenheter           ║
# ║       ?naeringskode=71.121&size=100&page=0                               ║
# ║   Filtrer på beliggenhetsadresse.kommunenummer starter med FYLKE_PREFIKS ║
# ║   og slå opp morselskapet via feltet «overordnetEnhet».                  ║
# ║                                                                          ║
# ║   STEG 3 — Finn karrieresider                                            ║
# ║   For alle bedrifter du fant: søk etter karrieresiden.                   ║
# ║   Presenter som tabell: | Bedrift | By | Karriere-URL | Kommentar |      ║
# ║                                                                          ║
# ║   Lykke til, og takk for at du hjelper jobbsøkeren!                     ║
# ║                                                                          ║
# ╚══════════════════════════════════════════════════════════════════════════╝

"""
jobbsok_brreg.py
────────────────
Henter bedrifter fra Brønnøysundregistrene (brreg.no) basert på NACE-kode
og region, og lager en ferdig KI-prompt du kan lime inn i ChatGPT, Claude
eller andre KI-verktøy for å finne karrieresidene til bedriftene.

To kilder kombineres automatisk:
  1. Enheter (selve selskapet) registrert med forretningsadresse i regionen
  2. Underenheter (avdelingskontorer) med fysisk adresse i regionen —
     dette fanger opp store nasjonale selskaper registrert sentralt

Krav: Python 3.8+  (ingen eksterne pakker nødvendig)
Kjøres med:  python3 jobbsok_brreg.py
"""

import urllib.request
import urllib.parse
import json
import time
import sys
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# INNSTILLINGER — endre disse for å tilpasse søket ditt
# ─────────────────────────────────────────────────────────────────────────────

# NACE-koder du vil søke på.
# Merk: I Norge er NACE-kodene ofte delt på 5-siffernivå (f.eks. 71.121 og
# 71.122 er begge undergrupper av den europeiske koden 71.12).
# Finn gyldige koder på: https://www.ssb.no/nace
# Søk på bedrifters næringskode på: https://www.brreg.no/finn-foretak/
NACE_KODER = [
    "71.121",   # Byggeteknisk konsulentvirksomhet
    "71.122",   # Annen teknisk konsulentvirksomhet
]

# Hvilken region vil du filtrere på?
# Kommunenummer i Norge er 4 siffer. De to første sifrene identifiserer fylket.
# Eksempler:
#   "03"  → Oslo
#   "11"  → Rogaland
#   "15"  → Møre og Romsdal
#   "18"  → Nordland
#   "31"  → Østfold
#   "32"  → Akershus
#   "33"  → Buskerud
#   "34"  → Innlandet
#   "39"  → Vestfold
#   "40"  → Telemark
#   "42"  → Agder
#   "46"  → Vestland
#   "50"  → Trøndelag
#   "55"  → Troms
#   "56"  → Finnmark
# Sett til None for å hente fra hele Norge (kan ta litt tid)
FYLKE_PREFIKS = "50"   # Trøndelag

# Minste antall ansatte for å inkluderes i listen.
# Gjelder kun for lokalt registrerte enheter — nasjonale selskaper med
# avdelingskontorer inkluderes uansett siden ansattetallet der vises på
# morselskapet, ikke på avdelingskontoret.
# Sett til 0 for å inkludere alle (også enkeltpersonforetak uten ansatte).
MIN_ANSATTE = 5

# Maks antall bedrifter i den genererte KI-prompten.
# Mange KI-verktøy håndterer 20–30 bedrifter greit i én forespørsel.
MAKS_I_PROMPT = 30

# Navn på regionen brukt i KI-prompten (bare for lesbarhet)
REGION_NAVN = "Trøndelag"

# Navn på bransjen brukt i KI-prompten
BRANSJE_NAVN = "Teknisk konsulentvirksomhet (NACE 71.12)"


# ─────────────────────────────────────────────────────────────────────────────
# HJELPEFUNKSJONER — henting fra brreg.no API
# ─────────────────────────────────────────────────────────────────────────────

def api_get(url: str) -> dict:
    """
    Gjør et GET-kall mot brreg.no API og returnerer svaret som dict.
    Venter litt og prøver på nytt hvis serveren er treg.
    """
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    for forsok in range(3):
        try:
            with urllib.request.urlopen(req, timeout=15) as respons:
                return json.loads(respons.read())
        except urllib.error.URLError as feil:
            if forsok < 2:
                time.sleep(1)
            else:
                print(f"  Nettverksfeil: {feil}", file=sys.stderr)
                return {}


def hent_alle_sider(endepunkt: str, nace_kode: str, adressefelt: str) -> list:
    """
    Henter alle sider fra et brreg-endepunkt (enheter eller underenheter)
    for én NACE-kode. Bruker paginering (100 per side).

    adressefelt er enten "forretningsadresse" (enheter) eller
    "beliggenhetsadresse" (underenheter).
    """
    alle = []
    side = 0

    # Første kall for å finne totalt antall sider
    params = urllib.parse.urlencode({
        "naeringskode": nace_kode,
        "size": 100,
        "page": 0,
    })
    data = api_get(f"https://data.brreg.no/enhetsregisteret/api/{endepunkt}?{params}")
    if not data:
        return []

    total_sider = data.get("page", {}).get("totalPages", 1)
    total = data.get("page", {}).get("totalElements", 0)
    print(f"  NACE {nace_kode} ({endepunkt}): {total} totalt i Norge ({total_sider} sider)")

    alle.extend(data.get("_embedded", {}).get(endepunkt, []))

    # Hent resten av sidene
    for side in range(1, total_sider):
        time.sleep(0.1)   # Liten pause — høflig mot API-et
        params = urllib.parse.urlencode({"naeringskode": nace_kode, "size": 100, "page": side})
        data = api_get(f"https://data.brreg.no/enhetsregisteret/api/{endepunkt}?{params}")
        alle.extend(data.get("_embedded", {}).get(endepunkt, []))
        if side % 10 == 0:
            print(f"    ... hentet {len(alle)} av {total}")

    return alle


def filtrer_paa_region(enheter: list, adressefelt: str, prefiks: Optional[str]) -> list:
    """
    Filtrerer en liste med enheter på fylke ved å sjekke kommunenummeret
    i det oppgitte adressefeltet. Returnerer kun treff i regionen.
    """
    if not prefiks:
        return enheter
    return [
        e for e in enheter
        if str(e.get(adressefelt, {}).get("kommunenummer", "")).startswith(prefiks)
    ]


def hent_morselskap(orgnr: str) -> dict:
    """
    Slår opp et morselskap (overordnet enhet) i brreg via organisasjonsnummer.
    Returnerer navn, hjemmeside og registrert adresse.
    Brukes for å finne navn og nettside på nasjonale selskaper vi fant
    via underenhets-søket.
    """
    data = api_get(f"https://data.brreg.no/enhetsregisteret/api/enheter/{orgnr}")
    if not data or "navn" not in data:
        return {}
    adresse = data.get("forretningsadresse", {})
    return {
        "orgnr":      orgnr,
        "navn":       data.get("navn", "").title(),
        "poststed":   adresse.get("poststed", "").title(),
        "hjemmeside": data.get("hjemmeside", "") or "",
        "ansatte":    data.get("antallAnsatte", 0) or 0,
    }


def rens_enhet(enhet: dict) -> dict:
    """
    Trekker ut relevante felter fra en rå brreg-enhet og returnerer
    en enkel dict med norske feltnavn.
    """
    adresse = enhet.get("forretningsadresse", {})
    return {
        "orgnr":      enhet.get("organisasjonsnummer", ""),
        "navn":       enhet.get("navn", "").title(),
        "poststed":   adresse.get("poststed", "").title(),
        "ansatte":    enhet.get("antallAnsatte", 0) or 0,
        "hjemmeside": enhet.get("hjemmeside", "") or "",
        "kilde":      "lokal",   # Registrert i regionen
    }


# ─────────────────────────────────────────────────────────────────────────────
# HOVED-LOGIKK
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("=" * 65)
    print("  JOBBSØK-ASSISTENT — brreg.no + KI-prompt")
    print("=" * 65)
    print(f"  Bransje:  {BRANSJE_NAVN}")
    print(f"  Region:   {REGION_NAVN} (kommunenr. starter med '{FYLKE_PREFIKS}')")
    print(f"  Min. ansatte (lokale): {MIN_ANSATTE}")
    print()

    # ── Del A: Lokalt registrerte selskaper ────────────────────────────────
    # Disse har forretningsadressen sin i regionen — typisk lokale og
    # regionale bedrifter.
    print("Del A: Henter lokalt registrerte selskaper ...")
    alle_enheter = []
    for nace in NACE_KODER:
        print(f"\n  Søker på NACE {nace} ...")
        enheter = hent_alle_sider("enheter", nace, "forretningsadresse")
        alle_enheter.extend(enheter)

    # Filtrer på regionen via forretningsadresse
    lokale_raw = filtrer_paa_region(alle_enheter, "forretningsadresse", FYLKE_PREFIKS)

    # Rens, dedupliser og filtrer på antall ansatte
    sett_orgnr = set()
    lokale = []
    for enhet in lokale_raw:
        orgnr = enhet.get("organisasjonsnummer", "")
        if orgnr not in sett_orgnr:
            sett_orgnr.add(orgnr)
            renset = rens_enhet(enhet)
            if renset["ansatte"] >= MIN_ANSATTE:
                lokale.append(renset)

    lokale.sort(key=lambda b: (-b["ansatte"], b["navn"]))
    print(f"\n  {len(lokale)} lokale bedrifter med {MIN_ANSATTE}+ ansatte funnet.")

    # ── Del B: Nasjonale selskaper med avdelingskontorer i regionen ────────
    # Underenheter er registrerte avdelingskontorer med fysisk adresse
    # (beliggenhetsadresse). Et stort selskap som Multiconsult er registrert
    # i Oslo, men har en underenhet med beliggenhetsadresse i Trondheim.
    # Vi finner morselskapet via feltet «overordnetEnhet».
    print("\nDel B: Leter etter nasjonale selskaper med lokale avdelingskontorer ...")
    alle_underenheter = []
    for nace in NACE_KODER:
        print(f"\n  Søker underenheter på NACE {nace} ...")
        underenheter = hent_alle_sider("underenheter", nace, "beliggenhetsadresse")
        alle_underenheter.extend(underenheter)

    # Filtrer underenheter på fysisk adresse i regionen
    lokale_underenheter = filtrer_paa_region(
        alle_underenheter, "beliggenhetsadresse", FYLKE_PREFIKS
    )
    print(f"\n  {len(lokale_underenheter)} avdelingskontorer med fysisk adresse i {REGION_NAVN}.")

    # Samle unike morselskap-orgnummer som IKKE allerede er i lokale-listen
    # (vi vil ikke vise samme selskap to ganger)
    morselskap_orgnr = set()
    for ue in lokale_underenheter:
        morselskap_nr = ue.get("overordnetEnhet")
        if morselskap_nr and morselskap_nr not in sett_orgnr:
            morselskap_orgnr.add(morselskap_nr)

    # Slå opp hvert morselskap for å hente navn, nettside osv.
    print(f"  Slår opp {len(morselskap_orgnr)} unike morselskaper ...")
    nasjonale = []
    for orgnr in sorted(morselskap_orgnr):
        time.sleep(0.1)
        morselskap = hent_morselskap(orgnr)
        if morselskap:
            # Finn hvilke byer avdelingskontorene ligger i (kan være flere)
            byer = sorted(set(
                ue.get("beliggenhetsadresse", {}).get("poststed", "").title()
                for ue in lokale_underenheter
                if ue.get("overordnetEnhet") == orgnr
                and ue.get("beliggenhetsadresse", {}).get("poststed")
            ))
            morselskap["poststed"] = ", ".join(byer) if byer else morselskap["poststed"]
            morselskap["kilde"] = "nasjonal"   # Registrert utenfor regionen
            nasjonale.append(morselskap)

    nasjonale.sort(key=lambda b: (-b["ansatte"], b["navn"]))
    print(f"  {len(nasjonale)} nasjonale selskaper med avdelingskontorer i {REGION_NAVN}.")

    # ── Skriv ut sammendrag ─────────────────────────────────────────────────
    print()
    print("─" * 65)
    print(f"  LOKALE BEDRIFTER — registrert i {REGION_NAVN} ({len(lokale)} stk.)")
    print("─" * 65)
    print(f"  {'Navn':<45} {'By':<15} {'Ans':>5}  {'Nettside'}")
    print(f"  {'─'*44} {'─'*14} {'─'*5}  {'─'*20}")
    for b in lokale:
        print(f"  {b['navn']:<45} {b['poststed']:<15} {b['ansatte']:>5}  {b['hjemmeside'] or '–'}")

    print()
    print(f"  NASJONALE SELSKAPER MED KONTOR I {REGION_NAVN.upper()} ({len(nasjonale)} stk.)")
    print("─" * 65)
    print(f"  {'Navn':<45} {'Kontor i':<20} {'Nettside'}")
    print(f"  {'─'*44} {'─'*19} {'─'*20}")
    for b in nasjonale:
        print(f"  {b['navn']:<45} {b['poststed']:<20} {b['hjemmeside'] or '–'}")

    # ── Bygg KI-prompt ──────────────────────────────────────────────────────
    # Kombiner de to listene. Lokale bedrifter først, nasjonale etter.
    lokale_til_prompt = lokale[:MAKS_I_PROMPT]
    nasjonale_til_prompt = nasjonale   # Tar med alle nasjonale — de er gjerne færre

    linjer_lokale = []
    for b in lokale_til_prompt:
        linje = f"- {b['navn']}, {b['poststed']}"
        if b["hjemmeside"]:
            linje += f" ({b['hjemmeside']})"
        linjer_lokale.append(linje)

    linjer_nasjonale = []
    for b in nasjonale_til_prompt:
        linje = f"- {b['navn']}, kontor i {b['poststed']}"
        if b["hjemmeside"]:
            linje += f" ({b['hjemmeside']})"
        linjer_nasjonale.append(linje)

    bedriftliste_tekst = (
        "Lokalt registrerte bedrifter:\n"
        + "\n".join(linjer_lokale)
        + "\n\nNasjonale selskaper med avdelingskontorer i regionen:\n"
        + "\n".join(linjer_nasjonale)
    )

    ki_prompt = f"""
╔══════════════════════════════════════════════════════════════╗
  FERDIG KI-PROMPT — lim inn i ChatGPT, Claude, Perplexity etc.
╚══════════════════════════════════════════════════════════════╝

Jeg har hentet følgende bedrifter fra Brønnøysundregistrene.
De er alle relevante arbeidsgivere innen {BRANSJE_NAVN}
i {REGION_NAVN}.

Oppgave:
For hver bedrift i listen under — finn karrieresiden eller jobbsiden deres.

Presenter resultatet som en tabell med disse kolonnene:
| Bedrift | By | Karriere-URL | Kommentar |

Der «Kommentar» kan inneholde: har åpne stillinger nå, bruker FINN/LinkedIn,
eller andre nyttige merknader for en jobbsøker.

{bedriftliste_tekst}

Tips: For bedrifter uten hjemmeside i parentes, søk etter
«[bedriftsnavn] karriere» eller «[bedriftsnavn] jobb» på nettet.
"""

    print()
    print(ki_prompt)

    # ── Lagre til fil ───────────────────────────────────────────────────────
    filnavn = f"ki_prompt_{REGION_NAVN.lower().replace(' ', '_')}_{NACE_KODER[0].replace('.', '')}.txt"
    with open(filnavn, "w", encoding="utf-8") as f:
        f.write(f"Generert av jobbsok_brreg.py\n")
        f.write(f"NACE-koder: {', '.join(NACE_KODER)}\n")
        f.write(f"Region: {REGION_NAVN}\n")
        f.write(f"Lokale bedrifter: {len(lokale)}  |  Nasjonale med kontor: {len(nasjonale)}\n")
        f.write("─" * 65 + "\n\n")
        f.write(ki_prompt)

    print(f"  Prompt lagret til:  {filnavn}")
    print()
    print("  Neste steg:")
    print(f"  1. Åpne {filnavn}")
    print("  2. Kopier KI-prompten")
    print("  3. Lim inn i ChatGPT (med søk), Claude eller Perplexity")
    print("  4. Gå gjennom karrieresidene KI-en finner")
    print()


# ─────────────────────────────────────────────────────────────────────────────
# Kjør scriptet
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    main()
