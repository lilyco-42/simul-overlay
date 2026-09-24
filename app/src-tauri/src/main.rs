// 普惠同传 - 悬浮字幕壳
// Python 管线子进程承载四路功能：麦克风同传 / 系统声音同传 / 圈选OCR / 整篇阅读。
// stdout 行分流：`[xxx]` 状态行 → status 事件；字幕行 → subtitle 事件；stderr → status。
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::io::{BufRead, BufReader};
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use tauri::Emitter;

fn py_path() -> String {
    std::env::var("SIMUL_PYTHON")
        .unwrap_or_else(|_| r"D:\Code\simul-demo\.venv\Scripts\python.exe".into())
}

/// 脚本定位：SIMUL_SCRIPT_DIR 可整体重定向（打包分发用），否则用开发目录。
fn script_path(name: &str) -> String {
    match std::env::var("SIMUL_SCRIPT_DIR") {
        Ok(dir) => format!(r"{dir}\{name}"),
        Err(_) => format!(r"D:\Code\simul-demo\{name}"),
    }
}

#[derive(Default)]
struct Slots {
    audio: Option<Child>,
    ocr: Option<Child>,
    doc: Option<Child>,
}

fn kill(slot: &mut Option<Child>) {
    if let Some(mut c) = slot.take() {
        let _ = c.kill();
        let _ = c.wait();
    }
}

/// 把子进程 stdout/stderr 接到前端事件流。
fn stream(app: &tauri::AppHandle, child: &mut Child) {
    if let Some(out) = child.stdout.take() {
        let app = app.clone();
        std::thread::spawn(move || {
            for line in BufReader::new(out).lines().map_while(Result::ok) {
                let t = line.trim_end().to_string();
                if t.is_empty() {
                    continue;
                }
                if t.starts_with('[') {
                    let _ = app.emit("status", t);
                } else {
                    let _ = app.emit("subtitle", t);
                }
            }
        });
    }
    if let Some(err) = child.stderr.take() {
        let app = app.clone();
        std::thread::spawn(move || {
            for line in BufReader::new(err).lines().map_while(Result::ok) {
                let t = line.trim_end().to_string();
                if !t.is_empty() {
                    let _ = app.emit("status", format!("[err] {t}"));
                }
            }
        });
    }
}

#[tauri::command]
fn start_pipeline(
    app: tauri::AppHandle,
    state: tauri::State<'_, Mutex<Slots>>,
    source: String,
    tts: bool,
    seconds: u64,
) -> Result<(), String> {
    let mut slots = state.lock().map_err(|e| e.to_string())?;
    kill(&mut slots.audio);

    let script = if source == "system" {
        std::env::var("SIMUL_DEMO_SYSTEM").unwrap_or_else(|_| script_path("demo_system.py"))
    } else {
        std::env::var("SIMUL_DEMO").unwrap_or_else(|_| script_path("demo_mic.py"))
    };

    let mut cmd = Command::new(py_path());
    cmd.arg(script)
        .arg(seconds.to_string())
        .env("SIMUL_TTS", if tts { "1" } else { "0" })
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .stdin(Stdio::null());

    let mut child = cmd.spawn().map_err(|e| e.to_string())?;
    stream(&app, &mut child);
    slots.audio = Some(child);
    Ok(())
}

#[tauri::command]
fn start_ocr(
    app: tauri::AppHandle,
    state: tauri::State<'_, Mutex<Slots>>,
    select: bool,
) -> Result<(), String> {
    let mut slots = state.lock().map_err(|e| e.to_string())?;
    kill(&mut slots.ocr);

    let script = std::env::var("SIMUL_OCR").unwrap_or_else(|_| script_path("demo_ocr.py"));
    let mut cmd = Command::new(py_path());
    cmd.arg(script);
    if select {
        cmd.arg("--select");
    }
    cmd.stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .stdin(Stdio::null());

    let mut child = cmd.spawn().map_err(|e| e.to_string())?;
    stream(&app, &mut child);
    slots.ocr = Some(child);
    Ok(())
}

#[tauri::command]
fn read_doc(
    app: tauri::AppHandle,
    state: tauri::State<'_, Mutex<Slots>>,
    path: String,
    dst: String,
) -> Result<(), String> {
    if !std::path::Path::new(&path).exists() {
        return Err(format!("文件不存在: {path}"));
    }
    let mut slots = state.lock().map_err(|e| e.to_string())?;
    kill(&mut slots.doc);

    let script = std::env::var("SIMUL_READ").unwrap_or_else(|_| script_path("read_doc.py"));
    let mut cmd = Command::new(py_path());
    cmd.arg(script).arg(&path);
    if !dst.is_empty() {
        cmd.arg(&dst);
    }
    cmd.stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .stdin(Stdio::null());

    let mut child = cmd.spawn().map_err(|e| e.to_string())?;
    stream(&app, &mut child);
    slots.doc = Some(child);
    Ok(())
}

#[tauri::command]
fn stop_all(state: tauri::State<'_, Mutex<Slots>>) -> Result<(), String> {
    let mut slots = state.lock().map_err(|e| e.to_string())?;
    kill(&mut slots.audio);
    kill(&mut slots.ocr);
    kill(&mut slots.doc);
    Ok(())
}

fn main() {
    tauri::Builder::default()
        .manage(Mutex::new(Slots::default()))
        .invoke_handler(tauri::generate_handler![
            start_pipeline,
            start_ocr,
            read_doc,
            stop_all
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
