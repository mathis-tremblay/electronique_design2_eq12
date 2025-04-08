// Constantes pour les pins
const int T_ACTU = A0;
const int T_MILIEU = A1;
const int T_LASER = A2;
const int ACTU = 11; // pour avoir timer1 (16 bits)

// Constantes thermistances
const double A = 0.00335401643468053;
const double B = 0.000256523550896126;
const double C = 0.00000260597012072052;
const double D = 0.000000063292612648746;
const int r_25deg = 10000;
const int r_diviseur = 10000;
const double freq = 1.5; // Freq échantillonnage = freq/3

// Constantes et variables pour PIDF;
/*double a0 = 367.68750;
double a1 = -710.27591;
double a2 = 343.01658;
double b0 = 0.60350;
double b1 = 0.39650;
*/

double Kp = 25.0;
double Ti = 0.16;
double Td = 664.34;
double Tf = 0.7336;

// Memoire donnees pour PIDF
double e[2] = {0}; // files entrees
double u[2] = {0}; // files sortie
int index = 0;
double err_integrale = 0;
double err_prev = 0;
double derivee_filtree_prev = 0;

// Saturation
const int umin = 290;
const int umax = 1670;

// Variables pour calculer T3 estimé (calculs en assumant T=2)
const double b = 0.085;
const double a = 0.9026;
double t3k_1 = 0;

bool mode_rep_echelon = true;  // Pour setter si on veut sauvegarder des réponses à l'échelon ou asservir la temperature (si false)

double temp_cible = 24.0;
double temp_piece = 24.0; // Point d'operation, mesuré dans le setup

// Stabilite
const double tolerance = 0.1;
const int N = 30;
double t3_mesures[N] = {0}; // tableau circulaire mesures
int indice = 0;

// Variables lecteurs températures
volatile uint16_t valeur_ADC[3];
volatile uint8_t canal_ADC = 0;   // numero pin en cours de lecture
volatile bool nouvelle_donnee = false;

// Déclarations fonctions
double bits_a_tension(double donne_brute);
double PID_output(double cible, double mesure);
double tension_a_temp(double tension);
double estimer_t3(double t2_mesure);
int verif_stable(double t3);


void setup() {
  // Pour print
  Serial.begin(115200);

  pinMode(T_ACTU, INPUT);
  pinMode(T_MILIEU, INPUT);
  pinMode(T_LASER, INPUT);
  pinMode(ACTU, OUTPUT);

  // Pour avoir fréquence de 1kHz et 16 bits sur le pwm
  TCCR1A = (1 << COM1A1) | (1 << WGM11); // Mode Fast PWM avec TOP = ICR1
  TCCR1B = (1 << WGM13) | (1 << WGM12) | (1 << CS11); // Prescaler = 8
  ICR1 = 2000;  // Définit la période pour obtenir 1kHz
  OCR1A = 980; // entre 280 et 1680 (0V quand 980)

  // Timer2 pour test sur arduino uno
  /*TCCR2A = (1 << WGM21);   // Mode CTC pour faire interruptions
  TCCR2B = (1 << CS22);    // Prescaler de 64
  OCR2A = 249;             // Calcul pour trouver OCR2A en fonction de la fréquence d'échantillonnage : (16 MHz / (prescaler *  62.5Hz)) - 1 = 249 
  TIMSK2 |= (1 << OCIE2A); // Activer l’interruption du timer
*/
  // Timer 3: code officiel pour arduino mega
  // Configurer Timer3 pour générer interruption
  TCCR3A = 0;                      // Mode normal
  TCCR3B = (1 << WGM32) | (1 << CS32) | (1 << CS30);  // CTC mode, prescaler 1024
  OCR3A = 16000000 / (1024 * freq) - 1;                 
  TIMSK3 |= (1 << OCIE3A);         // Activer l’interruption du timer
  

  // Configurer l’ADC
  ADMUX = (1 << REFS0);    // Référence AVCC, entrée (A0)
  ADCSRA = (1 << ADEN)  |  // Activer l’ADC
           (1 << ADPS2) | (1 << ADPS1) | (1 << ADPS0); // Prescaler 128 (16MHz / prescaler = 125kHz ADC)
  // Complète une conversion en 104us (13 cycle d'horloge / fréquence adc = 104us)

  // Récolter la température de la pièce (pour point d'opération)
  delay(1000);
  double somme = 0;
  const int nbMesures = 10; 
  for (int i = 0; i < nbMesures; i++) {
    somme += analogRead(T_MILIEU);
    delay(10);
  }
  double bits_operation = somme / nbMesures;
  temp_piece = tension_a_temp(bits_a_tension(bits_operation));
}


