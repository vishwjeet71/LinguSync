// Learn more about Tauri commands at https://tauri.app/develop/calling-rust/
#[tauri::command]
fn greet(name: String) -> Result<String, String> {
    if name.trim().is_empty() {
        return Err("Name cannot be empty".into());
    }

    Ok(format!("Hello, {}!", name))
}

#[tauri::command]
async fn start_processing(app: tauri::AppHandle) -> Result<(), String> {
    use std::time::Duration;
    use tauri::Emitter;

    for progress in [10, 25, 50, 75, 100] {
        std::thread::sleep(Duration::from_millis(500));

        app.emit("processing-progress", progress)
            .map_err(|e| e.to_string())?;
    }

    app.emit("processing-completed", ())
        .map_err(|e| e.to_string())?;

    Ok(())
}

use std::sync::Mutex;
use tauri::State;

struct AppState {
    counter: u32,
}

#[tauri::command]
fn get_counter(state: State<'_, Mutex<AppState>>) -> Result<u32, String> {
    let app_state = state.lock().map_err(|e| e.to_string())?;
    Ok(app_state.counter)
}

#[tauri::command]
fn increase_counter(state: State<'_, Mutex<AppState>>) -> Result<u32, String> {
    let mut app_state = state.lock().map_err(|e| e.to_string())?;
    app_state.counter += 1;
    Ok(app_state.counter)
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .manage(Mutex::new(AppState { counter: 0 }))
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_dialog::init())
        .invoke_handler(tauri::generate_handler![greet, start_processing, get_counter, increase_counter])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
