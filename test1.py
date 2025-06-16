import csv
import time
from urllib.parse import urlencode, urljoin, quote
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
    "5": "après bac/Bac +4 à +5",
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
    options.add_argument("--headless=new")  # Commenté pour debug
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
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

    formations = []
    page = 1

    try:
        while len(formations) < max_results and len(formations) < 50:
            paged_url = url+"&page="+str(page)
            print(f"\n🔄 Chargement page {page} : {paged_url}")
            driver.get(paged_url)
            time.sleep(3)

            # Rechercher les lignes du tableau
            rows = driver.find_elements(By.CSS_SELECTOR, "tbody tr")
            print(f"📊 {len(rows)} lignes trouvées sur la page {page}")
            
            if not rows:
                print("❌ Aucune ligne trouvée, fin de la recherche")
                break

            page_count = 0
            for row in rows:
                try:
                    a_tag = row.find_element(By.TAG_NAME, "a")
                    title = a_tag.text.strip()
                    link = urljoin(base_url, a_tag.get_attribute("href"))
                    
                    formations.append({
                        "titre": title,
                        "lien": link
                    })
                    page_count += 1
                    print(f"   ✅ Formation {len(formations)}: {title}")
                    
                    if len(formations) >= max_results or len(formations) >= 50:
                        break
                        
                except Exception as e:
                    print(f"⚠️ Erreur ligne : {e}")
                    continue
                    
            if page_count == 0:
                print("❌ Aucune formation trouvée sur cette page, arrêt")
                break
                
            page += 1

    except Exception as e:
        print(f"❌ Erreur globale lors de la recherche : {e}")
    finally:
        driver.quit()

    return formations


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
            autocomplete = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.autocomplete-list-wrapper")))
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


def extraire_infos_formation(driver, url, localisation):
    """Extrait les informations détaillées d'une formation"""
    # Initialiser le résultat avec des valeurs par défaut
    result = {
        "durée": "N/A",
        "nature": "N/A",
        "type": "N/A",
        "établissements_conseillés": "N/A"
    }
    
    try:
        print(f"🔍 Analyse de la formation : {url}")
        driver.get(url)
        time.sleep(5)  # Augmenter le délai d'attente

        # Renseigner la localisation si fournie
        if localisation:
            renseigner_localisation(driver, localisation)
            time.sleep(3)

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
        print(f"✅ {len(etablissements)} établissement(s) récupéré(s)")
        
        print(f"📋 Résumé extraction :")
        print(f"   - Durée: {result['durée']}")
        print(f"   - Nature: {result['nature']}")
        print(f"   - Type: {result['type']}")
        print(f"   - Établissements: {len(etablissements)} trouvé(s)")
        
        return result

    except Exception as e:
        print(f"❌ Erreur lors de l'extraction des infos : {e}")
        print(f"❌ Type d'erreur : {type(e).__name__}")
        return result  # Retourner le résultat avec les valeurs par défaut


def export_csv(data, filename="formations_onisep.csv"):
    if not data:
        print("❌ Aucune donnée à exporter.")
        return
    
    print(f"\n📊 Préparation de l'export de {len(data)} formation(s)...")
    
    # Debugging : afficher les données avant export
    print("🔍 DEBUG - Aperçu des données :")
    for i, item in enumerate(data[:2]):  # Afficher les 2 premiers éléments
        print(f"   Formation {i+1}: {item}")
    
    # Vérifier que les données ont bien des clés
    if not data or not data[0]:
        print("❌ Erreur : les données sont vides")
        return
        
    # S'assurer que toutes les formations ont les mêmes clés
    all_keys = set()
    for formation in data:
        if isinstance(formation, dict):
            all_keys.update(formation.keys())
    
    if not all_keys:
        print("❌ Erreur : aucune clé trouvée dans les données")
        return
    
    # Standardiser les données pour avoir toutes les clés
    standardized_data = []
    for formation in data:
        if isinstance(formation, dict):
            standardized_formation = {}
            for key in all_keys:
                standardized_formation[key] = formation.get(key, "N/A")
            standardized_data.append(standardized_formation)
    
    try:
        # Créer le fichier CSV
        with open(filename, mode="w", newline="", encoding="utf-8") as file:
            fieldnames = list(all_keys)
            print(f"📝 Colonnes : {fieldnames}")
            
            writer = csv.DictWriter(file, fieldnames=fieldnames, delimiter=';')
            writer.writeheader()
            
            for i, row in enumerate(standardized_data, 1):
                writer.writerow(row)
                print(f"   ✅ Ligne {i} écrite : {row.get('titre', 'N/A')}")
            
        print(f"\n🎉 Export réussi ! Fichier : {filename}")
        print(f"📁 Nombre de formations exportées : {len(standardized_data)}")
        
        # Vérifier que le fichier a été créé
        import os
        if os.path.exists(filename):
            size = os.path.getsize(filename)
            print(f"📊 Taille du fichier : {size} octets")
        else:
            print("❌ Le fichier n'a pas été créé")
        
    except Exception as e:
        print(f"❌ Erreur lors de l'export : {e}")
        print(f"Type d'erreur : {type(e).__name__}")
        import traceback
        traceback.print_exc()


