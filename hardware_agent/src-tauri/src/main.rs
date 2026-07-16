#![cfg_attr(
    all(not(debug_assertions), target_os = "windows"),
    windows_subsystem = "windows"
)]

use tauri::{CustomMenuItem, SystemTray, SystemTrayMenu, SystemTrayEvent, Manager};


mod telemetry;
mod hardware_monitor;

fn main() {
    let open_chat = CustomMenuItem::new("open_chat".to_string(), "Buka Chat Helpdesk");
    let quit = CustomMenuItem::new("quit".to_string(), "Keluar");
    
    let tray_menu = SystemTrayMenu::new()
        .add_item(open_chat)
        .add_item(quit);
        
    let system_tray = SystemTray::new().with_menu(tray_menu);

    tauri::Builder::default()
        .system_tray(system_tray)
        .on_system_tray_event(|app, event| match event {
            SystemTrayEvent::MenuItemClick { id, .. } => {
                match id.as_str() {
                    "open_chat" => {
                        let window = app.get_window("main").unwrap();
                        
                        if let Ok(Some(monitor)) = window.primary_monitor() {
                            let size = monitor.size();
                            let win_size = window.outer_size().unwrap_or(tauri::PhysicalSize::new(400, 600));
                            let x = size.width.saturating_sub(win_size.width + 20);
                            let y = size.height.saturating_sub(win_size.height + 60);
                            let _ = window.set_position(tauri::PhysicalPosition::new(x, y));
                        }
                        
                        window.show().unwrap();
                        window.set_focus().unwrap();
                    }
                    "quit" => {
                        std::process::exit(0);
                    }
                    _ => {}
                }
            }
            SystemTrayEvent::DoubleClick { .. } => {
                let window = app.get_window("main").unwrap();
                if let Ok(Some(monitor)) = window.primary_monitor() {
                    let size = monitor.size();
                    let win_size = window.outer_size().unwrap_or(tauri::PhysicalSize::new(400, 600));
                    let x = size.width.saturating_sub(win_size.width + 20);
                    let y = size.height.saturating_sub(win_size.height + 60);
                    let _ = window.set_position(tauri::PhysicalPosition::new(x, y));
                }
                window.show().unwrap();
                window.set_focus().unwrap();
            }
            _ => {}
        })
        .on_window_event(|event| match event.event() {
            tauri::WindowEvent::CloseRequested { api, .. } => {
                // Prevent window from closing, just hide it
                event.window().hide().unwrap();
                api.prevent_close();
            }
            _ => {}
        })
        .setup(|app| {
            let handle = app.handle();
            let handle2 = app.handle();
            
            // Start background telemetry task
            tauri::async_runtime::spawn(async move {
                telemetry::start_telemetry_loop(handle).await;
            });
            
            tauri::async_runtime::spawn(async move {
                hardware_monitor::start_hardware_monitor(handle2).await;
            });
            
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            send_chat_message,
            escalate_ticket,
            poll_chat_messages,
            send_live_chat,
            close_customer_ticket,
            upload_attachment
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

#[derive(serde::Serialize)]
pub struct ChatResponse {
    reply: String,
    ticket_id: String,
}

#[tauri::command]
async fn send_chat_message(message: String) -> Result<ChatResponse, String> {
    let client = reqwest::Client::new();
    let device_id = telemetry::get_saved_device_id().unwrap_or_else(|| "UNKNOWN".to_string());
    
    let payload = serde_json::json!({
        "device_id": device_id,
        "message": message,
        "sender": "POS User"
    });
    
    match client.post("http://10.20.0.193:8000/api/chat/incoming")
        .json(&payload)
        .send()
        .await {
            Ok(res) => {
                if res.status().is_success() {
                    if let Ok(json) = res.json::<serde_json::Value>().await {
                        let reply = json["reply"].as_str().unwrap_or("Pesan terkirim.").to_string();
                        let ticket_id = json["ticket_id"].as_str().unwrap_or("").to_string();
                        return Ok(ChatResponse { reply, ticket_id });
                    }
                }
                Err("Gagal menghubungi server.".to_string())
            },
            Err(e) => Err(format!("Network Error: {}", e))
        }
}

#[tauri::command]
async fn escalate_ticket(ticket_id: String) -> Result<String, String> {
    let client = reqwest::Client::new();
    let url = format!("http://10.20.0.193:8000/api/tickets/{}/escalate", ticket_id);
    match client.post(&url).send().await {
        Ok(res) => {
            if res.status().is_success() {
                Ok("Success".to_string())
            } else {
                Err(format!("Server returned {}", res.status()))
            }
        },
        Err(e) => Err(format!("Network Error: {}", e))
    }
}

#[tauri::command]
async fn poll_chat_messages(ticket_id: String) -> Result<Vec<serde_json::Value>, String> {
    let client = reqwest::Client::new();
    let url = format!("http://10.20.0.193:8000/api/chat/messages/{}", ticket_id);
    match client.get(&url).send().await {
        Ok(res) => {
            if res.status().is_success() {
                if let Ok(json) = res.json::<Vec<serde_json::Value>>().await {
                    return Ok(json);
                }
            }
            Err("Failed to parse".to_string())
        },
        Err(e) => Err(format!("Network Error: {}", e))
    }
}

#[tauri::command]
async fn send_live_chat(ticket_id: String, message: String) -> Result<String, String> {
    let client = reqwest::Client::new();
    let url = format!("http://10.20.0.193:8000/api/chat/messages/{}", ticket_id);
    let payload = serde_json::json!({
        "sender": "USER",
        "message_type": "TEXT",
        "content": message
    });
    match client.post(&url).json(&payload).send().await {
        Ok(res) => {
            if res.status().is_success() {
                Ok("Success".to_string())
            } else {
                Err(format!("Server returned {}", res.status()))
            }
        },
        Err(e) => Err(format!("Network Error: {}", e))
    }
}

#[tauri::command]
async fn close_customer_ticket(ticket_id: String) -> Result<String, String> {
    let client = reqwest::Client::new();
    let url = format!("http://10.20.0.193:8000/api/tickets/{}/close-by-customer", ticket_id);
    match client.post(&url).send().await {
        Ok(res) => {
            if res.status().is_success() {
                Ok("Success".to_string())
            } else {
                Err(format!("Server returned {}", res.status()))
            }
        },
        Err(e) => Err(format!("Network Error: {}", e))
    }
}

#[tauri::command]
async fn upload_attachment(file_path: String, ticket_id: String) -> Result<String, String> {
    use reqwest::multipart;
    use std::path::Path;
    
    let path = Path::new(&file_path);
    let file_name = path.file_name()
        .and_then(|n| n.to_str())
        .unwrap_or("attachment.png")
        .to_string();
        
    let file_bytes = match std::fs::read(&path) {
        Ok(bytes) => bytes,
        Err(e) => return Err(format!("Gagal membaca file: {}", e)),
    };
    
    let part = multipart::Part::bytes(file_bytes)
        .file_name(file_name)
        .mime_str("application/octet-stream")
        .unwrap_or_else(|_| multipart::Part::bytes(vec![]));
        
    let form = multipart::Form::new().part("file", part);
    
    let client = reqwest::Client::new();
    let url = format!("http://10.20.0.193:8000/api/chat/upload?ticket_id={}", ticket_id);
    
    match client.post(&url).multipart(form).send().await {
        Ok(res) => {
            if res.status().is_success() {
                if let Ok(json) = res.json::<serde_json::Value>().await {
                    let uploaded_url = json["url"].as_str().unwrap_or("").to_string();
                    return Ok(uploaded_url);
                }
            }
            Err(format!("Server returned {}", res.status()))
        },
        Err(e) => Err(format!("Network Error: {}", e))
    }
}
