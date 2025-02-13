import os
import serial
import csv
import time
from utils import lire_donnees, envoyer_commande

''' Code principal '''

PORT = "COM4"  # Changer selon le port usb de l'Arduino
BAUDRATE = 115200

# Nom fichier csv pas utilisé
OUTPUT_FILE = "data"
i = 0
while(os.path.exists("./"+OUTPUT_FILE+str(i)+".csv")):
    i += 1
OUTPUT_FILE = OUTPUT_FILE + str(i) + ".csv"

# Création du fichier CSV et écriture de l'en-tête
with open(OUTPUT_FILE, "w", newline='') as f:
    writer = csv.writer(f)
    writer.writerow(["temps", "ACTU", "MILIEU", "LASER"])  # En-tête du fichier CSV

print(f"Fichier {OUTPUT_FILE} créé avec en-tête.")

# Ouvrir la connexion série
try:
    ser = serial.Serial(port=PORT, baudrate=BAUDRATE, timeout=1)
    time.sleep(1)  # Attendre 1 seconde pour que le port série soit prêt
    print(f"Port série {PORT} ouvert, enregistrement en cours...")
except serial.SerialException:
    print("Erreur d'ouverture du port série")
    exit(1)

try:
    with open(OUTPUT_FILE, "a", newline='') as f:
        writer = csv.writer(f)
        time.sleep(1)
        print(envoyer_commande("set_voltage -1", ser))
        print(envoyer_commande("set_voltage -1", ser))
        print(envoyer_commande("set_voltage -1", ser))
        print(envoyer_commande("set_voltage -1", ser))
        while True:
            lire_donnees(ser, writer)
except KeyboardInterrupt:
    print("\nArrêt du programme")
    ser.close()