ISR(TIMER3_COMPA_vect) {
  //Sélectionner le canal ADC (A0, A1, A2)
  ADMUX = (ADMUX & 0xF8) | canal_ADC; // Met à jour les bits MUX pour ADC0, ADC1 ou ADC2

  ADCSRA |= (1 << ADSC);  // Lancer une conversion ADC
  while (ADCSRA & (1 << ADSC));  // Attendre la fin de conversion
  valeur_ADC[canal_ADC] = ADC;  // Lire la valeur (10 bits)

  canal_ADC = (canal_ADC + 1) % 3;
  if (canal_ADC == 0) nouvelle_donnee = true; // Après une séquence complète (A0, A1, A2)
}


void loop() {

  // Vérifier si une commande est reçue
  if (Serial.available() > 0) {
    String commande = Serial.readStringUntil('\n');
    commande.trim();
    if (commande.startsWith("set_mode ")) {
      int mode = commande.substring(8).toInt();
      if (mode == 1) {
        mode_rep_echelon = true;
        Serial.println("RESP:Mode manuel activé.");
      }
      else {
        mode_rep_echelon = false;
        Serial.println("RESP:Mode contrôleur activé.");
      }
    }

    else if (commande == "get_mode"){
      Serial.println("RESP:" + (String)mode_rep_echelon);
    }

    else if (commande == "get_temp_cible"){
      Serial.println("RESP:" + (String)temp_cible);
    }

    else if (commande == "get_temp_piece"){
      Serial.println("RESP:" + (String)temp_piece);
    }

    else if (commande == "get_pidf"){
      Serial.println("RESP:" + String(Kp,3) + "," + String(Ti,3) + "," + String(Td,3) + "," + String(Tf,3));
    }

    else if (commande.startsWith("set_voltage ")) {
      if (mode_rep_echelon) {
        String valeur_str = commande.substring(11);
        valeur_str.trim();
        bool estNombre = true;

        // Vérifier si la valeur est bien un nombre
        for (unsigned int i = 0; i < valeur_str.length(); i++) {
            if (!isDigit(valeur_str[i]) && valeur_str[i] != '.' && valeur_str[i] != '-' && valeur_str[i] != '+' && valeur_str[i] != ' ') {
                estNombre = false;
                break;
            }
        }
        float volt = valeur_str.toFloat();
        if (volt > 1. || volt < -1. || !estNombre) {
          Serial.println("RESP:La tension ne respecte pas les bornes de -1V a 1V.");
        }
        else {
          OCR1A = map(volt*500, -500, 500, umin, umax);
          Serial.print("RESP:Volts en entré: ");
          Serial.println(volt);
        } 
      }
      else {
        Serial.println("RESP:Tu ne peux pas commander une tension en mode automatique.");
      }
    }

    else if (commande.startsWith("set_temp ")){
      double temp = commande.substring(8).toFloat();
      if (temp > 30. || temp < 20.) {
        Serial.println("RESP:La température n'est pas entre 20°C et 30°C.");
      }
      else {
        temp_cible = temp;
        Serial.print("RESP:Température en entré: ");
        Serial.print(temp);
        if (mode_rep_echelon){
          Serial.println(". Cependant, il y n'aura pas d'effet, car vous êtes en mode manuel.");
        }
        else{
          Serial.println();
        }
      }
    }

    else if (commande.startsWith("set_temp_piece ")){
      double temp = commande.substring(14).toFloat();
      if (temp > 30. || temp < 20.) {
        Serial.println("RESP:La température n'est pas entre 20°C et 30°C.");
      }
      else {
        temp_piece = temp;
        Serial.print("RESP:Température pièce en entré: ");
        Serial.println(temp);
      }
    }

    else if (commande.startsWith("set_pidf ")){
      String pidf = commande.substring(8);
    
      char pidf_array[pidf.length() + 1]; 
      pidf.toCharArray(pidf_array, sizeof(pidf_array));
      
      char* token = strtok(pidf_array, ",");
      
      float vals[4] = {0};

      int i = 0;
      while (token != NULL && i < 4) {
          vals[i] = atof(token);
          token = strtok(NULL, ","); 
          i++;
      }
      
      if (i == 4) {
          Kp = vals[0];
          Ti = vals[1];
          Td = vals[2];
          Tf = vals[3];
          Serial.print("RESP:Voici les nouvelles valeurs: Kp=");
          Serial.print(Kp, 3);
          Serial.print(", Ti=");
          Serial.print(Ti, 3);
          Serial.print(", Td=");
          Serial.print(Tf, 3);
          Serial.print(", Tf=");
          Serial.println(Tf, 3);
      } else {
          Serial.println("RESP:Erreur.");
      }
    }
    
    else {
        Serial.println("RESP:Commande inconnue.");
    }
  }

  // attendre qu'on recupere une nouvelle donnee
  if (nouvelle_donnee) {
    // Conversions ADC (10 bits)
    // Tensions
    double v_actu = bits_a_tension(valeur_ADC[0]);
    double v_milieu = bits_a_tension(valeur_ADC[1]);
    double v_laser = bits_a_tension(valeur_ADC[2]);

    // Convertir les tensions en températures
    double t_actu = tension_a_temp(v_actu);
    double t_milieu = tension_a_temp(v_milieu);
    double t_laser = tension_a_temp(v_laser);

    double t3_estime = estimer_t3(t_milieu);


    // Afficher les donnees sur le serial monitor (pour export)
    Serial.print("DATA:");
    Serial.print(millis()/1000.0, 0);
    Serial.print(",");
    Serial.print(t_actu, 3);
    Serial.print(",");
    Serial.print(t_milieu, 3);
    Serial.print(",");
    Serial.print(t_laser, 3);
    Serial.print(",");
    Serial.print(t3_estime, 3);
    Serial.print(",");
    Serial.print(v_actu, 3);
    Serial.print(",");
    Serial.print(v_milieu, 3);
    Serial.print(",");
    Serial.print(v_laser, 3);

    if (mode_rep_echelon){
    }
    else { // Mode controleur
      double sortie_pid = PID_output(temp_cible, t3_estime); 
      // ici on va vouloir changer la fréquence du pwm en fonction de sorti_PI :
      OCR1A = sortie_pid;
    }
    Serial.print(",");
    Serial.print(OCR1A);
    int est_stable = verif_stable(t3_estime);
    Serial.print(",");
    Serial.println(est_stable);
    nouvelle_donnee = false;
  }
}

