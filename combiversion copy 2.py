import csv
import time
import re
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
    "3": "après bac/Bac +3",
    "4": "après bac/Bac +4 à +5",
    "5": "après bac/Bac +4 à +5",
    "6": "après bac/Bac +6 et +"
}

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
        if localisation.isdigit():
            if len(localisation) != 5:
                print("Si vous entrez un code postal, il doit contenir exactement 5 chiffres.")
                continue
        return localisation


def create_driver():
    options = webdriver.ChromeOptions()
    #options.add_argument("--headless=new")
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

    # Remplacer l'espace normal par espace insécable uniquement dans niveau_label
    niveau_label = niveau_label.replace(" à +", " à\u00A0+")

    niveau_encoded = quote(niveau_label)

    query_params = {
        "context": "formation",
    }
    query_string = urlencode(query_params)

    mot_cle_encode = encoder_text_personnalise(mot_cle)
    niveau_param = f"sf[niveau_enseignement_mid][]={niveau_encoded}"

    url = f"{base_url}?{query_string}&{niveau_param}&text={mot_cle_encode}"
    return url


# =================== Première page de recherche ====================
def rechercher_formations(driver, url, max_results=20):
    base_url = "https://www.onisep.fr"
    formations = []
    page = 1
    
    wait = WebDriverWait(driver, 10)
    
    # Charger la première page pour récupérer le total
    driver.get(url + "&page=1")
    
    try:
        total_count_elem = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "span.search-ui-total-count")))
        total_count = int(total_count_elem.text.strip())
        print(f"Nombre total de résultats trouvés : {total_count}")
    except Exception as e:
        print(f"❌ Impossible de récupérer le nombre total de résultats : {e}")
        total_count = max_results  # fallback

    total_to_fetch = min(max_results, total_count)

    while len(formations) < total_to_fetch:
        if page > 1:
            paged_url = url + "&page=" + str(page)
            print(f"\n🔄 Chargement page {page} : {paged_url}")
            driver.get(paged_url)
            time.sleep(2)

        try:
            wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "tbody tr")))
            rows = driver.find_elements(By.CSS_SELECTOR, "tbody tr")
        except Exception as e:
            print(f"❌ Erreur lors de la récupération des résultats : {e}")
            break

        if len(rows) == 0:
            print("🚫 Aucune formation trouvée sur cette page, arrêt de la recherche.")
            break

        for row in rows:
            try:
                a_tag = row.find_element(By.TAG_NAME, "a")
                title = a_tag.text.strip()
                link = urljoin(base_url, a_tag.get_attribute("href"))

                if any(f['lien'] == link for f in formations):
                    continue

                formations.append({"titre": title, "lien": link})
                if len(formations) >= total_to_fetch:
                    break
            except Exception as e:
                print(f"⚠️ Erreur ligne : {e}")
                continue

        page += 1

    return formations


# ======= Sortie Nom formation + URL =========


# ======= Gestion de la localisation ======

def renseigner_localisation(driver, localisation):
    wait = WebDriverWait(driver, 10)
    
    if not localisation:
        return
        
    try:
        champ = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[name='search-ui-geo-city']")))
        driver.execute_script("arguments[0].scrollIntoView(true);", champ)
        time.sleep(0.5)
        try:
            champ.click()
        except:
            # fallback click JS si le clic normal échoue
            driver.execute_script("arguments[0].click();", champ)
        champ.clear()
        time.sleep(0.5)
        champ.send_keys(localisation)
        print(f"📍 Localisation saisie : {localisation}")
        time.sleep(1.5)

        try:
            # Attendre la première suggestion de la liste
            first_suggestion = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, ".autocomplete-list li a"))
            )
            first_suggestion.click()
            print("✅ Première suggestion cliquée avec succès.")
        except Exception as e:
            print(f"⚠️ Aucune suggestion cliquable trouvée, tentative avec ENTER")
            champ.send_keys(Keys.ENTER)

        time.sleep(2)
        print("✅ Touche TAB et ENTER envoyées.")
    except Exception as e:
        print(f"❌ Erreur lors de la saisie de la localisation : {e}")


# ======== Fin gestion localisation =========





