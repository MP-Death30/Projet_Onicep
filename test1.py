import csv
import time
from urllib.parse import urlencode, urljoin, quote, urlparse, parse_qs, urlunparse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager


# Dictionnaire des niveaux d'études → valeur d'URL attendue par Onisep
NIVEAU_MAPPING = {
    "": "",  # Aucun filtre
    "1": "après bac/Bac +1 à +2",
    "2": "après bac/Bac +1 à +2",
    "3": "après bac/Bac +3",
    "4": "après bac/Bac +4 à +5",
    "5": "après bac/Bac +4 à +5",
    "6": "après bac/Bac +6 et +",
    "7": "après bac/Bac +6 et +",
}

def input_non_empty(prompt):
    while True:
        value = input(prompt).strip()
        if value:
            return value
        print("Ce champ est obligatoire.")


def create_driver():
    options = webdriver.ChromeOptions()
    # options.add_argument("--headless=new")  # facultatif pour debug
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)


def encoder_text_personnalise(text):
    # Garde les accents, encode seulement espace et &
    return text.replace(" ", "%20").replace("&", "%26")


def construire_url(mot_cle, niveau_code):
    base_url = "https://www.onisep.fr/recherche"
    
    niveau_label = NIVEAU_MAPPING.get(niveau_code.strip(), "")
    if not niveau_label:
        niveau_label = "après bac"

    niveau_encoded = quote(niveau_label)

    query_params = {
        "context": "formation",
    }
    query_string = urlencode(query_params)

    mot_cle_encode = encoder_text_personnalise(mot_cle)
    niveau_param = f"sf[niveau_enseignement_mid][]={niveau_encoded}"

    url = f"{base_url}?{query_string}&{niveau_param}&text={mot_cle_encode}"
    return url



def rechercher_formations(url, max_results=20):
    base_url = "https://www.onisep.fr"
    driver = create_driver()
    wait = WebDriverWait(driver, 10)

    formations = []
    page = 1

    try:
        while len(formations) < max_results and len(formations) < 50:
            paged_url = url+"&page="+str(page)
            print(f"\n🔄 Chargement page {page} : {paged_url}")
            driver.get(paged_url)
            time.sleep(2)

            rows = driver.find_elements(By.CSS_SELECTOR, "tbody tr")
            if not rows:
                break  # plus de résultats

            for row in rows:
                try:
                    a_tag = row.find_element(By.TAG_NAME, "a")
                    title = a_tag.text.strip()
                    link = urljoin(base_url, a_tag.get_attribute("href"))
                    formations.append({
                        "titre": title,
                        "lien": link
                    })
                    if len(formations) >= max_results or len(formations) >= 50:
                        break
                except Exception as e:
                    print(f"⚠️ Erreur ligne : {e}")
                    continue
            page += 1

    except Exception as e:
        print(f"❌ Erreur globale : {e}")

    driver.quit()
    return formations






def renseigner_localisation(driver, localisation):
    try:
        # Attendre que le champ de localisation soit visible
        champ = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='search-ui-geo-city']"))
        )

        # Cliquer pour s'assurer qu'il est actif
        champ.click()
        time.sleep(0.5)

        # Effacer tout contenu existant
        champ.clear()
        time.sleep(0.2)

        # Envoyer la localisation
        champ.send_keys(localisation)
        time.sleep(1.5)  # attendre que la suggestion s'affiche (important si autocomplétion)

        # Valider par Entrée si nécessaire
        champ.send_keys(Keys.TAB)
        time.sleep(1.5)
        champ.send_keys(Keys.RETURN)

        print(f"📍 Localisation renseignée : {localisation}")
    except Exception as e:
        print(f"❌ Erreur lors de la saisie de la localisation : {e}")





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

    print("\nChoisis un niveau d’étude :")
    print("  (laisser vide pour aucun filtre)")
    print("  1 → Bac +1 à +2")
    print("  3 → Bac +3")
    print("  4 → Bac +4 à +5")
    print("  6 → Bac +6 et +")
    niveau = input("Ton choix (1, 3, 4, 6 ou vide) : ").strip()
    localisation = input("Entrez une ville ou une région (facultatif) : ").strip()
    max_results_str = input("Nombre max de résultats (défaut = 10, max = 50) : ").strip()
    max_results = int(max_results_str) if max_results_str.isdigit() else 10
    max_results = min(max_results, 50)

    search_url = construire_url(mot_cle, niveau)
    formations = rechercher_formations(search_url, max_results=max_results)

    print(f"\n🔍 {len(formations)} formations trouvées :\n")
    for f in formations:
        print(f"{f['titre']} → {f['lien']}")

    export_csv(formations)


if __name__ == "__main__":
    main()