// Calcule la sortie du PID
double PID_output(double cible, double mesure) {
  // u = anciennes sorties
  // e : anciennes erreurs
  /*double err = (cible - mesure);
  double sortie = a0*err + a1*e[0] + a2*e[1] + b0*u[0] + b1*u[1];
  Serial.println();
  Serial.println(sortie);
  // Mise à jour des erreurs et sorties
  e[1] = e[0];
  e[0] = err;
  
  u[1] = u[0];
  u[0] = sortie;
  sortie = constrain(map(sortie, -100, 100, umin, umax), umin, umax);
  if (sortie == umin || sortie == umax) {
    e[0] = 0; // Anti-windup
    u[0] = u[1];
  }
  return sortie;*/

  double err = cible - mesure;

  // Mise à jour de l'erreur integrale
  err_integrale += err; // Accumulation pour le terme intégral

  // Calcul PID
  double derivee = err - err_prev;
  double derivee_filtree = (Tf * derivee + derivee_filtree_prev) / (1 + Tf);
  err_prev = err; 

  double output = Kp * err + Ti * err_integrale + Td * derivee_filtree;
  output = map(output*10, -1000, 1000, 0, 2000) - 20;

  
  // Appliquer saturation et anti-windup
  if (output > umax) {
    output = umax;
    err_integrale -= err; // Anti-windup
  } 
  else if (output < umin) {
    output = umin;
    err_integrale -= err; // Anti-windup
  }

  return constrain(output, umin, umax);
}

// Calcul la tension a partir du resultat de 0 a 1023
double bits_a_tension(double donne_brute){
  // Transfert en tension et enlever gain et soustraction ampli
  double ref = analogRead(A7);
  ref = ref*5./1023. + 0.04; // Tension drop de 0.04V lors de l'échantillonnage sur arduino
  double tension = donne_brute * 5 / 1023.0 * 24000/100000 + ref; // Avec soustracteur
  return tension;
}

// Calcule temperature avec thermistance NTC (resistance descend si température monte)
double tension_a_temp(double tension) {
  double rt = tension * r_diviseur / (5 - tension) ; // diviseur tension
  double log_r = log(rt/r_25deg); // Simplifier calcul
  return 1/(A+B*log_r+C*log_r*log_r+D*log_r*log_r*log_r) - 273.15; // temperature en °C
}

// Estime T3 a partir de T2 avec une fonction de transfert (discretisee et recurrente)
double estimer_t3(double t2_mesure){
  double t2_op = t2_mesure - temp_piece; // Enlever le point d'operation
  double t3_estime_op = b * t2_op + a * t3k_1; // T3 = 0.86/(1+19.5s) * T2
  t3k_1 = t3_estime_op;
  return t3_estime_op + temp_piece;
}

/* Verifie stabilite de t3
 * Stable (1) si 10 dernieres mesures sont a la cible +- la tolerance
 * Semi-stable (2) si derniere mesure est stable mais pas toutes les 10 dernieres (pour pas avoir delai de 20 secondes)
 * Instable (0) si un element de la liste pas dans tolerance et derniere mesure non plus
*/
int verif_stable(double t3) {
  t3_mesures[indice] = t3; 
  indice = (indice + 1) % N; // Pour gérer la liste circulaire
  
  // Calcul de la moyenne
  double somme = 0;
  for (int i = 0; i < N; i++) {
    somme += t3_mesures[i];
  }
  double moyenne = somme / N;

  // Calcul de la déviation standard
  double somme_carre = 0;
  for (int i = 0; i < N; i++) {
    somme_carre += pow(t3_mesures[i] - moyenne, 2);
  }
  double ecart_type = sqrt(somme_carre / N);

  // Vérification de la stabilité
  if (ecart_type < tolerance && abs(t3 - temp_cible) < 0.6) {
    return 1; // Stable
  }
  return 0; // Instable
}

