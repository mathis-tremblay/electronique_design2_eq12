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

// Constantes et variables pour PI
const double Kp = 0.00062;
const double Ki = 0.11735;
const double Kd = 0;

// Memoire donnees pour PID
const int N = 10;
double u[N] = {0}; // files entrees
double y[N] = {0}; // files sortie
int index = 0;
double erreur_integrale = 0;

// Saturation
const int umin = 130;
const int umax = 850;

// Variables pour calculer T3 estimé (calculs en assumant T=2)
const double K = 0.89;
const double tau = 19.5;
const double b0 = K/(tau + 1);
const double b1 = K/(tau + 1);
const double a1 = -(tau-1)/(tau+1);
double t2[2] = {24, 24}; // T2 mesuré
double t3[2] = {24, 24}; // T3 estimé

bool mode_rep_echelon = true;  // Pour setter si on veut sauvegarder des réponses à l'échelon ou asservir la temperature (si false)

double temp_cible = 27.0;
double temp_piece = 24.0; // Point d'operation, mesuré dans le setup

// Stabilite
bool stable = false;
double tolerance = 0.1; // °C
double t3_mesures[N] = {0}; // tableau circulaire mesures
int indice = 0;

// Variables lecteurs températures
volatile uint16_t valeur_ADC[3];
volatile uint8_t canal_ADC = 0;   // numero pin en cours de lecture
volatile bool nouvelle_donnee = false;

// Déclarations fonctions
double PID_output(double cible, double mesure);
double tension_a_temp(double tension);
double estimer_t3(double t2_mesure);
int verif_stable(double t3);

// A commenter si avec mega :
int OCR3A = 0;

void setup() {
  // Pour print
  Serial.begin(115200);

  pinMode(T_ACTU, INPUT);
  pinMode(T_MILIEU, INPUT);
  pinMode(T_LASER, INPUT);
  pinMode(ACTU, OUTPUT);


  // Configuration timer pour interruptions
  TCCR1A = 0;                       // Mode normal
  TCCR1B = (1 << WGM12) | (1 << CS12) | (1 << CS10);  // Mode CTC, Prescaler 1024
  OCR1A = 16000000 / (1024 * freq) - 1; 
  TIMSK1 |= (1 << OCIE1A);          // Activer l’interruption

/*
  // A commenter si tests avec uno
  // Pour avoir fréquence de 4kHz et 16 bits sur le PWM avec Timer3
  TCCR3A = (1 << COM3A1) | (1 << WGM31); // Mode Fast PWM avec TOP = ICR3
  TCCR3B = (1 << WGM33) | (1 << WGM32) | (1 << CS30); // Mode 14, prescaler = 1
  ICR3 = 1000;  // Définit la période pour obtenir 1 kHz
  OCR3A = 550; // entre 130 (ou 75 idéalement) et 850 (0V quand 490)
*/
  
  // Configurer l’ADC
  ADMUX = (1 << REFS0);    // Référence AVCC, entrée (A0)
  ADCSRA = (1 << ADEN)  |  // Activer l’ADC
           (1 << ADPS2) | (1 << ADPS1) | (1 << ADPS0); // Prescaler 128 (16MHz / prescaler = 125kHz ADC)
  // Complète une conversion en 104us (13 cycle d'horloge / fréquence adc = 104us)

  // Point d'operation (temperature piece)
  float tension_operation = analogRead(T_MILIEU)*5./1023.;
  temp_piece = tension_a_temp(tension_operation);
  Serial.println(temp_piece);
}


