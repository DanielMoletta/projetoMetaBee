// Bibliotecas necessárias para o projeto
#include <SPI.h>
#include <MFRC522.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include "time.h"

// --- CONFIGURAÇÕES DO WIFI ---
const char* ssid = "NOME_DA_SUA_REDE_WIFI";
const char* password = "SENHA_DA_SUA_REDE_WIFI";

// --- CONFIGURAÇÕES DO SERVIDOR ---
// Este será o endereço público gerado pelo ngrok
const char* serverUrl = "https://unindulgent-lynne-cranially.ngrok-free.dev"; 

// --- CONFIGURAÇÕES DO RFID ---
#define SS_PIN    5   // Pino SS (Slave Select) / SDA
#define RST_PIN   22  // Pino de Reset
MFRC522 mfrc522(SS_PIN, RST_PIN);

// --- CONFIGURAÇÕES DE FUSO HORÁRIO (UTC-3, BRASIL) ---
const char* ntpServer = "pool.ntp.org";
const long gmtOffset_sec = -3 * 3600;
const int daylightOffset_sec = 0;

void connectToWiFi();
void sendLogToServer(String uid, String timestamp);
String getTimestamp();

void setup() {
  Serial.begin(115200);
  SPI.begin();
  mfrc522.PCD_Init();

  Serial.println("\n[SETUP] A ligar ao WiFi...");
  connectToWiFi();

  Serial.println("[SETUP] A sincronizar relógio com NTP...");
  configTime(gmtOffset_sec, daylightOffset_sec, ntpServer);
  Serial.println("[SETUP] Sistema pronto. A aguardar por tags...");
}

void loop() {
  // Se não houver uma nova tag, não faz nada
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
  
  // Obter o horário exato da leitura
  String timestamp = getTimestamp();

  Serial.println("===================");
  Serial.print("TAG LIDA: ");
  Serial.println(uidString);
  Serial.print("HORÁRIO: ");
  Serial.println(timestamp);

  // Envia o UID e o horário para o servidor Flask
  sendLogToServer(uidString, timestamp);
  
  mfrc522.PICC_HaltA();
  mfrc522.PCD_StopCrypto1();

  // Aguarda um pouco para evitar leituras duplicadas
  delay(3000);
}

void connectToWiFi() {
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\n[WiFi] Ligado!");
  Serial.print("[WiFi] Endereço IP: ");
  Serial.println(WiFi.localIP());
}

String getTimestamp() {
  struct tm timeinfo;
  if (!getLocalTime(&timeinfo)) {
    Serial.println("[NTP] Falha ao obter hora local");
    return "0000-00-00 00:00:00";
  }
  char timeString[20];
  // Formato ISO 8601, ideal para bases de dados
  strftime(timeString, sizeof(timeString), "%Y-%m-%d %H:%M:%S", &timeinfo);
  return String(timeString);
}

void sendLogToServer(String uid, String timestamp) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[HTTP] WiFi desligado. A tentar religar...");
    connectToWiFi();
    return;
  }

  HTTPClient http;
  http.begin(serverUrl);
  http.addHeader("Content-Type", "application/json");

  // Cria um documento JSON para enviar os dados
  StaticJsonDocument<200> doc;
  doc["uid"] = uid;
  doc["timestamp"] = timestamp;

  String jsonPayload;
  serializeJson(doc, jsonPayload);

  Serial.print("[HTTP] A enviar para o servidor: ");
  Serial.println(jsonPayload);

  int httpResponseCode = http.POST(jsonPayload);

  if (httpResponseCode > 0) {
    Serial.printf("[HTTP] Resposta do Servidor: %d\n", httpResponseCode);
    String response = http.getString();
    Serial.println("[HTTP] Corpo da Resposta: " + response);
  } else {
    Serial.printf("[HTTP] Erro no envio: %s\n", http.errorToString(httpResponseCode).c_str());
  }

  http.end();
}
