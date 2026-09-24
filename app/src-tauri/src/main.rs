// 普惠同传 - 悬浮字幕壳（原型）
// 管线暂由 Python 子进程承载（验证期方案），stdout 按行流入前端渲染。
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::io::{BufRead, BufReader};
use std::process::{Command, Stdio};
use tauri::Emitter;

fn py_path() -> String {
    std::env::var("SIMUL_PYTHON")
        .unwrap_or_else(|_| r"D:\Code\simul-demo\.venv\Scripts\python.exe".into())
}
fn demo_path() -> String {
    std::env::var("SIMUL_DEMO")
        .unwrap_or_else(|_| r"D:\Code\simul-demo\demo_mic.py".into())
}

#[tauri::command]
fn start_pipeline(app: tauri::AppHandle, seconds: u64) -> Result<(), String> {
    let child = Command::new(py_path())
        .arg(demo_path())
        .arg(seconds.to_string())
        .stdout(Stdio::piped())
        .stderr(Stdio::null())
        .spawn()
        .map_err(|e| e.to_string())?;

    let mut stdout = child.stdout.ok_or("no stdout pipe")?;
    std::thread::spawn(move || {
        let reader = BufReader::new(&mut stdout);
        for line in reader.lines().map_while(Result::ok) {
            let trimmed = line.trim_end().to_string();
            if trimmed.is_empty() || trimmed.starts_with('[') {
                continue; // 过滤 [mic]/[level] 状态行
            }
            let _ = app.emit("subtitle", trimmed);
        }
    });
    Ok(())
}

fn main() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![start_pipeline])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
