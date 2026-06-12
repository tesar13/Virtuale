import base64
from io import StringIO
from datetime import datetime

import pandas as pd
import requests
from bs4 import BeautifulSoup
print("WERSJA API GITHUB 2026")
URL = "https://st-cdn001.akamaized.net/fortunagamesvirtuals/pl/1/season/3099557/h2h/276506/276502"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/137.0.0.0 Safari/537.36"
    )
}

REPO_OWNER = "tesar13"
REPO_NAME = "Virtuale"
CSV_PATH = "wyniki.csv"


def parse_match_row(row):
    cells = row.find_all("td", recursive=False)

    if len(cells) < 2:
        return None

    tura = ""

    first_td = cells[0]
    divs = first_td.find_all("div")

    if len(divs) >= 2:
        tura = divs[1].get_text(strip=True)

    match_td = cells[1]

    cols = match_td.find_all(
        "div",
        class_="col-xs-4",
        recursive=True
    )

    if len(cols) < 3:
        return None

    left_col = cols[0]
    center_col = cols[1]
    right_col = cols[2]

    home_div = left_col.find(
        "div",
        class_="hidden-xs-up visible-sm-up wrap"
    )

    away_div = right_col.find(
        "div",
        class_="hidden-xs-up visible-sm-up wrap"
    )

    home_team = home_div.get_text(strip=True) if home_div else ""
    away_team = away_div.get_text(strip=True) if away_div else ""

    godzina = ""

    time_divs = center_col.find_all(
        "div",
        class_="text-center",
        recursive=False
    )

    if len(time_divs) >= 1:
        godzina = time_divs[0].get_text(strip=True)

    wynik = ""

    wynik_div = center_col.find(
        "div",
        attrs={"aria-label": "Wynik"}
    )

    if wynik_div:
        nums = []

        for d in wynik_div.find_all("div", class_="inline-block"):
            txt = d.get_text(" ", strip=True)

            if txt.isdigit():
                nums.append(txt)

        if len(nums) >= 2:
            wynik = f"{nums[0]}:{nums[1]}"

    return {
        "Tura": tura,
        "Godzina": godzina,
        "Mecz": f"{home_team} - {away_team}",
        "Wynik": wynik
    }


def pobierz_dane():
    response = requests.get(
        URL,
        headers=HEADERS,
        timeout=30
    )

    response.raise_for_status()

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    rows = soup.select("tbody tr.cursor-pointer")

    dane = []

    for row in rows:
        rekord = parse_match_row(row)

        if rekord:
            rekord["Data"] = datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            dane.append(rekord)

        if len(dane) >= 5:
            break

    return dane


def github_headers():
    token = os.getenv("GITHUB_TOKEN")

    if not token:
        raise Exception(
            "Brak zmiennej GITHUB_TOKEN na Renderze."
        )

    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json"
    }


def pobierz_csv_z_github():
    url = (
        f"https://api.github.com/repos/"
        f"{REPO_OWNER}/{REPO_NAME}/contents/{CSV_PATH}"
    )

    r = requests.get(
        url,
        headers=github_headers()
    )

    if r.status_code == 404:
        pusty = pd.DataFrame(
            columns=[
                "Tura",
                "Godzina",
                "Mecz",
                "Wynik",
                "Data"
            ]
        )

        return pusty, None

    r.raise_for_status()

    data = r.json()

    content = base64.b64decode(
        data["content"]
    ).decode("utf-8-sig")

    df = pd.read_csv(StringIO(content))

    return df, data["sha"]


def zapisz_csv_na_github(df, sha):
    csv_text = df.to_csv(
        index=False
    )

    content = base64.b64encode(
        csv_text.encode("utf-8")
    ).decode()

    url = (
        f"https://api.github.com/repos/"
        f"{REPO_OWNER}/{REPO_NAME}/contents/{CSV_PATH}"
    )

    payload = {
        "message": (
            f"Aktualizacja wynikow "
            f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        ),
        "content": content
    }

    if sha:
        payload["sha"] = sha

    r = requests.put(
        url,
        headers=github_headers(),
        json=payload
    )

    r.raise_for_status()

    print("Plik zapisany na GitHub.")


def main():
    nowe_dane = pobierz_dane()

    if not nowe_dane:
        print("Brak danych.")
        return

    df_stary, sha = pobierz_csv_z_github()

    pierwsze_10 = df_stary.head(10)

    nowe_bez_duplikatow = []

    for rekord in nowe_dane:

        if len(df_stary) == 0:
            nowe_bez_duplikatow.append(rekord)
            continue

        duplikat = (
            (
                pierwsze_10["Tura"].astype(str)
                == str(rekord["Tura"])
            )
            &
            (
                pierwsze_10["Godzina"].astype(str)
                == str(rekord["Godzina"])
            )
            &
            (
                pierwsze_10["Mecz"].astype(str)
                == str(rekord["Mecz"])
            )
            &
            (
                pierwsze_10["Wynik"].astype(str)
                == str(rekord["Wynik"])
            )
        ).any()

        if not duplikat:
            nowe_bez_duplikatow.append(rekord)

    if not nowe_bez_duplikatow:
        print("Brak nowych rekordów.")
        return

    df_nowe = pd.DataFrame(
        nowe_bez_duplikatow
    )

    df_koncowy = pd.concat(
        [df_nowe, df_stary],
        ignore_index=True
    )

    zapisz_csv_na_github(
        df_koncowy,
        sha
    )

    print(
        f"Dodano {len(df_nowe)} nowych rekordów."
    )

    print(
        f"Łącznie rekordów: {len(df_koncowy)}"
    )


if __name__ == "__main__":
    import os
    main()