ISR(TIMER1_COMPA_vect) {
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
          OCR3A = (volt + 1.) * umax/2;
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
    
    else {
        Serial.println("RESP:Commande inconnue.");
    }
  }

  // attendre qu'on recupere une nouvelle donnee
  if (nouvelle_donnee) {
    // Conversions ADC (10 bits)
    // Tensions (pour récolte données)
    double t_actu_brut = valeur_ADC[0] * 5 / 1023.0 * 24000/100000 + 1.7929;
    double t_milieu_brut = valeur_ADC[1] * 5 / 1023.0 * 24000/100000 + 1.7929;
    double t_laser_brut = valeur_ADC[2] * 5 / 1023.0 * 24000/100000 + 1.7929;

    // Convertir les tensions en températures
    double t_actu_traite = tension_a_temp(valeur_ADC[0]);
    double t_milieu_traite = tension_a_temp(valeur_ADC[1]);
    double t_laser_traite = tension_a_temp(valeur_ADC[2]);

    double t3_estime = estimer_t3(t_milieu_traite);


    // Afficher les donnees sur le serial monitor (pour export)
    Serial.print("DATA:");
    Serial.print(millis()/1000.0, 0);
    Serial.print(",");
    Serial.print(t_actu_traite, 3);
    Serial.print(",");
    Serial.print(t_milieu_traite, 3);
    Serial.print(",");
    Serial.print(t_laser_traite, 3);
    Serial.print(",");
    Serial.print(t3_estime, 3);
    Serial.print(",");
    Serial.print(t_actu_brut, 3);
    Serial.print(",");
    Serial.print(t_milieu_brut, 3);
    Serial.print(",");
    Serial.print(t_laser_brut, 3);

    if (mode_rep_echelon){
    }
    else { // Mode controleur
      double sortie_pid = PID_output(temp_cible, t3_estime); 
      // ici on va vouloir changer la fréquence du pwm en fonction de sorti_PI :
      OCR3A = sortie_pid;
    }
    Serial.print(",");
    Serial.print(OCR3A);
    int est_stable = verif_stable(t3_estime);
    Serial.print(",");
    Serial.println(est_stable);
    nouvelle_donnee = false;

  }
  
}

// Calcule la sortie du PID
double PID_output(double cible, double mesure) {
  double erreur = cible - mesure;

  // Mise à jour de l'erreur integrale
  erreur_integrale += erreur; // Accumulation pour le terme intégral

  // Calcul PID
  double derivee = erreur - u[index];
  index = (index + 1) % N; // maj index
  u[index] = erreur; 

  double output = Kp * erreur + Ki * erreur_integrale + Kd * derivee;
  output = map(output, -104., 104., umin, umax); // output avant saturation... TODO: Changer borne depart
  
  // Appliquer saturation et anti-windup
  if (output > umax) {
    output = umax;
    erreur_integrale -= erreur; // Anti-windup
  } 
  else if (output < umin) {
    output = umin;
    erreur_integrale -= erreur; // Anti-windup
  }

  return constrain(output, umin, umax);
}


// Calcule temperature avec thermistance NTC (resistance descend si température monte)
double tension_a_temp(double donne_brute) {
  // Transfert en tension et enlever gain et soustraction ampli
  double ref = analogRead(A7);
  ref = ref*5./1023. + 0.02; // Tension drop de 0.02V lors de l'échantillonnage sur arduino
  double tension = donne_brute * 5 / 1023.0 * 24000/100000 + ref; // Avec soustracteur
  double rt = tension * r_diviseur / (5 - tension) ; // diviseur tension
  double log_r = log(rt/r_25deg); // Simplifier calcul
  return 1/(A+B*log_r+C*log_r*log_r+D*log_r*log_r*log_r) - 273.15; // temperature en °C
}

// Estime T3 a partir de T2 avec une fonction de transfert (discretisee et recurrente)
double estimer_t3(double t2_mesure){
  double t2_op = t2_mesure - temp_piece; // Enlever le point d'operation
  double t3_estime_op = b0 * t2_op + b1 * t2[0] - a1 * t3[0]; // T3 = 0.89/(1+19.5s) * T2

  // Mettre à jour les variables
  t2[1] = t2[0];
  t2[0] = t2_op;

  t3[1] = t3[0];
  t3[0] = t3_estime_op;

  return t3_estime_op + temp_piece;
}

/* Verifie stabilite de t3
 * Stable (1) si 10 dernieres mesures sont a la cible +- la tolerance
 * Semi-stable (2) si derniere mesure est stable mais pas toutes les 10 dernieres (pour pas avoir delai de 20 secondes)
 * Instable (0) si un element de la liste pas dans tolerance et derniere mesure non plus
*/
int verif_stable(double t3){
  int stable = 1; // init a stable
  t3_mesures[indice] = t3; 
  indice = (indice + 1) % N; // pour gerer liste
  // Verif si un element dans la liste n'est pas dans la tolerance. Si oui, instable (ou semi-stable)
  for (int i=0; i<N; i++){
    if (abs(t3_mesures[i] - temp_cible) > tolerance){
      stable = 0; //instable
    }
  }
  // Si derniere mesure stable, mais pas 10 dernieres, alors semi-stable
  if (abs(t3 - temp_cible) < tolerance && stable == 0){
    stable = 2; // Semi-stable
  }
  return stable;
}

