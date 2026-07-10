use sysinfo::{System, SystemExt, CpuExt, DiskExt};
use serde::{Deserialize, Serialize};
use std::time::Duration;
use tauri::AppHandle;
use std::fs;
use std::path::PathBuf;
use mac_address::get_mac_address;
use hostname::get as get_hostname;

#[derive(Serialize)]
struct AutoRegisterRequest {
    mac_address: String,
    hostname: String,
    ip_address: String,
    operating_system: String,
    os_version: String,
}

#[derive(Serialize)]
struct TelemetryRequest {
    ip_address: String,
    cpu_usage: f32,
    ram_usage: f32,
    disk_usage: f32,
    temperature: f32,
    current_active_app: Option<String>,
    current_active_url: Option<String>,
}

#[derive(Deserialize)]
struct RegisterResponse {
    device_id: String,
}

const CONFIG_FILE: &str = "device_config.json";
const API_BASE: &str = "http://localhost:8000/api";

pub fn get_saved_device_id() -> Option<String> {
    if let Ok(content) = fs::read_to_string(CONFIG_FILE) {
        if let Ok(json) = serde_json::from_str::<serde_json::Value>(&content) {
            if let Some(id) = json["device_id"].as_str() {
                return Some(id.to_string());
            }
        }
    }
    None
}

fn save_device_id(device_id: &str) {
    let payload = serde_json::json!({ "device_id": device_id });
    let _ = fs::write(CONFIG_FILE, payload.to_string());
}

fn get_local_ip() -> String {
    // Basic implementation - in production use a better crate to find active local IP
    "127.0.0.1".to_string()
}

async fn auto_register() -> Option<String> {
    if let Some(id) = get_saved_device_id() {
        return Some(id);
    }
    
    let mac = match get_mac_address() {
        Ok(Some(ma)) => ma.to_string(),
        _ => "UNKNOWN_MAC".to_string(),
    };
    
    let hostname_str = match get_hostname() {
        Ok(h) => h.to_string_lossy().into_owned(),
        _ => "UnknownPC".to_string(),
    };
    
    let payload = AutoRegisterRequest {
        mac_address: mac,
        hostname: hostname_str,
        ip_address: get_local_ip(),
        operating_system: std::env::consts::OS.to_string(),
        os_version: "Unknown".to_string(),
    };

    let client = reqwest::Client::new();
    match client.post(&format!("{}/devices/auto-register", API_BASE))
        .json(&payload)
        .send()
        .await {
            Ok(res) => {
                if let Ok(json) = res.json::<RegisterResponse>().await {
                    save_device_id(&json.device_id);
                    return Some(json.device_id);
                }
            },
            Err(_) => {}
    }
    None
}

pub async fn start_telemetry_loop(_app: AppHandle) {
    let mut sys = System::new_all();
    let client = reqwest::Client::new();
    
    // Attempt registration until success
    let mut device_id = None;
    while device_id.is_none() {
        device_id = auto_register().await;
        if device_id.is_none() {
            tokio::time::sleep(Duration::from_secs(10)).await;
        }
    }
    
    let device_id = device_id.unwrap();
    
    loop {
        sys.refresh_all();
        
        let cpu_usage = sys.global_cpu_info().cpu_usage();
        let total_mem = sys.total_memory() as f32;
        let used_mem = sys.used_memory() as f32;
        let ram_usage = if total_mem > 0.0 { (used_mem / total_mem) * 100.0 } else { 0.0 };
        
        let payload = TelemetryRequest {
            ip_address: get_local_ip(),
            cpu_usage,
            ram_usage,
            disk_usage: 0.0,
            temperature: 45.0, // Mock temperature for now
            current_active_app: Some("MKT_POS.exe".to_string()),
            current_active_url: None,
        };
        
        let url = format!("{}/devices/{}/telemetry", API_BASE, device_id);
        let _ = client.post(&url).json(&payload).send().await;
        
        tokio::time::sleep(Duration::from_secs(15)).await;
    }
}