def main():
    print("=== Recherche de formations sur Onisep.fr ===")
    
    # Saisie des paramètres
    mot_cle = input_non_empty("Mot-clé de recherche (ex: mathématiques) : ")

    print("\nChoisis un niveau d'étude :")
    print("  (laisser vide pour aucun filtre)")
    print("  1 → Bac +1 à +2")
    print("  3 → Bac +3")
    print("  4 → Bac +4 à +5")
    print("  6 → Bac +6 et +")
    niveau = input("Ton choix (1, 3, 4, 6 ou vide) : ").strip()
    
    localisation = input("Entrez une ville ou une région (facultatif) : ").strip()
    
    max_results_str = input("Nombre max de résultats (défaut = 3, max = 50) : ").strip()
    max_results = int(max_results_str) if max_results_str.isdigit() else 3
    max_results = min(max_results, 50)

    print(f"\n🔍 Recherche en cours avec les paramètres :")
    print(f"   - Mot-clé : {mot_cle}")
    print(f"   - Niveau : {niveau if niveau else 'Tous niveaux'}")
    print(f"   - Localisation : {localisation if localisation else 'Toute la France'}")
    print(f"   - Nombre max : {max_results}")

    # Construction de l'URL et recherche
    search_url = construire_url(mot_cle, niveau)
    print(f"\n🌐 URL de recherche : {search_url}")
    
    # Recherche des formations
    print("\n" + "="*50)
    print("ÉTAPE 1: RECHERCHE DES FORMATIONS")
    print("="*50)
    
    src_formations = rechercher_formations(search_url, max_results=max_results)
    
    if not src_formations:
        print("❌ Aucune formation trouvée.")
        return

    print(f"\n✅ {len(src_formations)} formation(s) trouvée(s) :")
    for i, formation in enumerate(src_formations, 1):
        print(f"   {i}. {formation['titre']}")

    # Analyse détaillée
    print("\n" + "="*50)
    print("ÉTAPE 2: ANALYSE DÉTAILLÉE")
    print("="*50)

    driver = create_driver()
    full_data = []

    try:
        for i, formation in enumerate(src_formations, 1):
            print(f"\n📋 === ANALYSE {i}/{len(src_formations)} ===")
            print(f"Formation : {formation['titre']}")
            print(f"URL : {formation['lien']}")
            
            # Extraction des infos détaillées
            infos_detaillees = extraire_infos_formation(driver, formation['lien'], localisation)
            
            # Fusion des données - CORRECTION ICI
            formation_complete = {
                "titre": formation["titre"],
                "lien": formation["lien"],
                "durée": infos_detaillees["durée"],
                "nature": infos_detaillees["nature"],
                "type": infos_detaillees["type"],
                "établissements_conseillés": infos_detaillees["établissements_conseillés"]
            }
            
            full_data.append(formation_complete)
            
            print(f"✅ Analyse terminée pour : {formation['titre']}")
            print(f"✅ Données ajoutées : {formation_complete}")
            print("-" * 50)
            
            # Petite pause entre les requêtes
            time.sleep(2)

    except KeyboardInterrupt:
        print("\n⚠️ Interruption par l'utilisateur")
    except Exception as e:
        print(f"❌ Erreur lors de l'analyse des formations : {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.quit()
        print("\n🔄 WebDriver fermé")

    # Export des résultats
    print("\n" + "="*50)
    print("ÉTAPE 3: EXPORT DES DONNÉES")
    print("="*50)
    
    if full_data:
        print(f"📊 Données collectées pour {len(full_data)} formation(s)")
        print(f"🔍 DEBUG - Exemple de données collectées :")
        if full_data:
            print(f"   {full_data[0]}")
        
        export_csv(full_data)
        print(f"\n🎉 Processus terminé ! {len(full_data)} formation(s) analysée(s) et exportée(s)")
    else:
        print("❌ Aucune donnée à exporter")


if __name__ == "__main__":
    main()
