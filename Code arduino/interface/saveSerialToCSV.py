import serial
import csv
import time

# Configuration du port série (ajuste selon ton système)
PORT = "COM4"  # Changer selon le port usb de l'Arduino
BAUDRATE = 115200
OUTPUT_FILE = "data.csv" # Nom du fichier, a changer sinon écrase l'ancier

# Création du fichier CSV et écriture de l'en-tête
with open(OUTPUT_FILE, "w", newline='') as f:
    writer = csv.writer(f)
    writer.writerow(["temps", "ACTU", "MILIEU", "LASER"])  # En-tête du fichier CSV

print(f"Fichier {OUTPUT_FILE} créé avec en-tête.")

# Ouvrir la connexion série
try:
    ser = serial.Serial(port=PORT, baudrate=BAUDRATE, timeout=1)
    time.sleep(1)  # Attendre 1 secondes pour que le port série soit prêt
    print(f"Port série {PORT} ouvert, enregistrement en cours...")
except serial.SerialException:
    print("Erreur d'ouverture du port série")
    exit(1)

try:
    with open(OUTPUT_FILE, "a", newline='') as f:
        writer = csv.writer(f)

        while True:
            ligne = ser.readline().decode('utf-8', errors='ignore').strip()
            if ligne:
                try:
                    # Split la ligne en donnees pour csv
                    valeurs = ligne.split(",")

                    # Vérifier que le format est correct et écrire dans le fichier CSV
                    if len(valeurs) == 4:
                        writer.writerow(valeurs)
                        print("Donnée enregistrée :", valeurs)
                    else:
                        print("Format invalide :", ligne)

                except Exception as e:
                    print("Erreur de lecture :", e)

# Ctrl C pour terminer
except KeyboardInterrupt:
    print("\nArrêt du programme")
    ser.close()