# Envoyer commande au Arduino.
# Liste de commandes : set_mode (1 ou 2), set_voltage (-1 à 1)
def envoyer_commande(commande, ser):
    """Envoie une commande et attend une réponse RESP:"""
    ser.write((commande + "\n").encode())
    while True:
        ligne = ser.readline().decode('utf-8', errors='ignore').strip()
        if ligne.startswith("RESP:"):
            return ligne[5:]  # Retourner la réponse après "RESP:"

# Lire les données capteur en continu
def lire_donnees(ser, writer):
    ligne = ser.readline().decode('utf-8', errors='ignore').strip()
    if ligne.startswith("DATA:"):
        try:
            # Extraire la valeur après "DATA:" et split la ligne en donnees pour csv
            valeurs = ligne[5:].split(",")

            # Vérifier que le format est correct et écrire dans le fichier CSV
            if len(valeurs) == 4:
                writer.writerow(valeurs)
                print("Donnée enregistrée :", valeurs)
            else:
                print("Format invalide :", ligne)

        except Exception as e:
            print("Erreur de lecture :", e)

