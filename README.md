# Jobbsøk med KI — finn arbeidsgivere via Brønnøysundregistrene

Et Python-script som henter relevante arbeidsgivere innen en valgt bransje og region
direkte fra [Brønnøysundregistrenes åpne API](https://data.brreg.no), og genererer
en ferdig KI-prompt du kan bruke i ChatGPT, Claude eller Perplexity (eller en helt annen modell) for å finne
karrieresidene deres. Det eneste kravet er at KI-modellen kan søke på nettet. 

---

## Tre måter å bruke dette på

### Alternativ 1 — Send GitHub-lenken til din KI-modell (enklest)

1. Be KI-modellen din besøke denne siden, lese scriptet og følge instruksjonene:
2. Last opp filen og skriv:

   > Gå til https://github.com/raymkri/jobbsok-ki, les scriptet og følg instruksjonene i det for å hjelpe meg finne arbeidsgivere.

Forutsetter at KI-modellen din har nettilgang.

---

### Alternativ 2 — Last ned og gi filen til din KI-modell

1. Last ned filen `jobbsok_brreg.py`
2. Last opp filen til din KI-modell og skriv:

 > Les instruksjonene øverst i dette scriptet og hjelp meg finne arbeidsgivere

Forutsetter at KI-modellen din har nettilgang.


### Alternativ 3 — Kjør scriptet selv (Python 3.8+)

Ingen installasjon av eksterne pakker nødvendig.

```bash
python3 jobbsok_brreg.py
```

Scriptet skriver ut en ferdig bedriftsliste og lagrer en KI-prompt til en `.txt`-fil
du kan lime inn i valgfritt KI-verktøy.

---

## Tilpass til din bransje og region
## NB! Hvis du vil ha flere NACE kode eksempler kan du se her: [NACE-koder.md](https://github.com/raymkri/jobbsok-ki/blob/main/NACE-koder.md)

Åpne `jobbsok_brreg.py` i et tekstredigeringsprogram og endre innstillingene øverst:

```python
# Hvilke NACE-koder vil du søke på?
NACE_KODER = [
    "71.121",   # Byggeteknisk konsulentvirksomhet
    "71.122",   # Annen teknisk konsulentvirksomhet
]

# Hvilken region? (de to første sifrene i kommunenummeret)
FYLKE_PREFIKS = "50"   # 50 = Trøndelag, 03 = Oslo, 11 = Rogaland ...
REGION_NAVN   = "Trøndelag"
```

### Fylkesnøkler

| Prefiks | Fylke |
|---------|-------|
| `03` | Oslo |
| `11` | Rogaland |
| `15` | Møre og Romsdal |
| `18` | Nordland |
| `31` | Østfold |
| `32` | Akershus |
| `33` | Buskerud |
| `34` | Innlandet |
| `39` | Vestfold |
| `40` | Telemark |
| `42` | Agder |
| `46` | Vestland |
| `50` | Trøndelag |
| `55` | Troms |
| `56` | Finnmark |

### Finn NACE-koder for din bransje

- Oversikt: [ssb.no/nace](https://www.ssb.no/nace)
- Søk på bedrift: [brreg.no/finn-foretak](https://www.brreg.no/finn-foretak/)

---

## Hva scriptet gjør

Scriptet kombinerer to kilder fra Brønnøysundregistrene:

**Del A — Lokalt registrerte bedrifter**
Finner selskaper med forretningsadresse i regionen.

**Del B — Nasjonale selskaper med lokale avdelingskontorer**
Søker etter registrerte avdelingskontorer (underenheter) med fysisk adresse i regionen.
Dette fanger opp store nasjonale selskaper som Multiconsult, Norconsult og Sweco
som er registrert sentralt, men har kontorer i regionen — og som ellers ville blitt oversett.

---

## Eksempel på output (Trøndelag, NACE 71.12)

```
LOKALE BEDRIFTER — registrert i Trøndelag (33 stk.)
  Sykehusbygg HF           Trondheim   219 ans
  Pro Invenia AS           Ranheim      50 ans
  Aas-Jakobsen Trondheim   Trondheim    39 ans
  ...

NASJONALE SELSKAPER MED KONTOR I TRØNDELAG (20 stk.)
  Norconsult Norge AS    Oppdal, Steinkjer, Trondheim, Verdal ...
  Multiconsult Norge AS  Steinkjer, Trondheim
  Sweco Norge AS         Steinkjer, Trondheim
  ...
```

---

## Krav

- Python 3.8 eller nyere
- Internettilgang (henter data fra brreg.no)
- Ingen eksterne pakker — kun standardbiblioteket

---

*Data hentet fra [Brønnøysundregistrenes åpne API](https://data.brreg.no) — lisensiert under [Norsk lisens for offentlige data (NLOD)](https://data.norge.no/nlod/no).*
