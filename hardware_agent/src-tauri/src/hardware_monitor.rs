#![allow(non_camel_case_types)]
#![allow(unused_variables)]

use std::collections::{HashSet, HashMap};
use std::time::Duration;
use serde::{Deserialize, Serialize};
use wmi::{COMLibrary, WMIConnection};
use tauri::AppHandle;
use tauri::api::dialog::MessageDialogBuilder;

// Data structures for WMI queries
#[derive(Deserialize, Debug)]
#[serde(rename_all = "PascalCase")]
struct Win32_PnPEntity {
    device_id: String,
    name: Option<String>,
    description: Option<String>,
    status: Option<String>,
    config_manager_error_code: Option<u32>,
}

#[derive(Deserialize, Debug)]
#[serde(rename_all = "PascalCase")]
struct Win32_DesktopMonitor {
    device_id: String,
    name: Option<String>,
}

#[derive(Deserialize, Debug)]
#[serde(rename_all = "PascalCase")]
struct Win32_NetworkAdapter {
    device_id: String,
    name: Option<String>,
    net_connection_status: Option<u16>,
}

#[derive(Serialize)]
struct IncidentPayload {
    category: String,
    summary: String,
    hardware_name: String,
    hardware_type: String,
}

const API_BASE: &str = "http://10.20.0.193:8000/api";

async fn report_incident(app: &AppHandle, payload: IncidentPayload) {
    let msg = format!("Warning: {} has been disconnected or failed. Reporting to Incident Memory.", payload.hardware_name);
    
    // Show UI notification (thread-safe)
    let _ = tauri::api::notification::Notification::new(&app.config().tauri.bundle.identifier)
        .title("Hardware Alert")
        .body(&msg)
        .show();
        
    // Send to backend
    let client = reqwest::Client::new();
    let url = format!("{}/port-checker/", API_BASE);
    
    // Wait for auto-register ID if needed or just send anonymously with hostname
    let hostname = hostname::get().unwrap_or_default().to_string_lossy().into_owned();
    
    let req_body = serde_json::json!({
        "summary": payload.summary,
        "category": payload.category,
        "hardware_name": payload.hardware_name,
        "hardware_type": payload.hardware_type,
        "device_name": hostname
    });
    
    let _ = client.post(&url).json(&req_body).send().await;
}