# ======= Récupérer l'URL de la formation + extraction des infos complémentaire ================
def formations(driver, url, localisation):
    wait = WebDriverWait(driver, 20)
    driver.get(url)
    time.sleep(0.5)

    # Initialiser le résultat avec des valeurs par défaut
    result = {
        "durée": "N/A",
        "nature": "N/A",
        "type": "N/A",
        "établissements_conseillés": "N/A"
    }

    # === Remplir la localisation ===
    if localisation:
        renseigner_localisation(driver, localisation)
        time.sleep(3)

    # === Extraction des informations ===
    # Extraire la durée avec plusieurs sélecteurs
        print("🔍 Recherche de la durée...")
        duree_selectors = [
            "//div[contains(text(),'Durée de la formation')]/strong",
            "//div[contains(text(),'Durée')]/following-sibling::*/strong",
            "//strong[contains(text(),'an') or contains(text(),'mois') or contains(text(),'semestre')]",
            "//*[contains(text(),'Durée')]/..//strong",
            "//*[contains(@class,'duration')]",
        ]
        
        for selector in duree_selectors:
            try:
                if selector.startswith("//"):
                    duree_elem = driver.find_element(By.XPATH, selector)
                else:
                    duree_elem = driver.find_element(By.CSS_SELECTOR, selector)
                result["durée"] = duree_elem.text.strip()
                print(f"✅ Durée trouvée : {result['durée']}")
                break
            except:
                continue

        # Extraire la nature avec plusieurs sélecteurs
        print("🔍 Recherche de la nature...")
        nature_selectors = [
            "//div[contains(@class, 'tag')][.//span[contains(text(),'Nature de la formation')]]//li//strong",
            "//span[contains(text(),'Nature')]/following-sibling::strong",
            "//*[contains(text(),'Nature')]/..//strong",
            "//div[contains(text(),'Nature')]//strong",
        ]
        
        for selector in nature_selectors:
            try:
                nature_elem = driver.find_element(By.XPATH, selector)
                result["nature"] = nature_elem.text.strip()
                print(f"✅ Nature trouvée : {result['nature']}")
                break
            except:
                continue

        # Extraire le type de formation
        print("🔍 Recherche du type...")
        type_selectors = [
            "//div[contains(@class, 'tag') and .//text()[contains(.,'Type de formation')]]/span/strong",
            "//span[contains(text(),'Type')]/following-sibling::strong",
            "//*[contains(text(),'Type')]/..//strong",
            "//div[contains(text(),'Type')]//strong",
        ]
        
        for selector in type_selectors:
            try:
                type_elem = driver.find_element(By.XPATH, selector)
                result["type"] = type_elem.text.strip()
                print(f"✅ Type trouvé : {result['type']}")
                break
            except:
                continue

        # Extraire les établissements
        print("🔍 Recherche des établissements...")
        etablissements = []
        table_selectors = [
            "table tbody tr",
            ".table tbody tr",
            "tbody tr",
            "[data-label] tr",
            ".establishment-list tr"
        ]
        
        for table_selector in table_selectors:
            try:
                time.sleep(2)
                table_rows = driver.find_elements(By.CSS_SELECTOR, table_selector)
                
                if table_rows:
                    print(f"🏫 {len(table_rows)} ligne(s) d'établissement(s) trouvée(s) avec sélecteur : {table_selector}")
                    
                    for i, tr in enumerate(table_rows, 1):
                        try:
                            # Essayer différentes façons d'extraire les infos
                            nom_elem = tr.find_element(By.TAG_NAME, "a")
                            nom = nom_elem.text.strip()
                            
                            # Essayer différents sélecteurs pour la ville
                            ville = "N/A"
                            ville_selectors = [
                                'td[data-label="Commune"]',
                                'td[data-label="Ville"]',
                                '.commune',
                                '.ville'
                            ]
                            
                            for ville_sel in ville_selectors:
                                try:
                                    ville_elem = tr.find_element(By.CSS_SELECTOR, ville_sel)
                                    ville = ville_elem.text.strip()
                                    break
                                except:
                                    continue
                            
                            # Essayer différents sélecteurs pour le code postal
                            code_postal = "N/A"
                            cp_selectors = [
                                'td[data-label="Code postal"]',
                                'td[data-label="CP"]',
                                '.code-postal',
                                '.cp'
                            ]
                            
                            for cp_sel in cp_selectors:
                                try:
                                    cp_elem = tr.find_element(By.CSS_SELECTOR, cp_sel)
                                    code_postal = cp_elem.text.strip()
                                    break
                                except:
                                    continue
                            
                            if ville != "N/A" and code_postal != "N/A":
                                etablissement_info = f"{nom} ({ville}, {code_postal})"
                            else:
                                etablissement_info = nom
                                
                            etablissements.append(etablissement_info)
                            print(f"   📍 Établissement {i}: {etablissement_info}")
                            
                        except Exception as e:
                            print(f"   ⚠️ Erreur établissement {i}: {e}")
                            continue
                    
                    break  # Sortir de la boucle des sélecteurs si on a trouvé des données
                    
            except Exception as e:
                print(f"⚠️ Erreur avec sélecteur {table_selector}: {e}")
                continue
    
    result["établissements_conseillés"] = " | ".join(etablissements) if etablissements else "N/A"

    return result




def export_csv(data, filename):
    caracteres_interdits = r'[\\/*?:"<>|]'
    filename = re.sub(caracteres_interdits, '', filename).replace(" ", "_")

    # Supprimer l'extension si déjà présente (.csv insensible à la casse)
    if filename.lower().endswith(".csv"):
        filename = filename[:-4]

    # Supprimer tous les points restants
    filename = filename.replace(".", "")

    # Ajouter proprement l'extension .csv
    filename = filename + ".csv"

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

    print("📍 Pour une **ville**, indique le code postal** (ex : Nîmes = 30000).")
    print("   Pour un **département** ou une **région**, indique son **nom complet** (ex : Gard, Occitanie).")
    localisation = input_localisation()

    max_results_str = input("Nombre max de résultats (défaut = 10, max = 50) : ").strip()
    max_results = int(max_results_str) if max_results_str.isdigit() else 10
    max_results = min(max_results, 50)

    nom_fichier = input("Nom du fichier en sortie : ").strip()

    driver = create_driver()

    try:
        search_url = construire_url(mot_cle, niveau)
        src_formations = rechercher_formations(driver, search_url, max_results=max_results)

        full_data = []
        for formation in src_formations:
            print(f"\n➡️  Traitement de : {formation['titre']}")
            infos = formations(driver, formation['lien'], localisation)
            full_data.append({**formation, **infos})

        export_csv(full_data,nom_fichier)
    finally:
        driver.quit()

if __name__ == "__main__":
    main()