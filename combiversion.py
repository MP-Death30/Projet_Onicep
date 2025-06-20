import csv
import time
import re
from urllib.parse import urlencode, urljoin, quote
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# ================================
# Niveaux d'études Onisep (mapping code → libellé)
# ================================
NIVEAU_MAPPING = {
    "": "",
    "1": "après bac/Bac +1 à +2",
    "3": "après bac/Bac +3",
    "4": "après bac/Bac +4 à +5",
    "5": "après bac/Bac +4 à +5",
    "6": "après bac/Bac +6 et +"
}

# ================================
# Fonctions utilitaires simples
# ================================
def input_non_empty(prompt):
    while True:
        value = input(prompt).strip()
        if value:
            return value
        print("Ce champ est obligatoire.")

def input_localisation():
    while True:
        localisation = input("Entrez une localisation (ville ou code postal) : ").strip()
        if not localisation:
            print("Ce champ est obligatoire.")
            continue
        if localisation.isdigit() and len(localisation) != 5:
            print("Si vous entrez un code postal, il doit contenir exactement 5 chiffres.")
            continue
        return localisation

def create_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def encoder_text_personnalise(text):
    return text.replace(" ", "%20").replace("&", "%26")

def construire_url(mot_cle, niveau_code):
    base_url = "https://www.onisep.fr/recherche"
    niveau_label = NIVEAU_MAPPING.get(niveau_code.strip(), "après bac")
    niveau_label = niveau_label.replace(" à +", " à\u00A0+")
    niveau_encoded = quote(niveau_label)
    query = urlencode({"context": "formation"})
    url = f"{base_url}?{query}&sf[niveau_enseignement_mid][]={niveau_encoded}&text={encoder_text_personnalise(mot_cle)}"
    return url

# ================================
# Recherche de formations sur les pages Onisep
# ================================
def rechercher_formations(driver, url, max_results=20):
    formations = []
    page = 1
    wait = WebDriverWait(driver, 10)

    driver.get(url + "&page=1")
    try:
        total_count_elem = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "span.search-ui-total-count")))
        total_count = int(total_count_elem.text.strip())
    except:
        total_count = max_results  # fallback si élément non trouvé

    total_to_fetch = min(max_results, total_count)

    while len(formations) < total_to_fetch:
        if page > 1:
            driver.get(url + "&page=" + str(page))
            time.sleep(2)

        try:
            wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "tbody tr")))
            rows = driver.find_elements(By.CSS_SELECTOR, "tbody tr")
        except:
            break

        if not rows:
            break

        for row in rows:
            try:
                a_tag = row.find_element(By.TAG_NAME, "a")
                title = a_tag.text.strip()
                link = urljoin("https://www.onisep.fr", a_tag.get_attribute("href"))
                if any(f['lien'] == link for f in formations):
                    continue
                formations.append({"titre": title, "lien": link})
                if len(formations) >= total_to_fetch:
                    break
            except:
                continue

        page += 1

    return formations

# ================================
# Saisie automatique de la localisation dans Onisep
# ================================
def renseigner_localisation(driver, localisation):
    if not localisation:
        return
        
    try:
        print(f"🔍 Tentative de filtrage par localisation : {localisation}")
        wait = WebDriverWait(driver, 10)
        
        # Plusieurs sélecteurs possibles pour le champ de localisation
        selectors = [
            "input.geo-city",
            "input[name='search-ui-geo-city']",
            "input[placeholder*='ville']",
            "input[placeholder*='localisation']"
        ]
        
        input_geo = None
        for selector in selectors:
            try:
                input_geo = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                print(f"✅ Champ de localisation trouvé avec : {selector}")
                break
            except:
                continue
                
        if not input_geo:
            print("⚠️ Champ de localisation non trouvé, pas de filtrage")
            return
            
        # Remplir le champ
        input_geo.clear()
        time.sleep(1)
        input_geo.send_keys(localisation)
        time.sleep(2)
        
        # Chercher la liste d'autocomplétion
        try:
            driver.execute_script("arguments[0].scrollIntoView(true);", input_geo)
            autocomplete = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.autocomplete-list-wrapper a")))
            time.sleep(1)
            autocomplete.click()
            print("✅ Localisation sélectionnée via autocomplétion")
        except:
            # Si pas d'autocomplétion, valider avec Enter
            input_geo.send_keys(Keys.RETURN)
            print("✅ Localisation validée avec Enter")

        time.sleep(3)  # Attendre le filtrage
        
    except Exception as e:
        print(f"❌ Erreur lors du filtrage par localisation : {e}")

