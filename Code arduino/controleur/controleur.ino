// Constantes pour les pins
const int T_ACTU = 0;
const int T_MILIEU = 0;
const int T_LASER = 0;
const int ACTU = 0;

// Constantes thermistances
const float A = 0.00335401643468053;
const float B = 0.000256523550896126;
const float C = 0.00000260597012072052;
const float D = 0.000000063292612648746;
const int r_25deg = 10000;
const int r_diviseur = 10000;

// Constantes pour PI
const float GAIN = 0;
const float TEMPS_INTEGRALE = 0;
const float TS = 0.1 // periode echantillonnage (en sec)... à choisir 

// Params
bool asservir = true;  // Pour setter si on veut asservir la temperature

// Déclarations fonctions
float PI_output(...);
float tension_a_temp(float tension);


void setup() {
  // Pour print
  Serial.begin(9600);

  pinMode(T_ACTU, INPUT);
  pinMode(T_MILIEU, INPUT);
  pinMode(T_LASER, INPUT);
  pinMode(ACTU, OUTPUT);
}

void loop() {
  // Donnes temperature (brut = tension termistance, traite = converti en temperature)
  float t_actu_brut = analogRead(T_ACTU);
  float t_actu_traite = tension_a_temp(t_actu_brut);
  float t_milieu_brut = analogRead(T_MILIEU);
  float t_milieu_traite = tension_a_temp(t_milieu_brut);
  float t_laser_brut = analogRead(T_LASER);
  float t_laser_traite = tension_a_temp(t_laser_brut);
  Serial.println(String(t_actu_traite) + " | " + String(t_milieu_traite) + " | " + String(t_laser_traite));
  delay(1000); // temporaire

  float sortie_pi = PI_output(28.0, t_laser_traite); // 28 pour test
  //analogWrite(ACTU, constrain(sortie_pi * 255.0 / 5.0, 0, 255)); 
}

// Calcule la sortie du PI
float PI_output(float cible, float mesure){
  // TODO: integrale

  float erreur = cible - mesure;

  return ; // mettre formule pi

}

// Calcule temperature avec thermistance NTC (resistance descend si température monte)
float tension_a_temp(float tension) {
  float rt = tension * r_diviseur / (3.3 - tension) ; // diviseur tension (3.3V à confirmer)
  int log_r = log(rt/r_25deg); // Simplifier calcul
  return 1/(A+B*log_r+C*log_r*log_r+D*log_r*log_r*log_r) - 273.15; // temperature en °C
}