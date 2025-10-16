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
// !!! IMPORTANTE: Substitua pelo endereço gerado pelo ngrok !!!
// A URL deve incluir o caminho completo para a API.
const char* serverUrl = "https://unindulgent-lynne-cranially.ngrok-free.dev/api/rfid_log"; 

// --- CONFIGURAÇÕES DO RFID ---
#define SS_PIN    5   // Pino SS (Slave Select) / SDA
#define RST_PIN   22  // Pino de Reset
MFRC522 mfrc522(SS_PIN, RST_PIN);

// Protótipos das funções
void connectToWiFi();
void sendUidToServer(String uid);

void setup() {
  Serial.begin(115200);
  SPI.begin();
  mfrc522.PCD_Init();

  Serial.println("\n[SETUP] Conectando ao WiFi...");
  connectToWiFi();

  Serial.println("[SETUP] Sistema pronto. Aguardando por tags RFID...");
}

void loop() {
  // Se não houver uma nova tag, não faz nada
  if (!mfrc522.PICC_IsNewCardPresent() || !mfrc522.PICC_ReadCardSerial()) {
    delay(50);
    return;
  }

  // Obter o UID da tag em formato de String
  String uidString = "";
  for (byte i = 0; i < mfrc522.uid.size; i++) {
    uidString += (mfrc522.uid.uidByte[i] < 0x10 ? "0" : "");
    uidString += String(mfrc522.uid.uidByte[i], HEX);
  }
  uidString.toUpperCase();
  
  Serial.println("===================");
  Serial.print("TAG LIDA: ");
  Serial.println(uidString);

  // Envia apenas o UID para o servidor Flask, pois o servidor já
  // cuida de registrar o horário do acesso.
  sendUidToServer(uidString);
  
  mfrc522.PICC_HaltA();
  mfrc522.PCD_StopCrypto1();

  // Aguarda um pouco para evitar leituras duplicadas da mesma tag
  delay(3000);
}

/**
 * @brief Conecta o ESP32 à rede WiFi especificada.
 */
void connectToWiFi() {
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\n[WiFi] Conectado!");
  Serial.print("[WiFi] Endereço IP: ");
  Serial.println(WiFi.localIP());
}

/**
 * @brief Envia o UID da tag lida para o servidor web via POST.
 * @param uid A string hexadecimal do UID da tag.
 */
void sendUidToServer(String uid) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[HTTP] WiFi desconectado. Tentando reconectar...");
    connectToWiFi();
    return;
  }

  HTTPClient http;
  
  // Inicia a conexão com a URL completa do servidor
  http.begin(serverUrl);
  http.addHeader("Content-Type", "application/json");

  // Cria um documento JSON para enviar os dados
  StaticJsonDocument<100> doc;
  doc["uid"] = uid;

  String jsonPayload;
  serializeJson(doc, jsonPayload);

  Serial.print("[HTTP] Enviando para o servidor: ");
  Serial.println(jsonPayload);

  // Executa a requisição POST
  int httpResponseCode = http.POST(jsonPayload);

  if (httpResponseCode > 0) {
    Serial.printf("[HTTP] Resposta do Servidor: %d\n", httpResponseCode);
    String response = http.getString();
    Serial.println("[HTTP] Corpo da Resposta: " + response);
  } else {
    Serial.printf("[HTTP] Erro no envio: %s\n", http.errorToString(httpResponseCode).c_str());
  }

  // Libera os recursos
  http.end();
}
