import csv
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from urllib.parse import urljoin


def input_non_empty(prompt):
    while True:
        value = input(prompt).strip()
        if value:
            return value
        print("Ce champ est obligatoire.")


def create_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")  # Pour afficher le navigateur, commente cette ligne
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)


def rechercher_formations(mot_cle, niveau="après bac/Bac +3", max_results=20):
    base_url = "https://www.onisep.fr"
    query = mot_cle.replace(" ", "%20")
    niveau_param = niveau.replace(" ", "%20").replace("+", "%2B")
    search_url = f"https://www.onisep.fr/recherche?context=formation&sf[niveau_enseignement_mid][]={niveau_param}&text={query}"

    driver = create_driver()
    wait = WebDriverWait(driver, 10)

    driver.get(search_url)
    time.sleep(5)

    formations = []

    try:
        rows = driver.find_elements(By.CSS_SELECTOR, "tbody tr")
        for row in rows:
            try:
                a_tag = row.find_element(By.TAG_NAME, "a")
                title = a_tag.text.strip()
                link = urljoin(base_url, a_tag.get_attribute("href"))
                formations.append({
                    "titre": title,
                    "lien": link
                })
                if len(formations) >= max_results:
                    break
            except Exception as e:
                print(f"Erreur de lecture ligne : {e}")
                continue
    except Exception as e:
        print(f"Erreur globale : {e}")

    driver.quit()
    return formations


def export_csv(data, filename="resultats_formations_onisep.csv"):
    if not data:
        print("Aucune donnée à exporter.")
        return
    with open(filename, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=data[0].keys(), delimiter=';')
        writer.writeheader()
        writer.writerows(data)
    print(f"\n✅ Données exportées dans : {filename}")


def main():
    print("=== Recherche de formations sur Onisep.fr ===")
    mot_cle = input_non_empty("Mot-clé de recherche (ex: mathématiques) : ")
    max_results_str = input("Nombre max de résultats (défaut = 10) : ").strip()
    max_results = int(max_results_str) if max_results_str.isdigit() else 10

    formations = rechercher_formations(mot_cle, max_results=max_results)

    print(f"\n🔎 {len(formations)} formations trouvées :\n")
    for f in formations:
        print(f"{f['titre']} → {f['lien']}")

    export_csv(formations)


if __name__ == "__main__":
    main()
 
