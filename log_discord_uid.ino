// Bibliotecas necessárias para o projeto
#include <SPI.h>
#include <MFRC522.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

// --- CONFIGURAÇÕES DO WIFI ---
// !!! IMPORTANTE: Substitua com os dados da sua rede !!!
const char* ssid = "NOME_DA_SUA_REDE_WIFI";
const char* password = "SENHA_DA_SUA_REDE_WIFI";

// --- CONFIGURAÇÕES DO SERVIDOR ---
// URL base do Ngrok (sem a rota final)
String baseUrl = "https://unindulgent-lynne-cranially.ngrok-free.dev";

// Rota para enviar LOGS (POST)
String logUrl = baseUrl + "/api/rfid_log";

// Rota para verificar COMANDOS de abertura (GET)
String checkUrl = baseUrl + "/api/check_door_command";

// --- CONFIGURAÇÕES DE HARDWARE ---
#define SS_PIN    5   // Pino SS (Slave Select) do RFID
#define RST_PIN   22  // Pino de Reset do RFID
#define RELAY_PIN 4   // Pino de controle do RELÉ/Fechadura

MFRC522 mfrc522(SS_PIN, RST_PIN);

// --- Variáveis de Controle de Tempo ---
unsigned long lastCheckTime = 0;
const long checkInterval = 2000; // Verifica comandos a cada 2000ms (2 segundos)

// Protótipos das funções
void connectToWiFi();
void sendUidToServer(String uid);
void checkRemoteCommand();
void openDoor();

void setup() {
  Serial.begin(115200);
  SPI.begin();
  mfrc522.PCD_Init();

  // Configuração do pino do Relé
  pinMode(RELAY_PIN, OUTPUT);
  digitalWrite(RELAY_PIN, LOW); // Inicia desligado/fechado

  Serial.println("\n[SETUP] Conectando ao WiFi...");
  connectToWiFi();
  Serial.println("[SETUP] Sistema pronto. Aguardando tags ou comandos remotos...");
}

void loop() {
  // 1. VERIFICAÇÃO DE COMANDO REMOTO (POLLING)
  // Executa a cada X segundos sem bloquear o resto do código
  if (millis() - lastCheckTime >= checkInterval) {
    lastCheckTime = millis();
    checkRemoteCommand();
  }

  // 2. LEITURA RFID
  // Se não houver uma nova tag, encerra o loop atual e começa de novo
  if (!mfrc522.PICC_IsNewCardPresent() || !mfrc522.PICC_ReadCardSerial()) {
    delay(50); 
    return;
  }

  // Obter o UID da tag
  String uidString = "";
  for (byte i = 0; i < mfrc522.uid.size; i++) {
    uidString += (mfrc522.uid.uidByte[i] < 0x10 ? "0" : "");
    uidString += String(mfrc522.uid.uidByte[i], HEX);
  }
  uidString.toUpperCase();
  
  Serial.println("===================");
  Serial.print("TAG LIDA: ");
  Serial.println(uidString);

  // Envia o UID para o servidor Flask
  sendUidToServer(uidString);
  
  // Para a leitura da tag atual
  mfrc522.PICC_HaltA();
  mfrc522.PCD_StopCrypto1();

  // Pequeno delay para evitar leituras múltiplas seguidas da mesma tag
  delay(1000);
}

/**
 * @brief Conecta o ESP32 à rede WiFi.
 */
void connectToWiFi() {
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\n[WiFi] Conectado!");
  Serial.print("[WiFi] IP: ");
  Serial.println(WiFi.localIP());
}

/**
 * @brief Verifica no servidor se há ordem de abrir a porta.
 */
void checkRemoteCommand() {
  if (WiFi.status() != WL_CONNECTED) return;

  HTTPClient http;
  http.begin(checkUrl);
  
  // Realiza requisição GET
  int httpResponseCode = http.GET();
  
  if (httpResponseCode > 0) {
    String payload = http.getString();
    
    // Analisa o JSON: {"open": true} ou {"open": false}
    StaticJsonDocument<200> doc;
    DeserializationError error = deserializeJson(doc, payload);

    if (!error) {
      bool shouldOpen = doc["open"];
      if (shouldOpen) {
        Serial.println("[REMOTO] Comando de abertura recebido!");
        openDoor();
      }
    } else {
      Serial.print("[JSON] Erro no parse: ");
      Serial.println(error.c_str());
    }
  }
  http.end();
}

/**
 * @brief Ativa o relé para abrir a porta.
 */
void openDoor() {
  Serial.println("[PORTA] Abrindo...");
  digitalWrite(RELAY_PIN, HIGH); // Ativa o relé
  delay(3000);                   // Mantém aberto por 3 segundos
  digitalWrite(RELAY_PIN, LOW);  // Desativa o relé
  Serial.println("[PORTA] Fechada.");
}

/**
 * @brief Envia o UID para o servidor.
 */
void sendUidToServer(String uid) {
  if (WiFi.status() != WL_CONNECTED) {
    connectToWiFi();
    return;
  }

  HTTPClient http;
  http.begin(logUrl);
  http.addHeader("Content-Type", "application/json");

  StaticJsonDocument<100> doc;
  doc["uid"] = uid;
  String jsonPayload;
  serializeJson(doc, jsonPayload);

  Serial.print("[HTTP] Enviando UID: ");
  Serial.println(uid);

  int httpResponseCode = http.POST(jsonPayload);
  
  if (httpResponseCode > 0) {
    Serial.printf("[HTTP] Resposta: %d\n", httpResponseCode);
    // Aqui você poderia ler a resposta para ver se o acesso foi "Garantido"
    // e chamar openDoor() também se a tag for válida.
    // String response = http.getString();
  } else {
    Serial.printf("[HTTP] Erro: %s\n", http.errorToString(httpResponseCode).c_str());
  }

  http.end();
}