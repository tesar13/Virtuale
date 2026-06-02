import os
import requests
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime

URL = "https://st-cdn001.akamaized.net/fortunagamesvirtuals/pl/1/season/3094110/h2h/276506/276503"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/137.0.0.0 Safari/537.36"
    )
}

PLIK_WYNIKOW = "wyniki.csv"


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

    home_team = (
        home_div.get_text(strip=True)
        if home_div
        else ""
    )

    away_div = right_col.find(
        "div",
        class_="hidden-xs-up visible-sm-up wrap"
    )

    away_team = (
        away_div.get_text(strip=True)
        if away_div
        else ""
    )

    time_divs = center_col.find_all(
        "div",
        class_="text-center",
        recursive=False
    )

    godzina = ""

    if len(time_divs) >= 1:
        godzina = time_divs[0].get_text(strip=True)

    wynik_div = center_col.find(
        "div",
        attrs={"aria-label": "Wynik"}
    )

    wynik = ""

    if wynik_div:
        nums = []

        for d in wynik_div.find_all("div", class_="inline-block"):
            txt = d.get_text(" ", strip=True)

            if txt.isdigit():
                nums.append(txt)

        if len(nums) >= 2:
            wynik = f"{nums[0]}:{nums[1]}"

    mecz = f"{home_team} - {away_team}"

    return {
        "Tura": tura,
        "Godzina": godzina,
        "Mecz": mecz,
        "Wynik": wynik
    }


def pobierz_dane():
    r = requests.get(URL, headers=HEADERS, timeout=30)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")

    rows = soup.select("tbody tr.cursor-pointer")

    dane = []

    for row in rows:
        rekord = parse_match_row(row)

        if rekord:
            rekord["Data"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            dane.append(rekord)

        if len(dane) >= 5:
            break

    return dane


def wczytaj_istniejace():
    if not os.path.exists(PLIK_WYNIKOW):
        return pd.DataFrame(
            columns=["Tura", "Godzina", "Mecz", "Wynik", "Data"]
        )

    return pd.read_csv(PLIK_WYNIKOW)


def main():
    nowe_dane = pobierz_dane()

    if not nowe_dane:
        print("Brak danych.")
        return

    df_stary = wczytaj_istniejace()

    pierwsze_10 = df_stary.head(10)

    nowe_bez_duplikatow = []

    for rekord in nowe_dane:

        duplikat = (
            (
                pierwsze_10["Tura"].astype(str) == str(rekord["Tura"])
            )
            &
            (
                pierwsze_10["Godzina"].astype(str) == str(rekord["Godzina"])
            )
            &
            (
                pierwsze_10["Mecz"].astype(str) == str(rekord["Mecz"])
            )
            &
            (
                pierwsze_10["Wynik"].astype(str) == str(rekord["Wynik"])
            )
        ).any()

        if not duplikat:
            nowe_bez_duplikatow.append(rekord)

    if not nowe_bez_duplikatow:
        print("Brak nowych rekordów.")
        return

    df_nowe = pd.DataFrame(
        nowe_bez_duplikatow,
        columns=["Tura", "Godzina", "Mecz", "Wynik", "Data"]
    )

    # NOWE REKORDY NA GÓRZE
    df_koncowy = pd.concat(
        [df_nowe, df_stary],
        ignore_index=True
    )

    df_koncowy.to_csv(
        PLIK_WYNIKOW,
        index=False,
        encoding="utf-8-sig"
    )

    print(f"Dodano {len(df_nowe)} nowych rekordów.")
    print(f"Łącznie rekordów: {len(df_koncowy)}")


if __name__ == "__main__":
    main()