# ================================
# Extraction des infos complémentaires sur une formation
# ================================
def formations(driver, url, localisation):
    wait = WebDriverWait(driver, 20)
    driver.get(url)
    time.sleep(0.5)

    result = {
        "durée": "N/A",
        "nature": "N/A",
        "type": "N/A",
        "établissements_conseillés": "N/A"
    }

    if localisation:
        renseigner_localisation(driver, localisation)
        time.sleep(3)

    # Sélecteurs d'extraction
    def extraire_info(selectors, xpath=True):
        for sel in selectors:
            try:
                elem = driver.find_element(By.XPATH if xpath else By.CSS_SELECTOR, sel)
                return elem.text.strip()
            except:
                continue
        return "N/A"

    result["durée"] = extraire_info([
        "//div[contains(text(),'Durée de la formation')]/strong",
        "//div[contains(text(),'Durée')]/following-sibling::*/strong",
        "//strong[contains(text(),'an') or contains(text(),'mois') or contains(text(),'semestre')]",
        "//*[contains(text(),'Durée')]/..//strong",
        "//*[contains(@class,'duration')]"
    ])

    result["nature"] = extraire_info([
        "//div[contains(@class, 'tag')][.//span[contains(text(),'Nature de la formation')]]//li//strong",
        "//span[contains(text(),'Nature')]/following-sibling::strong",
        "//*[contains(text(),'Nature')]/..//strong",
        "//div[contains(text(),'Nature')]//strong"
    ])

    result["type"] = extraire_info([
        "//div[contains(@class, 'tag') and .//text()[contains(.,'Type de formation')]]/span/strong",
        "//span[contains(text(),'Type')]/following-sibling::strong",
        "//*[contains(text(),'Type')]/..//strong",
        "//div[contains(text(),'Type')]//strong"
    ])

    # Extraction des établissements
    etablissements = []
    table_selectors = ["table tbody tr", ".table tbody tr", "tbody tr", "[data-label] tr", ".establishment-list tr"]

    for table_selector in table_selectors:
        try:
            time.sleep(2)
            rows = driver.find_elements(By.CSS_SELECTOR, table_selector)
            if not rows:
                continue

            for tr in rows:
                try:
                    nom = tr.find_element(By.TAG_NAME, "a").text.strip()

                    ville = "N/A"
                    for sel in ['td[data-label="Commune"]', 'td[data-label="Ville"]', '.commune', '.ville']:
                        try:
                            ville = tr.find_element(By.CSS_SELECTOR, sel).text.strip()
                            break
                        except:
                            continue

                    code_postal = "N/A"
                    for sel in ['td[data-label="Code postal"]', 'td[data-label="CP"]', '.code-postal', '.cp']:
                        try:
                            code_postal = tr.find_element(By.CSS_SELECTOR, sel).text.strip()
                            break
                        except:
                            continue

                    info = f"{nom} ({ville}, {code_postal})" if ville != "N/A" and code_postal != "N/A" else nom
                    etablissements.append(info)
                except:
                    continue
            break
        except:
            continue

    result["établissements_conseillés"] = " | ".join(etablissements) if etablissements else "N/A"
    return result

# ================================
# Export vers fichier CSV (nom nettoyé)
# ================================
def export_csv(data, filename):
    if not filename:
        filename="resultats_formations_onisep.csv"
    
    else:
        caracteres_interdits = r'[\\/*?:"<>|]'
        filename = re.sub(caracteres_interdits, '', filename).replace(" ", "_")

        if filename.lower().endswith(".csv"):
            filename = filename[:-4]
            
        filename = filename.replace(".", "") + ".csv"

    if not data:
        print("Aucune donnée à exporter.")
        return

    with open(filename, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=data[0].keys(), delimiter=';')
        writer.writeheader()
        writer.writerows(data)

    print(f"\n✅ Données exportées dans : {filename}")

# ================================
# Programme principal
# ================================
def main():
    print("=== Recherche de formations sur Onisep.fr ===")

    # Mot-clé
    mot_cle = input_non_empty("Mot-clé de recherche (ex: mathématiques) : ")

    # Niveau d'étude
    print("\nChoisis un niveau d'étude :")
    print("  (laisser vide pour aucun filtre)")
    print("  1 → Bac +1 à +2")
    print("  3 → Bac +3")
    print("  4 → Bac +4 à +5")
    print("  6 → Bac +6 et +")
    niveau = input_non_empty("Ton choix (1, 3, 4, 6 ou vide) : ").strip()

    # Zone géographique
    print("📍 Pour une **ville**, indique le code postal** (ex : Nîmes = 30000).")
    print("   Pour un **département** ou une **région**, indique son **nom complet** (ex : Gard, Occitanie).")
    localisation = input_localisation()

    # Nombre de résultats attendus
    max_results_str = input_non_empty("Nombre max de résultats (défaut = 10, max = 50) : ").strip()
    max_results = int(max_results_str) if max_results_str.isdigit() else 10
    max_results = min(max_results, 50)

    # Nom du fichier
    nom_fichier = input_non_empty("Nom du fichier en sortie : ").strip()

    driver = create_driver()

    # Lancement des diverses fonctions
    try:
        search_url = construire_url(mot_cle, niveau)
        src_formations = rechercher_formations(driver, search_url, max_results=max_results)

        full_data = []
        for formation in src_formations:
            infos = formations(driver, formation['lien'], localisation)
            full_data.append({**formation, **infos})

        export_csv(full_data, nom_fichier)
    finally:
        driver.quit()

if __name__ == "__main__":
    main()