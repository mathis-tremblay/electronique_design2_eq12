# Envoyer commande au Arduino.
# Liste de commandes : set_mode (1 ou 2), set_voltage (-1 à 1)
import csv
import os
import time


def envoyer_commande(commande, ser):
    """Envoie une commande et attend une réponse RESP:"""
    ser.write((commande + "\n").encode())
    start_time = time.time()
    timeout = 3  # 3 secondes max pour une réponse

    while True:
        if time.time() > start_time + timeout:
            return "Aucune réponse, veuillez réessayer."

        try:
            ligne = ser.readline().decode('utf-8', errors='ignore').strip()
            if ligne.startswith("RESP:"):
                return ligne[5:]  # Retourner la réponse après "RESP:"
        except Exception as e:
            return f"Erreur lors de la lecture: {e}"


# Lire les données capteur en continu
def lire_donnees(ser, writer):
    ligne = ser.readline().decode('utf-8', errors='ignore').strip()
    if ligne.startswith("DATA:"):
        try:
            # Extraire la valeur après "DATA:" et split la ligne en donnees pour csv
            valeurs = ligne[5:].split(",")

            # Vérifier que le format est correct et écrire dans le fichier CSV
            if len(valeurs) == 8:
                writer.writerow(valeurs)
                print("Donnée enregistrée :", valeurs)
            else :
                print("Format invalide :", ligne)

        except Exception as e:
            print("Erreur de lecture :", e)

def creer_fichier():
    # Nom fichier csv pas utilisé
    OUTPUT_FILE = "data"
    i = 0
    while (os.path.exists("./" + OUTPUT_FILE + str(i) + ".csv")):
        i += 1
    OUTPUT_FILE = OUTPUT_FILE + str(i) + ".csv"

    # Création du fichier CSV et écriture de l'en-tête
    fichier = open(OUTPUT_FILE, "w", newline='')
    writer = csv.writer(fichier)
    writer.writerow(["temps", "ACTU", "MILIEU", "LASER", "LASER_ESTIME", "TENSION_ACTU", "TENSION_MILIEU", "TENSION_LASER",
                         "DUTY CYCLE", "STABILITE"])  # En-tête du fichier CSV
    #writer.writerow(
    #    ["temps", "COMMANDE", "ACTU", "MILIEU", "LASER", "LASER_ESTIME", "STABILITE"])

    print(f"Fichier {OUTPUT_FILE} créé avec en-tête.")
    return fichier, writer