pub async fn start_hardware_monitor(app: AppHandle) {
    // We use a dedicated thread for WMI because COM must be initialized in a specific way per thread
    let (tx, mut rx) = tokio::sync::mpsc::channel::<(String, String, String)>(100);
    
    // WMI Thread
    std::thread::spawn(move || {
        let com_con = match COMLibrary::new() {
            Ok(c) => c,
            Err(_) => return,
        };
        
        let wmi_con = match WMIConnection::new(com_con) {
            Ok(w) => w,
            Err(_) => return,
        };
        
        let mut known_usb_names: HashMap<String, String> = HashMap::new();
        let mut previous_usb: HashSet<String> = HashSet::new();
        let mut missing_usb_since: HashMap<String, std::time::Instant> = HashMap::new();
        
        let mut known_monitor_names: HashMap<String, String> = HashMap::new();
        let mut previous_monitors: HashSet<String> = HashSet::new();
        let mut missing_monitors_since: HashMap<String, std::time::Instant> = HashMap::new();
        
        let mut known_lan_names: HashMap<String, String> = HashMap::new();
        let mut previous_lan_status: HashMap<String, u16> = HashMap::new();
        let mut lan_down_since: HashMap<String, std::time::Instant> = HashMap::new();
        
        // Initial population
        if let Ok(usb_devices) = wmi_con.raw_query::<HashMap<String, wmi::Variant>>("SELECT DeviceID, Name, ConfigManagerErrorCode FROM Win32_PnPEntity WHERE DeviceID LIKE 'USB%'") {
            for dev in usb_devices {
                let device_id = match dev.get("DeviceID") {
                    Some(wmi::Variant::String(s)) => s.clone(),
                    _ => continue,
                };
                let err_code = match dev.get("ConfigManagerErrorCode") {
                    Some(wmi::Variant::I4(v)) => *v,
                    Some(wmi::Variant::UI4(v)) => *v as i32,
                    _ => 0,
                };
                if err_code != 0 { continue; }
                
                let name = match dev.get("Name") {
                    Some(wmi::Variant::String(s)) => s.clone(),
                    _ => "Unknown USB Device".to_string(),
                };
                previous_usb.insert(device_id.clone());
                known_usb_names.insert(device_id, name);
            }
        }
        
        if let Ok(monitors) = wmi_con.raw_query::<HashMap<String, wmi::Variant>>("SELECT DeviceID, Name, ConfigManagerErrorCode FROM Win32_PnPEntity WHERE PNPClass = 'Monitor'") {
            for dev in monitors {
                let device_id = match dev.get("DeviceID") {
                    Some(wmi::Variant::String(s)) => s.clone(),
                    _ => continue,
                };
                let err_code = match dev.get("ConfigManagerErrorCode") {
                    Some(wmi::Variant::I4(v)) => *v,
                    Some(wmi::Variant::UI4(v)) => *v as i32,
                    _ => 0,
                };
                if err_code != 0 { continue; }
                
                let name = match dev.get("Name") {
                    Some(wmi::Variant::String(s)) => s.clone(),
                    _ => "Unknown Display".to_string(),
                };
                previous_monitors.insert(device_id.clone());
                known_monitor_names.insert(device_id, name);
            }
        }
        
        loop {
            std::thread::sleep(Duration::from_secs(5));
            
            // 1. Check USB Devices
            if let Ok(usb_devices) = wmi_con.raw_query::<HashMap<String, wmi::Variant>>("SELECT DeviceID, Name, ConfigManagerErrorCode FROM Win32_PnPEntity WHERE DeviceID LIKE 'USB%'") {
                let mut current_usb = HashSet::new();
                for d in &usb_devices {
                    let device_id = match d.get("DeviceID") {
                        Some(wmi::Variant::String(s)) => s.clone(),
                        _ => continue,
                    };
                    let err_code = match d.get("ConfigManagerErrorCode") {
                        Some(wmi::Variant::I4(v)) => *v,
                        Some(wmi::Variant::UI4(v)) => *v as i32,
                        _ => 0,
                    };
                    if err_code != 0 { continue; }
                    
                    let name = match d.get("Name") {
                        Some(wmi::Variant::String(s)) => s.clone(),
                        _ => "Unknown USB Device".to_string(),
                    };
                    current_usb.insert(device_id.clone());
                    known_usb_names.insert(device_id, name);
                }
                
                for old_dev in &previous_usb {
                    if !current_usb.contains(old_dev) {
                        missing_usb_since.entry(old_dev.clone()).or_insert_with(std::time::Instant::now);
                    }
                }
                
                missing_usb_since.retain(|dev, _| !current_usb.contains(dev));
                
                let now = std::time::Instant::now();
                let mut to_report = Vec::new();
                for (dev, since) in &missing_usb_since {
                    if now.duration_since(*since).as_secs() >= 30 {
                        to_report.push(dev.clone());
                    }
                }
                
                for dev in to_report {
                    missing_usb_since.remove(&dev);
                    previous_usb.remove(&dev);
                    let name = known_usb_names.get(&dev).cloned().unwrap_or_else(|| dev.clone());
                    let _ = tx.blocking_send(("USB".to_string(), name, "USB device disconnected".to_string()));
                }
                
                for dev in current_usb {
                    previous_usb.insert(dev);
                }
            }
            
            // 2. Check LAN
            if let Ok(adapters) = wmi_con.raw_query::<HashMap<String, wmi::Variant>>("SELECT DeviceID, Name, NetConnectionStatus FROM Win32_NetworkAdapter WHERE NetConnectionStatus IS NOT NULL") {
                let now = std::time::Instant::now();
                let mut to_report_lan = Vec::new();
                
                for adapter in adapters {
                    let id = match adapter.get("DeviceID") {
                        Some(wmi::Variant::String(s)) => s.clone(),
                        _ => continue,
                    };
                    let status = match adapter.get("NetConnectionStatus") {
                        Some(wmi::Variant::I2(v)) => *v as u16,
                        Some(wmi::Variant::UI2(v)) => *v as u16,
                        Some(wmi::Variant::I4(v)) => *v as u16,
                        Some(wmi::Variant::UI4(v)) => *v as u16,
                        _ => 0,
                    };
                    let name = match adapter.get("Name") {
                        Some(wmi::Variant::String(s)) => s.clone(),
                        _ => "Unknown Adapter".to_string(),
                    };
                    
                    known_lan_names.insert(id.clone(), name.clone());
                    let prev_status = previous_lan_status.get(&id).copied().unwrap_or(status);
                    
                    if (status == 4 || status == 7) && prev_status == 2 {
                        lan_down_since.entry(id.clone()).or_insert_with(std::time::Instant::now);
                    } else if status == 2 {
                        lan_down_since.remove(&id);
                    }
                    
                    previous_lan_status.insert(id.clone(), status);
                }
                
                for (dev_id, since) in &lan_down_since {
                    if now.duration_since(*since).as_secs() >= 30 {
                        to_report_lan.push(dev_id.clone());
                    }
                }
                
                for dev_id in to_report_lan {
                    lan_down_since.remove(&dev_id);
                    let name = known_lan_names.get(&dev_id).cloned().unwrap_or_else(|| dev_id.clone());
                    let _ = tx.blocking_send(("LAN".to_string(), name, "Network adapter disconnected".to_string()));
                }
            }
            
            // 3. Check Monitors/HDMI
            if let Ok(monitors) = wmi_con.raw_query::<HashMap<String, wmi::Variant>>("SELECT DeviceID, Name, ConfigManagerErrorCode FROM Win32_PnPEntity WHERE PNPClass = 'Monitor'") {
                let mut current_monitors = HashSet::new();
                for d in &monitors {
                    let device_id = match d.get("DeviceID") {
                        Some(wmi::Variant::String(s)) => s.clone(),
                        _ => continue,
                    };
                    let err_code = match d.get("ConfigManagerErrorCode") {
                        Some(wmi::Variant::I4(v)) => *v,
                        Some(wmi::Variant::UI4(v)) => *v as i32,
                        _ => 0,
                    };
                    if err_code != 0 { continue; }
                    
                    let name = match d.get("Name") {
                        Some(wmi::Variant::String(s)) => s.clone(),
                        _ => "Unknown Display".to_string(),
                    };
                    current_monitors.insert(device_id.clone());
                    known_monitor_names.insert(device_id, name);
                }
                
                for old_dev in &previous_monitors {
                    if !current_monitors.contains(old_dev) {
                        missing_monitors_since.entry(old_dev.clone()).or_insert_with(std::time::Instant::now);
                    }
                }
                
                missing_monitors_since.retain(|dev, _| !current_monitors.contains(dev));
                
                let now = std::time::Instant::now();
                let mut to_report = Vec::new();
                for (dev, since) in &missing_monitors_since {
                    if now.duration_since(*since).as_secs() >= 30 {
                        to_report.push(dev.clone());
                    }
                }
                
                for dev in to_report {
                    missing_monitors_since.remove(&dev);
                    previous_monitors.remove(&dev);
                    let name = known_monitor_names.get(&dev).cloned().unwrap_or_else(|| dev.clone());
                    let _ = tx.blocking_send(("HDMI/Display".to_string(), name, "Display monitor disconnected".to_string()));
                }
                
                for dev in current_monitors {
                    previous_monitors.insert(dev);
                }
            }
        }
    });
    
    // Receiver task in tokio async context
    tokio::spawn(async move {
        while let Some((dev_type, dev_name, summary)) = rx.recv().await {
            report_incident(&app, IncidentPayload {
                category: "HARDWARE_FAILURE".to_string(),
                summary: format!("{}: {}", summary, dev_name),
                hardware_name: dev_name,
                hardware_type: dev_type,
            }).await;
        }
    });
}
